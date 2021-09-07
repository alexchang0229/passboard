import React, { useEffect, useState } from "react";
import TextField from '@material-ui/core/TextField';
import { makeStyles } from "@material-ui/core/styles";
import { Grid, Box, Paper, Tooltip } from '@material-ui/core';
import IconButton from '@material-ui/core/IconButton';
import AddIcon from '@material-ui/icons/Add';
import Table from '../functions/table.js'
import HelpIcon from '@material-ui/icons/Help';
import GoogleSignIn from '../assets/btn_google_signin_dark_normal_web@2x.png';
import Button from '@material-ui/core/Button';
import Select from '@material-ui/core/Select';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import FormControl from '@material-ui/core/FormControl';
import { DateTimePicker, MuiPickersUtilsProvider } from "@material-ui/pickers";
import DateFnsUtils from '@date-io/date-fns';

const useStyles = makeStyles((theme) => ({
    root: {
        '& .MuiTextField-root': {
            margin: theme.spacing(1),
            width: '25ch',
        },
    },
    formControl: {
        margin: theme.spacing(1),
        minWidth: 120,
    },
}));

export default function SettingsPage(props) {
    const [settings, setSettings] = useState(false);
    useEffect(() => {
        fetch('/api/settings').then(res => res.json()).then(data => {
            setSettings(data);
        });
    }, []);

    const classes = useStyles();
    const handleSubmit = (evt) => {
        evt.preventDefault();
        var apiRoute
        if (evt.nativeEvent.submitter.name === 'database') {
            apiRoute = '/api/changeSettings'
        }
        else {
            apiRoute = '/api/save_to_session'
        }
        fetch(apiRoute, {
            method: "POST",
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
            .then(response => response.json())
            .then(resBody => alert(resBody))
            .catch(error => console.error(error))

        //There's a delay here before refetching the passdata to allow
        //for the database to update
        setTimeout(() => props.setrefetchData(!props.refetchData), 1000)
    }
    const addSat = () => {
        const newSat = { NORADid: 0, name: "New Satellite", priority: 0 }
        var list = Object.values(settings['satList'])
        list.forEach((sat, ind) => sat['priority'] = ind + 1) //Move all priority down 1
        list.unshift(newSat)
        list.forEach((data, ind) => setSettings(
            (prevSetting) => ({
                ...prevSetting, satList: {
                    ...prevSetting.satList, [ind]: data
                }
            })
        ));
    }
    const deleteSat = (_, index) => {
        var list = Object.values(settings['satList'])
        list.splice(index, 1)
        list.forEach((sat, ind) => sat['priority'] = ind)
        var newSatList = {}
        list.forEach((data, ind) => (newSatList = {
            ...newSatList, [ind]: data
        }));
        setSettings((prevSetting) => ({ ...prevSetting, satList: newSatList }))
    }
    console.log(settings)

    return (
        <div style={{
            textAlign: "center", color: "white",
        }}>
            <h2>Settings</h2>
            {settings === false ? (<div>Loading...</div>) : (
                <Grid
                    container
                    direction="row"
                    spacing={1}
                    justify="center"

                    style={{
                        margin: 0,
                        width: '100%',
                    }}
                >
                    <Grid item >
                        <Paper>
                            <Box m={3}>
                                <Box m={1}>
                                    <span style={{ float: 'right' }}>
                                        <IconButton size='small' onClick={() => { if (Object.values(settings['satList']).length < 18) { addSat() } }}>
                                            <AddIcon />
                                        </IconButton>
                                    </span>
                                    <h4 style={{ paddingTop: 5 }}>
                                        Satellites
                                        <Tooltip title="Drag satellites to arrange priority">
                                            <HelpIcon style={{ fontSize: 14, paddingLeft: 6 }} />
                                        </Tooltip>
                                    </h4>
                                    <p>NORAD IDs can be found at <a href="https://celestrak.com/satcat/search.php">Celestrak</a></p>
                                </Box>

                                <Table deleteSat={deleteSat} settingIn={settings} setSettings={setSettings} />
                            </Box>
                        </Paper>
                    </Grid>
                    <Grid item>
                        <Paper>
                            <Box pb={3} m={3}>
                                <h4 style={{ paddingTop: 5 }}>User
                                    <Tooltip title="I just need your email so next time I can get your settings from the database,
                                    use save to session to store settings temporarily.">
                                        <HelpIcon style={{ fontSize: 14, paddingLeft: 6 }} />
                                    </Tooltip>
                                </h4>
                                {props.userSession === null
                                    ? (<div>
                                        <p>Not logged in</p>
                                        <a href={"/api/login"} target="_blank" rel="noreferrer">
                                            <img src={GoogleSignIn} height='50px' alt='Log in with Google' />
                                        </a>
                                    </div>)
                                    : (<div>
                                        <p>Logged in as: {props.userSession.email}</p>
                                        <a href="/api/logout">
                                            <Button variant="contained" >Log out</Button>
                                        </a>
                                    </div>)}
                            </Box>
                        </Paper>
                        <Paper>
                            <h4 style={{ paddingTop: 5 }}>Station</h4>
                            <Box pb={3} m={3}>
                                <form onSubmit={handleSubmit} className={classes.root}>
                                    <div>
                                        <TextField
                                            id="Longitude-setting"
                                            label="Station longitude"
                                            type="number"
                                            value={settings.stationLong}
                                            InputLabelProps={{ shrink: true }}
                                            onChange={e => {
                                                if (e.target.value >= -180 && e.target.value <= 180) {
                                                    setSettings(prevState => ({ ...prevState, stationLong: e.target.value }))
                                                }
                                            }}
                                            variant="filled"
                                        />
                                    </div>
                                    <div>
                                        <TextField
                                            id="Latitude-setting"
                                            label="Station latitude"
                                            type="number"
                                            value={settings.stationLat}
                                            InputLabelProps={{ shrink: true }}
                                            onChange={e => {
                                                if (e.target.value >= -90 && e.target.value <= 90) {
                                                    setSettings(prevState => ({ ...prevState, stationLat: e.target.value }))
                                                }
                                            }}
                                            variant="filled"
                                        />
                                    </div>
                                    <FormControl variant="filled" className={classes.formControl}>
                                        <InputLabel id="demo-simple-select-filled">
                                            Start time</InputLabel>
                                        <Select
                                            labelId="demo-simple-select-helper-label"
                                            id="demo-simple-select-helper"
                                            value={settings.predictionType}
                                            onChange={e => {
                                                setSettings(prevState => ({ ...prevState, predictionType: e.target.value }))
                                            }}
                                        >
                                            <MenuItem value={'realtime'}>Real-time</MenuItem>
                                            <MenuItem value={'custom'}>Custom</MenuItem>
                                        </Select>
                                    </FormControl>
                                    {settings.predictionType === 'custom'
                                        ? (<MuiPickersUtilsProvider utils={DateFnsUtils}>
                                            <DateTimePicker
                                                label="Custom start time"
                                                inputVariant="outlined"
                                                value={settings.customStartTime}
                                                onChange={e => setSettings(prevState => ({ ...prevState, customStartTime: e }))}
                                            />
                                        </MuiPickersUtilsProvider>)
                                        : (<div></div>)}
                                    <div>
                                        <TextField
                                            id="prediction-time-setting"
                                            label="Prediction duration (Hours)"
                                            value={settings.predHours}
                                            type="number"
                                            InputProps={{ inputProps: { min: 0, max: 24 } }}
                                            InputLabelProps={{ shrink: true }}
                                            onChange={e => setSettings(prevState => ({ ...prevState, predHours: e.target.value }))}
                                            variant="filled"
                                        />
                                    </div>
                                    <div>
                                        <TextField
                                            id="elevation-setting"
                                            label="Minimum Elevation (&#176;)"
                                            type="number"
                                            InputProps={{ inputProps: { min: 0, max: 90 } }}
                                            value={settings.minElevation}
                                            InputLabelProps={{ shrink: true }}
                                            onChange={e => setSettings(prevState => ({ ...prevState, minElevation: e.target.value }))}
                                            variant="filled"
                                        />
                                    </div>
                                    <Button
                                        type='submit'
                                        variant='contained'
                                        name='database'
                                        disabled={props.userSession === null
                                            ? (true)
                                            : (false)}
                                        style={{ margin: 5, marginLeft: 0 }}>
                                        Save to database
                                    </Button>
                                    <Button
                                        type='submit'
                                        variant="contained"
                                        name='session'
                                        style={{ margin: 5, marginRight: 0 }}>
                                        Save to session
                                    </Button>
                                </form>
                            </Box>
                        </Paper>
                    </Grid>
                </Grid>

            )
            }
        </div >
    )
}