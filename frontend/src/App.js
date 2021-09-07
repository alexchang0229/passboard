import React, { useState, useEffect } from 'react';
import './App.css';
import PassTimeTable from './pages/PassTimeTable.js';
import SettingsPage from './pages/SettingsPage.js';
import AboutPage from './pages/AboutPage.js';
import { BrowserRouter as Router, Switch, Route, Link } from "react-router-dom";
import { createMuiTheme } from "@material-ui/core/styles";
import { ThemeProvider } from "@material-ui/styles";


const theme = createMuiTheme({
  palette: {
    type: "dark"
  }
});

function App() {
  const [passData, setPassData] = useState(false);
  const [userSession, setuserSession] = useState(null);
  const [refetchData, setrefetchData] = useState(false);
  const [settings, setSettings] = useState(false);
  useEffect(() => {
    fetch('/api/passData').then(res => res.json()).then(data => {
      setPassData(data);
    }).catch(() => alert('Error fetching data from flask server.'));
  }, [refetchData]);
  useEffect(() => {
    fetch('/api/session').then(res => res.json()).then(data => {
      setuserSession(data);
    }).catch((e) => console.log(e));
  }, []);
  useEffect(() => {
    fetch('/api/settings').then(res => res.json()).then(data => {
      setSettings(data);
    });
  }, [refetchData]);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#282c34" }}>
      <Router>
        <ThemeProvider theme={theme}>
          <div className="App">
            &emsp;
            <Link to='/SettingsPage'>
              Settings
            </Link>&emsp;
            <Link to="" style={{ textAlign: "left" }}>
              Pass Board
            </Link>&emsp;
            <Link to="/About">
              About
            </Link>
            <Switch>
              <Route path="/SettingsPage">
                <SettingsPage
                  userSession={userSession}
                  setrefetchData={setrefetchData}
                  refetchData={refetchData} />
              </Route>
              <Route path="/About">
                <AboutPage />
              </Route>
              <Route path="/">
                <PassTimeTable
                  passData={passData}
                  setPassData={setPassData}
                  settings={settings} />
              </Route>
            </Switch>
          </div>
        </ThemeProvider>
      </Router>
    </div>
  );
}

export default App;
