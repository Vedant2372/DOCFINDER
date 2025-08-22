const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let pythonProcess;

function waitForBackend(url, maxAttempts = 20, interval = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          retry();
        }
      }).on('error', retry);
    };

    const retry = () => {
      attempts++;
      if (attempts >= maxAttempts) return reject("❌ Backend failed to start.");
      setTimeout(check, interval);
    };

    check();
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile(path.join(__dirname, 'index.html'));

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(async () => {
  // ✅ Use EXE instead of Python for production
  const isDev = !app.isPackaged;
  const backendPath = isDev
    ? path.join(__dirname, '../connection/app.py')
    : path.join(__dirname, 'backend', 'app.exe');

  console.log(`⚙ Starting backend from: ${backendPath}`);

  pythonProcess = isDev
    ? spawn('python', [backendPath], { shell: true })
    : spawn(backendPath, [], { shell: true });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Backend exited with code ${code}]`);
  });

  // ✅ Wait for backend before launching UI
  try {
    console.log("⏳ Waiting for backend to be ready...");
    await waitForBackend('http://127.0.0.1:5005/');
    console.log("🚀 Backend is ready. Launching UI...");
    createWindow();
  } catch (err) {
    console.error(err);
  }
});

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
