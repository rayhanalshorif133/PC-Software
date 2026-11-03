const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  openVideoDialog: () => ipcRenderer.invoke('dialog:open-video'),
  saveVideoDialog: (defaultName) => ipcRenderer.invoke('dialog:save-video', defaultName),
  selectDirectory: () => ipcRenderer.invoke('dialog:select-directory'),
  probeMedia: (filePath) => ipcRenderer.invoke('media:probe', filePath),
  exportVideo: (payload) => ipcRenderer.invoke('media:export', payload),
  cancelExport: () => ipcRenderer.invoke('media:cancel-export'),
  showItemInFolder: (path) => ipcRenderer.invoke('shell:show-item-in-folder', path),
  openPath: (path) => ipcRenderer.invoke('shell:open-path'),
  getSampleVideo: () => ipcRenderer.invoke('app:get-sample-video'),
  getSystemStats: () => ipcRenderer.invoke('system:get-stats'),
  onSystemStats: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('system:stats-update', handler);
    return () => ipcRenderer.removeListener('system:stats-update', handler);
  },
  onExportProgress: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('export:progress', handler);
    return () => ipcRenderer.removeListener('export:progress', handler);
  }
});
