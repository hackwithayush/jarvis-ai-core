const { app, BrowserWindow } = require('electron');
const path = require('path');

let orbWindow;

function createOrbWindow() {
  orbWindow = new BrowserWindow({
    width: 350,
    height: 400,
    type: 'toolbar', // Prevents showing in taskbar
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    orbWindow.loadURL('http://localhost:5173');
  } else {
    orbWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
}

let dashWindow;
function createDashboardWindow() {
  if (dashWindow) {
    dashWindow.focus();
    return;
  }
  dashWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    frame: false,
    backgroundColor: '#0a0a0f',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    dashWindow.loadURL('http://localhost:5173/#dashboard');
  } else {
    dashWindow.loadFile(path.join(__dirname, 'dist', 'index.html'), { hash: 'dashboard' });
  }
  
  dashWindow.on('closed', () => { dashWindow = null });
}

app.whenReady().then(() => {
  createOrbWindow();
  // By default, we also show the dashboard to test it, but usually the tray triggers it
  createDashboardWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
