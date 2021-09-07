from skyfield.api import load, wgs84, utc
from datetime import date, datetime, timedelta
from flask import Flask, request, session, render_template, send_from_directory, make_response
from flask import url_for, redirect, jsonify
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
import json
import numpy as np
import pytz
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)
app.config.from_object('configfile')
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    userSettings = db.Column(db.PickleType, nullable=False)

    def __repr__(self):
        return '<%r>' % self.id


CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth = OAuth(app)
oauth.register(name='google',
               server_metadata_url=CONF_URL,
               client_kwargs={'scope': 'openid email profile'})


def make_sat_from_id(idList):
    satellites = []
    makeSatError = False
    for SatID in idList:
        try:
            url = 'https://celestrak.com/satcat/tle.php?CATNR={}'.format(SatID)
            filename = './TLEs/tle-{}.txt'.format(SatID)
            satellite = load.tle_file(url, filename=filename)
            days = load.timescale().now() - satellite[0].epoch
            if abs(days) > 5:  #if TLEs > 2 days old, get new ones
                satellite = load.tle_file(url, filename=filename, reload=True)
            satellites.append(satellite)
        except Exception as e:
            makeSatError = SatID
            print(e)
    return satellites, makeSatError


def calc_path(passesSorted, passIndex):
    if session.get('useSessionSettings') == True:
        settings = session['settings']
    else:
        settings = get_settings_from_file()
    stationLong = float(settings['stationLong'])
    stationLat = float(settings['stationLat'])
    stationLocation = wgs84.latlon(stationLat, stationLong)
    selected_pass = passesSorted[passIndex]
    satellite, _ = make_sat_from_id([selected_pass['NORADid']])
    passTimeArray = np.arange(selected_pass['start'], selected_pass['end'], 1)
    difference = satellite[0][0] - stationLocation
    ELAZ = []
    ts = load.timescale()
    for t in passTimeArray:
        timeStep = datetime.utcfromtimestamp(t).replace(tzinfo=pytz.utc)
        _el, _az, _ = difference.at(ts.from_datetime(timeStep)).altaz()
        _eldeg = _el.degrees
        ELAZ.append([t, _eldeg, _az.degrees])
    return ELAZ


def calc_map_coords(passesSorted, passIndex):
    if session.get('useSessionSettings') == True:
        settings = session['settings']
    else:
        settings = get_settings_from_file()
    stationCoord = [
        float(settings['stationLong']),
        float(settings['stationLat'])
    ]
    selected_pass = passesSorted[passIndex]
    satellite, _ = make_sat_from_id([selected_pass['NORADid']])
    ts = load.timescale()
    AOStime = ts.from_datetime(
        datetime.utcfromtimestamp(
            selected_pass['start']).replace(tzinfo=pytz.timezone('UTC')))
    LOStime = ts.from_datetime(
        datetime.utcfromtimestamp(
            selected_pass['end']).replace(tzinfo=pytz.timezone('UTC')))
    AOSpos = wgs84.subpoint(satellite[0][0].at(AOStime))
    LOSpos = wgs84.subpoint(satellite[0][0].at(LOStime))
    AOScoord = [
        round(AOSpos.longitude.degrees, 2),
        round(AOSpos.latitude.degrees, 2)
    ]
    LOScoord = [
        round(LOSpos.longitude.degrees, 2),
        round(LOSpos.latitude.degrees, 2)
    ]
    return AOScoord, LOScoord, stationCoord


# This function loads and returns the settings for list of satellites to track,
# station location ...
def get_settings_from_file():
    if session.get('user') != None:
        userdata = User.query.filter_by(
            id=session.get('user')['email']).first()
        settings = userdata.userSettings
    else:
        #Default settings if custom settings file doesn't exist
        stationLong = -73.43
        stationLat = +45.51
        predHours = 24.0
        predictionType = 'realtime'
        customStartTime = datetime.strftime(datetime.now(),
                                            "%Y-%m-%dT%H:%M:%S.%fZ")
        minAltitudeDegrees = 5.0
        idList = [25338, 28654, 33591, 38771, 43689, 37214, 25544]
        satellites, _ = make_sat_from_id(idList)
        satList = {}
        for i in range(idList.__len__()):
            satList[i] = {
                'name': satellites[i][0].name,
                'NORADid': idList[i],
                'priority': i
            }

        settings = {
            'satList': satList,
            'stationLong': stationLong,
            'stationLat': stationLat,
            'predHours': predHours,
            'minElevation': minAltitudeDegrees,
            'predictionType': predictionType,
            'customStartTime': customStartTime
        }

    return (settings)


# This function predicts the upcoming passes for the list of satellites in the
# specified time period
def predict(settings):

    satList = settings['satList']
    stationLong = float(settings['stationLong'])
    stationLat = float(settings['stationLat'])
    predHours = float(settings['predHours'])
    minAltitudeDegrees = float(settings['minElevation'])
    stationLocation = wgs84.latlon(stationLat, stationLong)
    predictionType = settings['predictionType']
    customStartTime = datetime.strptime(settings['customStartTime'],
                                        "%Y-%m-%dT%H:%M:%S.%fZ")
    #  Get TLEs from celestrak and save in file
    idList = [satList[ind]['NORADid'] for ind in satList]
    satellites, _ = make_sat_from_id(idList)

    #Timescale range for predicting satellite passes
    ts = load.timescale()
    if predictionType == 'realtime':
        t0 = ts.utc(ts.now().utc_datetime() -
                    timedelta(seconds=30))  #Time range starts 30s before now
    else:
        t0 = ts.utc(customStartTime.replace(tzinfo=pytz.utc))
    t1 = ts.utc(t0.utc_datetime() + timedelta(hours=predHours))
    passes = {}

    #This for loop goes through each satellite and finds passes over the
    #station, passe information for all satellites are stored in the 'passes' array
    passIndex = 0

    for i, satloop in enumerate(satList):
        t_temp, events_temp = satellites[i][0].find_events(
            stationLocation, t0, t1, altitude_degrees=minAltitudeDegrees)
        # find event returns [0: AOS, 1: PEAK, 2: LOS, 0: AOS ... ]
        t_AOSLOS = np.delete(t_temp, np.where(events_temp == 1))

        #If we call find_events() during a pass, it's going to return an array
        #starting with event 1 or 2 (PEAK/LOS) instead of 0 (AOS). To find the
        #AOS time in the past, this if statement goes back one day and finds the
        #closest AOS time to the current time and puts that as the first element
        #of the t_AOSLOS array
        if events_temp[0] != 0:
            t_temp1, events_temp1 = satellites[i][0].find_events(
                stationLocation,
                ts.utc(t0.utc_datetime() - timedelta(hours=24)),
                t0,
                altitude_degrees=minAltitudeDegrees)
            aosArray = np.delete(
                t_temp1,
                np.append(np.where(events_temp1 == 1),
                          np.where(events_temp1 == 2)))
            passAOS = min(aosArray, key=lambda x: abs(x - t0))
            t_AOSLOS = [passAOS] + t_AOSLOS.tolist()

        t_AOS = t_AOSLOS[0:][::2]
        t_LOS = t_AOSLOS[1:][::2]
        orbitatEpoch = satellites[i][0].model.revnum
        angVel = satellites[i][0].model.no_kozai
        for j, _ in enumerate(t_LOS):
            minSinceEpoch = (
                datetime.timestamp(t_AOS[j].utc_datetime()) -
                datetime.timestamp(satellites[i][0].epoch.utc_datetime())) / 60
            orbitsSinceEpoch = np.floor(minSinceEpoch * angVel / (2 * np.pi))
            orbitnum = orbitatEpoch + orbitsSinceEpoch

            passes[passIndex] = {
                'start':
                datetime.timestamp(t_AOS[j].utc_datetime()),
                'end':
                datetime.timestamp(t_LOS[j].utc_datetime()),
                'duration': (t_LOS[j].utc_datetime() -
                             t_AOS[j].utc_datetime()).total_seconds(),
                'satName':
                satellites[i][0].name,
                'NORADid':
                satList[satloop]['NORADid'],
                'priority':
                satList[satloop]['priority'],
                'satIND':
                i,
                'orbitnum':
                orbitnum,
                'take':
                True
            }
            passIndex = passIndex + 1

    minSecBetweenPass = 0
    # Sort passes by AOS time
    passSortKeys = sorted(passes, key=lambda x: passes.get(x).get('start'))
    passesSorted = []
    for i in passSortKeys:
        passesSorted.append(passes[i])
    # Handles conflicts based on priority
    for i in range(0, len(passesSorted)):
        if passesSorted[i]['take'] == True:
            for j in range(i + 1, len(passesSorted)):
                if passesSorted[i]['end'] + minSecBetweenPass > passesSorted[
                        j]['start']:
                    if passesSorted[i]['priority'] < passesSorted[j][
                            'priority']:
                        passesSorted[i]['take'] = True
                        passesSorted[j]['take'] = False
                    else:
                        passesSorted[i]['take'] = False
                        passesSorted[j]['take'] = True
                        break
                else:
                    passesSorted[i]['take'] = True
                    break

    return passesSorted


@app.route('/api/mapviewInfo', methods=['POST'])
def map_coord_to_react():
    passAOS = request.json
    passsorted = np.array(session['passesSorted'])
    aosList = [aos['start'] for aos in passsorted]
    passIndex = aosList.index(passAOS)
    aosCoord, losCoord, stationCoord = calc_map_coords(passsorted, passIndex)
    mapinfo = [aosCoord, losCoord, stationCoord]
    return jsonify(mapinfo)


@app.route('/api/passData')
def passData_to_react():
    if session.get('useSessionSettings') == True:
        settings = session['settings']
    else:
        settings = get_settings_from_file()
    passesSorted = predict(settings)
    session['passesSorted'] = passesSorted
    return json.dumps(passesSorted)


@app.route('/api/settings', methods=['GET'])
def pass_settings_to_react():
    if session.get('useSessionSettings') == True:
        settings = session['settings']
    else:
        settings = get_settings_from_file()
    return settings


@app.route('/api/changeSettings', methods=['POST'])
def get_settings_from_react():
    session['useSessionSettings'] = False
    data = request.json
    idList = [data['satList'][sats]['NORADid'] for sats in data['satList']]
    stationLong = data['stationLong']
    stationLat = data['stationLat']
    predHours = data['predHours']
    minAltitudeDegrees = data['minElevation']
    customStartTime = data['customStartTime']
    predictionType = data['predictionType']
    satellites, makeSatError = make_sat_from_id(idList)

    if makeSatError is False:
        satList = {}
        for i in range(satellites.__len__()):
            satList[i] = {
                'name': satellites[i][0].name,
                'NORADid': idList[i],
                'priority': i
            }
        settings = {
            'satList': satList,
            'stationLong': stationLong,
            'stationLat': stationLat,
            'predHours': predHours,
            'minElevation': minAltitudeDegrees,
            'customStartTime': customStartTime,
            'predictionType': predictionType
        }
        userEmail = session.get('user')['email']
        userData = User.query.filter_by(id=userEmail).first()
        if userData == None:
            newSettings = User(id=userEmail, userSettings=settings)
            db.session.add(newSettings)
        else:
            userData.userSettings = settings
        db.session.commit()

        return jsonify('Settings saved!')
    else:
        errorString = 'NORAD ID: {ErrorID} caused an error, settings not saved.'
        return jsonify(errorString.format(ErrorID=makeSatError))


@app.route('/api/get_path_csv', methods=['POST'])
def path_CSV_to_react():
    passAOS = request.json
    passesSorted = np.array(session['passesSorted'])
    aosList = [aos['start'] for aos in passesSorted]
    passIndex = aosList.index(passAOS)
    path = calc_path(session['passesSorted'], passIndex)
    return jsonify(path)


@app.route('/api/next_pass_path', methods=['POST'])
def next_pass_path():
    userEmail = request.get_json()['Email address']
    try:
        userdata = User.query.filter_by(id=userEmail).first()
        settings = userdata.userSettings
    except:
        return "Email not found in database", 400
    passesSorted = predict(settings)
    for passes in passesSorted:
        if passes['take'] == True and passes['start'] > datetime.now(
        ).timestamp():
            nextPass = passes
            break
    aosList = [aos['start'] for aos in passesSorted]
    passIndex = aosList.index(nextPass['start'])
    path = calc_path(passesSorted, passIndex)
    return jsonify(path)


@app.route('/api/save_to_session', methods=['POST'])
def save_settings_to_session():
    data = request.json
    idList = [data['satList'][sats]['NORADid'] for sats in data['satList']]
    stationLong = data['stationLong']
    stationLat = data['stationLat']
    predHours = data['predHours']
    minAltitudeDegrees = data['minElevation']
    customStartTime = data['customStartTime']
    predictionType = data['predictionType']
    satellites, makeSatError = make_sat_from_id(idList)

    if makeSatError is False:
        satList = {}
        for i in range(satellites.__len__()):
            satList[i] = {
                'name': satellites[i][0].name,
                'NORADid': idList[i],
                'priority': i
            }
        settings = {
            'satList': satList,
            'stationLong': stationLong,
            'stationLat': stationLat,
            'predHours': predHours,
            'minElevation': minAltitudeDegrees,
            'customStartTime': customStartTime,
            'predictionType': predictionType
        }
    else:
        errorString = 'NORAD ID: {ErrorID} caused an error, settings not saved.'
        return jsonify(errorString.format(ErrorID=makeSatError))

    session['settings'] = settings
    session['useSessionSettings'] = True

    return jsonify('Settings saved!')


@app.route('/api/session')
def apiSession():
    sessionUser = session.get('user')
    return jsonify(sessionUser)


@app.route('/api/login')
def login():
    redirect_uri = url_for('auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/auth')
def auth():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    session['user'] = user
    return redirect('/SettingsPage')


@app.route('/api/logout')
def logout():
    session.pop('user', None)
    return redirect('/SettingsPage')


@app.errorhandler(404)
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    app.run(host='localhost', port=5000)
