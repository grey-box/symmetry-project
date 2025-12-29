/*
Here, you can mention the FASTAPI endpoint
*/
import { app } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';

// Defining our config json interface for type safety
interface AppConfig {
  port: number;
  backendBaseUrl?: string; // Optional backend URL override
}

// Handles the reading of the json file, run by the main process.
async function initializeConstants(): Promise<any> {
  // Our relative path is different between packaged and non-packaged versions...
  let backendPath;
  if (app.isPackaged) {
    backendPath = path.join(process.resourcesPath, './../config.json');
  } else {
    backendPath = path.join(process.cwd(), './../config.json');
  }

  // Attempt to read the config data and return it.
  try {
    const json = await fs.readFile(backendPath, 'utf-8');
    const configData = JSON.parse(json) as AppConfig;

    if (typeof configData.port === 'undefined') {
        throw new Error("Port is not defined in config.json");
    }

    // Construct and return the constants object
    let result = {
      BACKEND_BASE_URL: configData.backendBaseUrl || `http://127.0.0.1:${configData.port}`,
      BACKEND_PORT: configData.port,
    }
    return result;

  } catch (error) {
    console.error("Failed to load or parse configuration:", error);
    // Propagate the error so consumers of the promise can handle it
    throw new Error(`Failed to initialize AppConstants: ${error instanceof Error ? error.message : String(error)}`);
  }
}

// Export a promise that returns our json data
export const appConstantsPromise: Promise = initializeConstants();