/*
Here, you can mention the FASTAPI endpoint
*/
import { app } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';

// Defining our config json interface for type safety
interface AppConfig {
  BACKEND_BASE_URL?: string;
  BACKEND_PORT?: number;
  FRONTEND_PORT?: number;
  OLLAMA_BASE_URL?: string;
  DEFAULT_TIMEOUT?: number;
  SIMILARITY_THRESHOLD?: number;
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

    // Construct and return the constants object with defaults
    const result = {
      BACKEND_BASE_URL: configData.BACKEND_BASE_URL || `http://127.0.0.1:${configData.BACKEND_PORT || 8000}`,
      BACKEND_PORT: configData.BACKEND_PORT || 8000,
      FRONTEND_PORT: configData.FRONTEND_PORT || 5173,
      OLLAMA_BASE_URL: configData.OLLAMA_BASE_URL || 'http://localhost:11434',
      DEFAULT_TIMEOUT: configData.DEFAULT_TIMEOUT || 30000,
      SIMILARITY_THRESHOLD: configData.SIMILARITY_THRESHOLD || 0.65,
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