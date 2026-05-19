const { contextBridge, ipcRenderer, shell } = require('electron');

const api = {
  pickVideos: () => ipcRenderer.invoke('pick-videos'),
  pickJson: () => ipcRenderer.invoke('pick-json'),
  minimize: () => ipcRenderer.send('win:minimize'),
  maximize: () => ipcRenderer.send('win:maximize'),
  close: () => ipcRenderer.send('win:close'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
};

// App uses both window.nativeApi.* and window.electronAPI.*
contextBridge.exposeInMainWorld('electronAPI', api);
contextBridge.exposeInMainWorld('electronApi', api);
contextBridge.exposeInMainWorld('nativeApi', api);
