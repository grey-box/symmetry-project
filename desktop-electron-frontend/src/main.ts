/*
This file which runs when you use command 'npm run start'
*/

import { app, BrowserWindow, ipcMain } from 'electron'
import * as path from 'path'
import { get } from 'node:http'

declare const MAIN_WINDOW_VITE_DEV_SERVER_URL: string;
declare const MAIN_WINDOW_VITE_NAME: string;

import { appConstantsPromise } from './constants/AppConstants'
let AppConstants: any;
const BACKEND_HEALTH_URL = 'http://127.0.0.1:8000/health';

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

function checkBackendHealth(backendUrl: string) {
  return new Promise<{ status: string; url?: string; httpCode?: number; error?: string }>((resolve) => {
    const req = get(backendUrl, { timeout: 5000 }, (res) => {
      res.resume();

      if (res.statusCode === 200) {
        console.log(`[INFO] Backend is healthy (HTTP 200)`);
        resolve({ status: 'healthy', url: backendUrl });
        return;
      }

      console.log(`[WARN] Backend responded with HTTP ${res.statusCode}`);
      resolve({ status: 'unhealthy', httpCode: res.statusCode });
    });

    req.on('error', (error) => {
      console.log(`[WARN] Backend health check failed: ${error.message}`);
      resolve({ status: 'unhealthy', error: error.message });
    });

    req.on('timeout', () => {
      req.destroy();
      console.log('[WARN] Backend health check timed out.');
      resolve({ status: 'unhealthy', error: 'timeout' });
    });
  });
}

// IPC handler to check backend health (does not start backend, just checks if it's running)
ipcMain.handle('check-backend-health', async () => {
  return checkBackendHealth(BACKEND_HEALTH_URL);
});

// IPC handler to start backend from renderer
ipcMain.handle('start-backend', async () => {
  try {
    // Kill any existing backend processes first
    console.log("[INFO] Killing existing backend processes...")
    exec('pkill -f "python.*main.py" || true', (err: any) => {
      if (err) {
        console.log(`No existing backend processes found: ${err}`);
      }
    });
    
    // Start the backend from the correct directory
    console.log("[INFO] Starting backend API from renderer request...")
    execFile('python3', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
      cwd: path.join(process.cwd(), '../symmetry-unified-backend'),
      timeout: 10000
    }, (error: any, stdout: any, stderr: any) => {
      if (error) {
        console.error(`Backend exec error: ${error}`);
        return { success: false, error: error.message };
      }
      console.log(`[INFO] Backend API started successfully from renderer!`)
      console.log(`stdout: ${stdout}`);
      console.error(`stderr: ${stderr}`);
    });
    
    return { success: true };
  } catch (error) {
    console.error('Error starting backend from renderer:', error);
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
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
  let backendPath;
  let backendDir;
  if (app.isPackaged) {
    backendPath = path.join(process.resourcesPath, 'main');
    backendDir = path.join(process.resourcesPath, '..');
  } else {
    // For development, run the Python script directly from the correct directory
    backendPath = path.join(process.cwd(), '../symmetry-unified-backend/app/main.py');
    backendDir = path.join(process.cwd(), '../symmetry-unified-backend');
  }
  console.log(`[INFO] backendPath: ${backendPath}`)
  console.log(`[INFO] backendDir: ${backendDir}`)
  
  // Check backend health on startup
  try {
    AppConstants = await grabConfig();
    
    // Kill any existing backend processes first
    console.log("[INFO] Killing existing backend processes...")
    
    // Kill processes on the specific port first
    exec(`lsof -ti:8000 | xargs kill -9 || true`, (err: any, stdout: any, stderr: any) => {
      if (err) {
        console.log(`No processes found on port 8000 or kill command failed: ${err}`);
      }
      
      // Then kill any python main.py processes
      exec('pkill -f "python.*main.py" || true', (err: any, stdout: any, stderr: any) => {
        if (err) {
          console.log(`No existing backend processes found or kill command failed: ${err}`);
        }
        console.log("[INFO] Existing backend processes killed")
        
        // Start the backend from the correct directory
        console.log("[INFO] Starting backend API from correct directory...")
        execFile('python3', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
          cwd: backendDir,
          timeout: 10000
        }, (error: any, stdout: any, stderr: any) => {
          console.log("[INFO] Backend API process started")
          if (error) {
            console.error(`Backend exec error: ${error}`);
            return;
          }
          console.log(`[INFO] Backend API has started on port ${AppConstants.BACKEND_PORT}!`)
          console.log(`stdout: ${stdout}`);
          console.error(`stderr: ${stderr}`);
        });
      });
    });
  }
  
  // Perform a health check on backend
  const health = await checkBackendHealth(BACKEND_HEALTH_URL);
  if (health.status !== 'healthy') {
      console.log(`[WARN] Backend health check failed: Backend may not be running`);
      console.log(`[INFO] Please start backend using: ./start.sh backend`);
  }

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
