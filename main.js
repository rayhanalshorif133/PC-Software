const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execFile } = require('child_process');
const si = require('systeminformation');

let mainWindow = null;
let currentExportProcess = null;
let statsInterval = null;

// Hardware cache
const cachedHardware = {
  cpuBrand: 'Detecting CPU...',
  cpuCores: 1,
  gpus: []
};

// Resolve ffmpeg and ffprobe paths (handling packaged asar)
function getFfmpegPath() {
  let p = require('ffmpeg-static');
  if (p && p.includes('app.asar')) {
    p = p.replace('app.asar', 'app.asar.unpacked');
  }
  return p;
}

function getFfprobePath() {
  let p = require('ffprobe-static').path;
  if (p && p.includes('app.asar')) {
    p = p.replace('app.asar', 'app.asar.unpacked');
  }
  return p;
}

// Initialize system hardware info
async function initHardwareInfo() {
  try {
    const [cpu, gfx] = await Promise.all([si.cpu(), si.graphics()]);
    cachedHardware.cpuBrand = cpu.brand || `${cpu.manufacturer || ''} ${cpu.brand || ''}`.trim() || 'Intel/AMD Processor';
    cachedHardware.cpuCores = cpu.cores || cpu.physicalCores || 4;
    cachedHardware.gpus = (gfx.controllers || []).map(g => ({
      model: g.model || 'Standard Display Adapter',
      vendor: g.vendor || 'GPU Vendor',
      vram: g.vram || g.memoryTotal || 0
    }));
    if (cachedHardware.gpus.length === 0) {
      cachedHardware.gpus.push({
        model: 'Integrated / Dedicated GPU',
        vendor: 'Graphics Controller',
        vram: 0
      });
    }
  } catch (err) {
    console.error('Error querying hardware info:', err);
  }
}

// Fetch live dynamic stats (CPU load, Memory, etc.)
async function getLiveSystemStats() {
  try {
    const [load, mem] = await Promise.all([si.currentLoad(), si.mem()]);
    const cpuLoad = Math.round(load.currentLoad || 0);
    const totalBytes = mem.total || (16 * 1024 * 1024 * 1024);
    const usedBytes = mem.used || (mem.active || 0);
    const freeBytes = mem.free || (totalBytes - usedBytes);
    const usedPercent = Math.round((usedBytes / totalBytes) * 100);

    return {
      cpu: {
        brand: cachedHardware.cpuBrand,
        cores: cachedHardware.cpuCores,
        loadPercent: Math.min(100, Math.max(0, cpuLoad))
      },
      ram: {
        totalBytes,
        usedBytes,
        freeBytes,
        usedPercent: Math.min(100, Math.max(0, usedPercent))
      },
      gpu: cachedHardware.gpus
    };
  } catch (err) {
    console.error('Error fetching live stats:', err);
    return null;
  }
}

function startStatsMonitoring() {
  if (statsInterval) clearInterval(statsInterval);
  statsInterval = setInterval(async () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      const stats = await getLiveSystemStats();
      if (stats) {
        mainWindow.webContents.send('system:stats-update', stats);
      }
    }
  }, 1500);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 980,
    minHeight: 650,
    title: 'CineCut Studio - Video Editor & Splitter',
    backgroundColor: '#0a0d14',
    frame: true,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false // allow loading local video files smoothly
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (statsInterval) {
      clearInterval(statsInterval);
      statsInterval = null;
    }
    if (currentExportProcess) {
      try { currentExportProcess.kill('SIGKILL'); } catch (e) {}
    }
  });
}

app.whenReady().then(async () => {
  await initHardwareInfo();
  createWindow();
  startStatsMonitoring();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (statsInterval) clearInterval(statsInterval);
  if (process.platform !== 'darwin') app.quit();
});

// --- IPC Handlers ---

// System live stats
ipcMain.handle('system:get-stats', async () => {
  return await getLiveSystemStats();
});

// Open Video File Dialog
ipcMain.handle('dialog:open-video', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Video File',
    properties: ['openFile'],
    filters: [
      { name: 'Video Files', extensions: ['mp4', 'mkv', 'mov', 'webm', 'avi', 'flv', 'wmv', 'ts'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Select Output File Dialog
ipcMain.handle('dialog:save-video', async (event, defaultName) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Choose Output File Location',
    defaultPath: defaultName || 'edited_video.mp4',
    filters: [
      { name: 'MP4 Video', extensions: ['mp4'] },
      { name: 'MKV Video', extensions: ['mkv'] },
      { name: 'MOV Video', extensions: ['mov'] }
    ]
  });

  if (result.canceled || !result.filePath) {
    return null;
  }
  return result.filePath;
});

// Select Output Directory Dialog
ipcMain.handle('dialog:select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Output Folder',
    properties: ['openDirectory', 'createDirectory']
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Probe video metadata (duration, resolution, audio streams)
ipcMain.handle('media:probe', async (event, filePath) => {
  return new Promise((resolve, reject) => {
    const ffprobe = getFfprobePath();
    if (!ffprobe || !fs.existsSync(ffprobe)) {
      return reject(new Error('ffprobe executable not found'));
    }

    const args = [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_format',
      '-show_streams',
      filePath
    ];

    execFile(ffprobe, args, { maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
      if (err) {
        return reject(err);
      }
      try {
        const data = JSON.parse(stdout);
        const videoStream = data.streams ? data.streams.find(s => s.codec_type === 'video') : null;
        const audioStream = data.streams ? data.streams.find(s => s.codec_type === 'audio') : null;
        const duration = parseFloat(data.format?.duration || videoStream?.duration || 0);

        let fps = 30;
        if (videoStream && videoStream.r_frame_rate) {
          const parts = videoStream.r_frame_rate.split('/');
          if (parts.length === 2 && Number(parts[1]) > 0) {
            fps = Math.round(Number(parts[0]) / Number(parts[1]));
          }
        }

        resolve({
          duration,
          width: videoStream ? videoStream.width : 0,
          height: videoStream ? videoStream.height : 0,
          fps,
          codec: videoStream ? videoStream.codec_name : 'unknown',
          hasAudio: !!audioStream,
          audioCodec: audioStream ? audioStream.codec_name : null,
          size: data.format?.size ? Number(data.format.size) : 0,
          bitrate: data.format?.bit_rate ? Number(data.format.bit_rate) : 0
        });
      } catch (parseErr) {
        reject(parseErr);
      }
    });
  });
});

// Export and merge video clips
ipcMain.handle('media:export', async (event, { clips, outputPath, settings }) => {
  return new Promise((resolve, reject) => {
    const ffmpeg = getFfmpegPath();
    if (!ffmpeg || !fs.existsSync(ffmpeg)) {
      return reject(new Error('ffmpeg executable not found'));
    }

    if (!clips || clips.length === 0) {
      return reject(new Error('No clips provided to export'));
    }

    if (!outputPath) {
      return reject(new Error('No output path specified'));
    }

    // Calculate total output duration
    let totalTargetDuration = 0;
    clips.forEach(c => {
      const dur = Math.max(0, (c.end - c.start));
      totalTargetDuration += dur;
    });

    if (totalTargetDuration <= 0) {
      return reject(new Error('Invalid clip duration'));
    }

    // Build FFmpeg command
    const inputFiles = [];
    const fileIndexMap = new Map();

    clips.forEach(clip => {
      if (!fileIndexMap.has(clip.filePath)) {
        fileIndexMap.set(clip.filePath, inputFiles.length);
        inputFiles.push(clip.filePath);
      }
    });

    const args = ['-y'];

    // Add inputs
    inputFiles.forEach(file => {
      args.push('-i', file);
    });

    let filterString = '';
    const vOutputs = [];
    const aOutputs = [];

    const hasAudio = settings?.hasAudio !== false;

    clips.forEach((clip, i) => {
      const fileIdx = fileIndexMap.get(clip.filePath);
      const startSec = Math.max(0, clip.start).toFixed(3);
      const endSec = Math.max(clip.start, clip.end).toFixed(3);

      filterString += `[${fileIdx}:v]trim=start=${startSec}:end=${endSec},setpts=PTS-STARTPTS[v${i}]; `;
      vOutputs.push(`[v${i}]`);

      if (hasAudio) {
        filterString += `[${fileIdx}:a]atrim=start=${startSec}:end=${endSec},asetpts=PTS-STARTPTS[a${i}]; `;
        aOutputs.push(`[a${i}]`);
      }
    });

    if (hasAudio) {
      filterString += `${vOutputs.join('')}${aOutputs.join('')}concat=n=${clips.length}:v=1:a=1[outv][outa]`;
    } else {
      filterString += `${vOutputs.join('')}concat=n=${clips.length}:v=1:a=0[outv]`;
    }

    args.push('-filter_complex', filterString);
    args.push('-map', '[outv]');
    if (hasAudio) {
      args.push('-map', '[outa]');
    }

    // Preset & codecs
    const preset = settings?.preset || 'fast';
    args.push('-c:v', 'libx264', '-preset', preset, '-crf', '20');

    // Resolution scaling if requested
    if (settings?.resolution === '1080p') {
      args.push('-vf', 'scale=-2:1080');
    } else if (settings?.resolution === '720p') {
      args.push('-vf', 'scale=-2:720');
    }

    if (hasAudio) {
      args.push('-c:a', 'aac', '-b:a', '192k');
    }

    args.push(outputPath);

    console.log('Spawning FFmpeg:', ffmpeg, args.join(' '));

    const proc = spawn(ffmpeg, args);
    currentExportProcess = proc;

    let stderrBuffer = '';

    proc.stderr.on('data', data => {
      const text = data.toString();
      stderrBuffer += text;

      // Parse progress: time=HH:MM:SS.xx
      const timeMatch = text.match(/time=(\d{2}):(\d{2}):(\d{2}\.\d+)/);
      const speedMatch = text.match(/speed=\s*([\d\.]+)x/);
      const fpsMatch = text.match(/fps=\s*([\d\.]+)/);

      if (timeMatch) {
        const hours = parseFloat(timeMatch[1]);
        const minutes = parseFloat(timeMatch[2]);
        const seconds = parseFloat(timeMatch[3]);
        const currentSec = hours * 3600 + minutes * 60 + seconds;

        const percent = Math.min(99.9, Math.max(0, (currentSec / totalTargetDuration) * 100));

        mainWindow?.webContents.send('export:progress', {
          percent: Number(percent.toFixed(1)),
          currentSeconds: currentSec,
          totalSeconds: totalTargetDuration,
          speed: speedMatch ? speedMatch[1] + 'x' : '1.0x',
          fps: fpsMatch ? fpsMatch[1] : '--',
          status: 'Encoding & merging video...'
        });
      }
    });

    proc.on('error', err => {
      currentExportProcess = null;
      reject(new Error(`Failed to start FFmpeg: ${err.message}`));
    });

    proc.on('close', code => {
      currentExportProcess = null;
      if (code === 0) {
        mainWindow?.webContents.send('export:progress', {
          percent: 100,
          currentSeconds: totalTargetDuration,
          totalSeconds: totalTargetDuration,
          speed: '1.0x',
          fps: '--',
          status: 'Done!'
        });

        let stats = null;
        try {
          stats = fs.statSync(outputPath);
        } catch (e) {}

        resolve({
          success: true,
          outputPath,
          size: stats ? stats.size : 0,
          duration: totalTargetDuration
        });
      } else {
        reject(new Error(`FFmpeg exited with error code ${code}.\n${stderrBuffer.slice(-500)}`));
      }
    });
  });
});

// Cancel active export
ipcMain.handle('media:cancel-export', async () => {
  if (currentExportProcess) {
    try {
      currentExportProcess.kill('SIGKILL');
      currentExportProcess = null;
      return true;
    } catch (e) {
      return false;
    }
  }
  return false;
});

// Reveal file in Explorer
ipcMain.handle('shell:show-item-in-folder', async (event, fullPath) => {
  if (fullPath && fs.existsSync(fullPath)) {
    shell.showItemInFolder(fullPath);
    return true;
  }
  return false;
});

// Open file with default media player
ipcMain.handle('shell:open-path', async (event, fullPath) => {
  if (fullPath && fs.existsSync(fullPath)) {
    await shell.openPath(fullPath);
    return true;
  }
  return false;
});

// Get sample video path if exists
ipcMain.handle('app:get-sample-video', async () => {
  const samplePath = path.join(__dirname, 'test_sample.mp4');
  if (fs.existsSync(samplePath)) {
    return samplePath;
  }
  return null;
});
