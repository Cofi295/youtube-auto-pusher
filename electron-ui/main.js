const { app, BrowserWindow, dialog, ipcMain, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const { autoUpdater } = require('electron-updater');

const ROOT = path.resolve(__dirname, '..');
const API_PORT = 8765;

// Auto-update config
autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;

if (app.isPackaged) {
  app.setPath('userData', path.join(path.dirname(process.execPath), 'data'));
}

let apiProcess = null;
let mainWindow = null;
let tray = null;
let isQuitting = false;

function getApiCommand() {
  if (app.isPackaged) {
    return {
      command: path.join(process.resourcesPath, 'backend', 'api_server.exe'),
      args: ['--port', String(API_PORT)],
      cwd: app.getPath('userData'),
    };
  }
  return {
    command: path.join(ROOT, 'venv', 'Scripts', 'python.exe'),
    args: [path.join(ROOT, 'api_server.py'), '--port', String(API_PORT)],
    cwd: ROOT,
  };
}

function startApi() {
  // Kill old Python processes bi tranh loi port conflict (exit code 4294967295)
  try { process.kill(apiProcess.pid); } catch(e) {}
  try { require('child_process').execSync('taskkill /F /IM python.exe >nul 2>&1', {stdio:'ignore'}); } catch(e) {}

  const api = getApiCommand();
  // Dev mode: use project ROOT as data dir (where DB, cache, tokens, config are)
  // Packaged mode: use Electron userData dir
  const dataDir = app.isPackaged ? app.getPath('userData') : ROOT;
  apiProcess = spawn(api.command, api.args, {
    cwd: api.cwd,
    env: {
      ...process.env,
      PYTHONUTF8: '1',
      PYTHONIOENCODING: 'utf-8:replace',
      YTAP_DATA_DIR: dataDir,
    },
    windowsHide: true,
  });
  apiProcess.stdout.on('data', (d) => console.log('[py]', d.toString().trim()));
  apiProcess.stderr.on('data', (d) => console.error('[py err]', d.toString().trim()));
  apiProcess.on('exit', (code) => console.log('[py] exited', code));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    title: 'YouTube Auto Pusher V1.0',
    icon: path.join(__dirname, 'assets', 'app-icon.ico'),
    backgroundColor: '#0b0e17',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Prevent actual close — hide to tray instead
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function createTray() {
  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, 'assets', 'app-icon.jpg')
    : path.join(__dirname, 'assets', 'app-icon.jpg');

  const icon = nativeImage.createFromPath(iconPath);
  tray = new Tray(icon.resize({ width: 16, height: 16 }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Hiện cửa sổ',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      },
    },
    { type: 'separator' },
    {
      label: 'Thoát',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setToolTip('YouTube Auto Pusher');
  tray.setContextMenu(contextMenu);

  // Double-click on tray icon = show window
  tray.on('double-click', () => {
    mainWindow.show();
    mainWindow.focus();
  });
}

// ── IPC: Window controls ──
ipcMain.on('win:minimize', () => mainWindow?.minimize());
ipcMain.on('win:maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('win:close', () => {
  // Hide to system tray instead of closing
  mainWindow?.hide();
});

// ── IPC: File dialogs ──
ipcMain.handle('pick-videos', async () => {
  const result = await dialog.showOpenDialog({
    title: 'Chọn video để đăng',
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Video files', extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'] },
      { name: 'All files', extensions: ['*'] },
    ],
  });
  return result.canceled ? [] : result.filePaths;
});

ipcMain.handle('pick-json', async () => {
  const result = await dialog.showOpenDialog({
    title: 'Chọn OAuth client JSON',
    properties: ['openFile'],
    filters: [
      { name: 'JSON files', extensions: ['json'] },
      { name: 'All files', extensions: ['*'] },
    ],
  });
  return result.canceled ? null : result.filePaths[0];
});

// ── IPC: Open external URL ──
ipcMain.handle('open-external', async (_, url) => {
  const { shell } = require('electron');
  return shell.openExternal(url);
});

// ── App lifecycle ──
app.whenReady().then(() => {
  startApi();
  setTimeout(() => {
    createWindow();
    createTray();
    // Auto-update: chi check khi app da dong goi (packaged)
    if (app.isPackaged) {
      autoUpdater.checkForUpdates().catch(() => {});
    }
  }, 900);
});

autoUpdater.on('update-available', () => {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Cập nhật mới',
    message: 'Đã có phiên bản mới! Bạn có muốn tải về ngay không?',
    buttons: ['Tải ngay', 'Để sau']
  }).then(({ response }) => {
    if (response === 0) autoUpdater.downloadUpdate();
  });
});

autoUpdater.on('update-downloaded', () => {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Sẵn sàng cài đặt',
    message: 'Bản cập nhật đã tải xong. Cài đặt ngay bây giờ?',
    buttons: ['Cài & khởi động lại', 'Để sau']
  }).then(({ response }) => {
    if (response === 0) autoUpdater.quitAndInstall();
  });
});

app.on('window-all-closed', () => {
  // Don't quit — keep running in tray
  if (process.platform !== 'darwin') {
    // On Windows, just keep the process alive with tray
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  if (apiProcess) apiProcess.kill();
});

app.on('activate', () => {
  // macOS: re-create window when dock icon clicked
  if (mainWindow === null) {
    createWindow();
    createTray();
  } else {
    mainWindow.show();
  }
});
