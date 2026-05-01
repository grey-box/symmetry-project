/*
Here, you can mention the FASTAPI endpoint
*/
import { app } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';

export interface ComparisonModelOption {
  value: string;
  label: string;
  description?: string;
}

export interface ArticlePreset {
  label: string;
  url: string;
}

export interface ThresholdPreset {
  label: string;
  value: number;
  description: string;
  speedRange: string;
}

// Defining our config json interface for type safety
export interface AppConfig {
  BACKEND_BASE_URL?: string;
  BACKEND_PORT?: number;
  FRONTEND_PORT?: number;
  OLLAMA_BASE_URL?: string;
  DEFAULT_TIMEOUT?: number;
  SIMILARITY_THRESHOLD?: number;
  COMPARISON_MODELS?: Array<string | ComparisonModelOption>;
  DEFAULT_MODEL?: string;
  PRESELECTED_ARTICLES?: ArticlePreset[];
  THRESHOLD_PRESETS?: ThresholdPreset[];
}

function resolveConfigPaths() {
  if (app.isPackaged) {
    return {
      defaultConfigPath: path.join(process.resourcesPath, './../config.default.json'),
      customConfigPath: path.join(process.resourcesPath, './../config.json'),
    };
  }

  return {
    defaultConfigPath: path.join(process.cwd(), './../config.default.json'),
    customConfigPath: path.join(process.cwd(), './../config.json'),
  };
}

async function loadJsonFile<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(raw) as T;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return null;
    }
    console.warn(`Failed to read config file ${filePath}:`, error);
    return null;
  }
}

// Handles the reading of the json file, run by the main process.
async function initializeConstants(): Promise<AppConfig> {
  const { defaultConfigPath, customConfigPath } = resolveConfigPaths();

  const defaultConfig = (await loadJsonFile<AppConfig>(defaultConfigPath)) || {};
  const customConfig = (await loadJsonFile<AppConfig>(customConfigPath)) || {};
  const configData: AppConfig = {
    ...defaultConfig,
    ...customConfig,
  };

  // Construct and return the constants object with defaults
  return {
    BACKEND_BASE_URL: configData.BACKEND_BASE_URL || `http://127.0.0.1:${configData.BACKEND_PORT || 8000}`,
    BACKEND_PORT: configData.BACKEND_PORT || 8000,
    FRONTEND_PORT: configData.FRONTEND_PORT || 5173,
    OLLAMA_BASE_URL: configData.OLLAMA_BASE_URL || 'http://localhost:11434',
    DEFAULT_TIMEOUT: configData.DEFAULT_TIMEOUT || 30000,
    SIMILARITY_THRESHOLD: configData.SIMILARITY_THRESHOLD || 0.65,
    COMPARISON_MODELS: configData.COMPARISON_MODELS,
    DEFAULT_MODEL: configData.DEFAULT_MODEL || (Array.isArray(configData.COMPARISON_MODELS) && configData.COMPARISON_MODELS.length > 0 ?
      (typeof configData.COMPARISON_MODELS[0] === 'string'
        ? configData.COMPARISON_MODELS[0]
        : configData.COMPARISON_MODELS[0]?.value ?? 'sentence-transformers/LaBSE')
      : 'sentence-transformers/LaBSE'),
    PRESELECTED_ARTICLES: configData.PRESELECTED_ARTICLES,
    THRESHOLD_PRESETS: configData.THRESHOLD_PRESETS,
  };
}

// Export a promise that returns our json data
export const appConstantsPromise: Promise<AppConfig> = initializeConstants();