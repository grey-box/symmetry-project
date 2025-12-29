// See the Electron documentation for details on how to use preload scripts:
// https://www.electronjs.org/docs/latest/tutorial/process-model#preload-scripts

import { contextBridge, ipcRenderer } from 'electron';
import { AppConfig } from './constants/AppConstants'


// Preloads an invokable get-app-config command for the IPC. Allows renderer processes to get the configuration file.
contextBridge.exposeInMainWorld('electronAPI', {
  getAppConfig: () => ipcRenderer.invoke('get-app-config'),
  onConfigUpdated: (callback) => {
    const listener = (_event, config) => callback(config);
    ipcRenderer.on('config-updated', listener);
    return () => {
      ipcRenderer.removeListener('config-updated', listener);
    };
  },
 });