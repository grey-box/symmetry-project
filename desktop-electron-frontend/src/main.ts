/*
This file which runs when you use command 'npm run start'
*/

import { app, BrowserWindow, ipcMain } from 'electron'
import * as path from 'path'
import { exec } from 'child_process'

declare const MAIN_WINDOW_VITE_DEV_SERVER_URL: string;
declare const MAIN_WINDOW_VITE_NAME: string;

import { appConstantsPromise } from './constants/AppConstants'
let AppConstants: any;

// A function to load our configuration file. Must be done from this main process
// since renderer processes have no file access.
async function grabConfig() {
    let AppConstants: any;
   try {
        AppConstants = await appConstantsPromise;
    } catch (error) {
        console.error("Failed to load configuration file: ", error);
        throw new Error(`Failed to load configuration file: ${error instanceof Error ? error.message : String(error)}`);
    }
    return AppConstants;
}

// IPC handler to check backend health (does not start backend, just checks if it's running)
ipcMain.handle('check-backend-health', async () => {
  const backendUrl = 'http://127.0.0.1:8000/health';
  
  return new Promise((resolve) => {
    exec(`curl -s -o /dev/null -w "%{http_code}" ${backendUrl}`, (error: any, stdout: any) => {
      if (error) {
        console.log(`[WARN] Backend health check failed: ${error.message}`);
        resolve({ status: 'unhealthy', error: error.message });
      } else if (stdout === '200') {
        console.log(`[INFO] Backend is healthy (HTTP 200)`);
        resolve({ status: 'healthy', url: backendUrl });
      } else {
        console.log(`[WARN] Backend responded with HTTP ${stdout}`);
        resolve({ status: 'unhealthy', httpCode: stdout });
      }
    });
  });
});

// Defining an IPC handle so renderer processes can access config.
ipcMain.handle('get-app-config', () => {
  return AppConstants as any;
});

// Detect if we're in development mode
const isDev = !app.isPackaged || process.env.NODE_ENV === 'development';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require("electron-squirrel-startup")) {
  app.quit();
}

const createWindow = async () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });
  
  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`)
    );
  }
  
  // Check backend health on startup
  try {
    AppConstants = await grabConfig();
  } catch(e) {
    console.error(`Error loading config: ${e}`);
  }
  
  // Perform a health check on backend
  exec('curl -s http://127.0.0.1:8000/health', (error: any, stdout: any, stderr: any) => {
    if (error) {
      console.log(`[WARN] Backend health check failed: Backend may not be running`);
      console.log(`[INFO] Please start backend using: ./start.sh backend`);
    } else {
      console.log(`[INFO] Backend is healthy: ${stdout.trim()}`);
    }
  });

  // Open the DevTools.
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on("ready", createWindow);

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
});

app.on("activate", () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
