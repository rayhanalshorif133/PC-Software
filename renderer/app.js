// CineCut Studio - Desktop Video Editor & Splitter Engine

(function () {
  'use strict';

  // --- State ---
  let currentVideoPath = null;
  let videoMeta = null;
  let clips = []; // Array of { id, filePath, start, end }
  let selectedClipId = null;
  let nextClipId = 1;
  let isDraggingPlayhead = false;
  let previewCutMode = true;
  let zoomLevel = 1.0;
  let outputFilePath = '';

  // --- DOM Elements ---
  const emptyCanvasOverlay = document.getElementById('empty-canvas-overlay');
  const playerWrapper = document.getElementById('player-wrapper');
  const video = document.getElementById('video-element');
  
  // Center Play Overlay
  const centerPlayOverlay = document.getElementById('center-play-overlay');
  const centerPlayIcon = document.getElementById('center-play-icon');
  const centerPauseIcon = document.getElementById('center-pause-icon');
  const centerPlayLabel = document.getElementById('center-play-label');

  // Play, Pause, Stop Controls (Timeline Toolbar)
  const btnTimelinePlay = document.getElementById('btn-timeline-play');
  const btnTimelinePause = document.getElementById('btn-timeline-pause');
  const btnTimelineStop = document.getElementById('btn-timeline-stop');

  // Step and Skip Buttons
  const btnStepPrev = document.getElementById('btn-step-prev');
  const btnStepNext = document.getElementById('btn-step-next');
  const btnSkipBack = document.getElementById('btn-skip-back');
  const btnSkipFwd = document.getElementById('btn-skip-fwd');
  const timeCurrent = document.getElementById('time-current');
  const timeTotal = document.getElementById('time-total');
  
  // Scrubber
  const scrubberContainer = document.getElementById('player-scrubber-container');
  const scrubberFill = document.getElementById('player-scrubber-fill');
  const scrubberThumb = document.getElementById('player-scrubber-thumb');

  // Volume & Speed
  const btnMute = document.getElementById('btn-mute');
  const iconVolHigh = document.getElementById('icon-vol-high');
  const iconVolMute = document.getElementById('icon-vol-mute');
  const volumeSlider = document.getElementById('volume-slider');
  const selectSpeed = document.getElementById('select-speed');
  const btnFullscreen = document.getElementById('btn-fullscreen');

  // Split / Delete Actions
  const btnSplitAtPlayhead = document.getElementById('btn-split-at-playhead');
  const btnTimelineSplit = document.getElementById('btn-timeline-split');
  const btnTimelineDelete = document.getElementById('btn-timeline-delete');
  const btnDeleteClip = document.getElementById('btn-delete-clip');
  const btnJumpClipStart = document.getElementById('btn-jump-clip-start');
  const btnMoveLeft = document.getElementById('btn-move-left');
  const btnMoveRight = document.getElementById('btn-move-right');

  // Inspector Elements (Clips)
  const labelFilename = document.getElementById('label-filename');
  const badgeCodec = document.getElementById('badge-codec');
  const metaRes = document.getElementById('meta-res');
  const metaFps = document.getElementById('meta-fps');
  const metaDuration = document.getElementById('meta-duration');
  const metaSize = document.getElementById('meta-size');

  const labelClipIndex = document.getElementById('label-clip-index');
  const inputClipStart = document.getElementById('input-clip-start');
  const inputClipEnd = document.getElementById('input-clip-end');
  const labelClipDuration = document.getElementById('label-clip-duration');

  const summaryClipsCount = document.getElementById('summary-clips-count');
  const summaryOrigLen = document.getElementById('summary-orig-len');
  const summaryNewLen = document.getElementById('summary-new-len');
  const summaryCutTime = document.getElementById('summary-cut-time');

  // Timeline
  const timelineViewport = document.getElementById('timeline-viewport');
  const rulerCanvas = document.getElementById('ruler-canvas');
  const timelineTracks = document.getElementById('timeline-tracks');
  const clipsLane = document.getElementById('clips-lane');
  const playhead = document.getElementById('playhead');
  const timelineZoom = document.getElementById('timeline-zoom');
  const togglePreviewMode = document.getElementById('toggle-preview-mode');

  // Header buttons
  const btnOpenVideo = document.getElementById('btn-open-video');
  const btnBrowseFile = document.getElementById('btn-browse-file');
  const btnSampleVideo = document.getElementById('btn-sample-video');
  const btnSampleDrop = document.getElementById('btn-sample-drop');
  const btnReset = document.getElementById('btn-reset');
  const btnExportModal = document.getElementById('btn-export-modal');

  // Header mini PC stats
  const headerPcStats = document.getElementById('header-pc-stats');
  const hdrCpuVal = document.getElementById('hdr-cpu-val');
  const hdrRamVal = document.getElementById('hdr-ram-val');
  const hdrGpuVal = document.getElementById('hdr-gpu-val');

  // Sidebar Tabs
  const tabBtnPc = document.getElementById('tab-btn-pc');
  const tabBtnClips = document.getElementById('tab-btn-clips');
  const tabContentPc = document.getElementById('tab-content-pc');
  const tabContentClips = document.getElementById('tab-content-clips');

  // PC Hardware Monitor DOM
  const capacityBadge = document.getElementById('capacity-badge');
  const capacitySubtext = document.getElementById('capacity-subtext');

  const cpuBrandLabel = document.getElementById('cpu-brand-label');
  const cpuLoadNum = document.getElementById('cpu-load-num');
  const cpuMeterFill = document.getElementById('cpu-meter-fill');
  const cpuCoresText = document.getElementById('cpu-cores-text');
  const cpuLoadState = document.getElementById('cpu-load-state');

  const ramTotalLabel = document.getElementById('ram-total-label');
  const ramLoadNum = document.getElementById('ram-load-num');
  const ramMeterFill = document.getElementById('ram-meter-fill');
  const ramUsedText = document.getElementById('ram-used-text');
  const ramFreeText = document.getElementById('ram-free-text');

  const gpuModelLabel = document.getElementById('gpu-model-label');
  const gpuVendorBadge = document.getElementById('gpu-vendor-badge');
  const gpuVramText = document.getElementById('gpu-vram-text');
  const gpuStatusText = document.getElementById('gpu-status-text');

  // Modal elements
  const exportModal = document.getElementById('export-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const exportFormState = document.getElementById('export-form-state');
  const exportProgressState = document.getElementById('export-progress-state');
  const exportSuccessState = document.getElementById('export-success-state');

  const inputOutputPath = document.getElementById('input-output-path');
  const btnBrowseOutput = document.getElementById('btn-browse-output');
  const exportPreset = document.getElementById('export-preset');
  const exportResolution = document.getElementById('export-resolution');
  const modalClipCount = document.getElementById('modal-clip-count');
  const modalFinalDuration = document.getElementById('modal-final-duration');
  const modalTimeSaved = document.getElementById('modal-time-saved');
  const btnStartExport = document.getElementById('btn-start-export');

  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressPercentText = document.getElementById('progress-percent-text');
  const progressStatusText = document.getElementById('progress-status-text');
  const pstatTime = document.getElementById('pstat-time');
  const pstatSpeed = document.getElementById('pstat-speed');
  const pstatFps = document.getElementById('pstat-fps');
  const btnAbortExport = document.getElementById('btn-abort-export');

  const successFilePath = document.getElementById('success-file-path');
  const successSize = document.getElementById('success-size');
  const successDur = document.getElementById('success-dur');
  const btnRevealFile = document.getElementById('btn-reveal-file');
  const btnPlayExported = document.getElementById('btn-play-exported');
  const btnFinishModal = document.getElementById('btn-finish-modal');

  let currentExportFilePath = null;

  // --- Helper Functions ---

  function formatTime(seconds, includeMs = true) {
    if (isNaN(seconds) || seconds < 0) seconds = 0;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);

    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    const msStr = String(ms).padStart(2, '0');

    if (h > 0) {
      const hh = String(h).padStart(2, '0');
      return includeMs ? `${hh}:${mm}:${ss}.${msStr}` : `${hh}:${mm}:${ss}`;
    }
    return includeMs ? `${mm}:${ss}.${msStr}` : `${mm}:${ss}`;
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(1) + ' MB';
  }

  function bytesToGB(bytes) {
    if (!bytes || bytes <= 0) return '0.0';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1);
  }

  // --- Tab Switching Logic ---

  function switchTab(target) {
    if (target === 'pc') {
      tabBtnPc.classList.add('active');
      tabBtnClips.classList.remove('active');
      tabContentPc.classList.add('active');
      tabContentClips.classList.remove('active');
    } else {
      tabBtnClips.classList.add('active');
      tabBtnPc.classList.remove('active');
      tabContentClips.classList.add('active');
      tabContentPc.classList.remove('active');
    }
  }

  tabBtnPc.addEventListener('click', () => switchTab('pc'));
  tabBtnClips.addEventListener('click', () => switchTab('clips'));
  if (headerPcStats) {
    headerPcStats.addEventListener('click', () => switchTab('pc'));
  }

  // --- Real-Time PC Hardware Stats Handler ---

  function updateSystemStatsUI(stats) {
    if (!stats) return;

    // 1. CPU
    const cpuLoad = stats.cpu.loadPercent;
    hdrCpuVal.textContent = `${cpuLoad}%`;
    cpuLoadNum.textContent = `${cpuLoad}%`;
    cpuMeterFill.style.width = `${cpuLoad}%`;

    if (stats.cpu.brand) {
      cpuBrandLabel.textContent = stats.cpu.brand;
    }
    cpuCoresText.textContent = `${stats.cpu.cores} Cores`;

    if (cpuLoad < 50) {
      cpuLoadState.textContent = 'Normal';
      cpuLoadState.className = 'load-state-text text-green';
      hdrCpuVal.style.color = '#38bdf8';
    } else if (cpuLoad < 80) {
      cpuLoadState.textContent = 'Moderate';
      cpuLoadState.className = 'load-state-text text-warning';
      hdrCpuVal.style.color = '#f59e0b';
    } else {
      cpuLoadState.textContent = 'High Load';
      cpuLoadState.className = 'load-state-text text-danger';
      hdrCpuVal.style.color = '#ef4444';
    }

    // 2. RAM
    const ramPct = stats.ram.usedPercent;
    hdrRamVal.textContent = `${ramPct}%`;
    ramLoadNum.textContent = `${ramPct}%`;
    ramMeterFill.style.width = `${ramPct}%`;

    const totalGB = bytesToGB(stats.ram.totalBytes);
    const usedGB = bytesToGB(stats.ram.usedBytes);
    const freeGB = bytesToGB(stats.ram.freeBytes);

    ramTotalLabel.textContent = `${totalGB} GB Total RAM`;
    ramUsedText.textContent = `${usedGB} GB Used`;
    ramFreeText.textContent = `${freeGB} GB Free`;

    // 3. GPU
    if (stats.gpu && stats.gpu.length > 0) {
      const primaryGpu = stats.gpu[0];
      gpuModelLabel.textContent = primaryGpu.model || 'Display Adapter';
      hdrGpuVal.textContent = primaryGpu.model.replace(/NVIDIA|GeForce|AMD|Radeon|Intel|Graphics/gi, '').trim() || 'Active';
      gpuVendorBadge.textContent = (primaryGpu.vendor || 'GPU').toUpperCase();

      if (primaryGpu.vram && primaryGpu.vram > 0) {
        if (primaryGpu.vram >= 1024) {
          gpuVramText.textContent = `${(primaryGpu.vram / 1024).toFixed(1)} GB VRAM`;
        } else {
          gpuVramText.textContent = `${primaryGpu.vram} MB VRAM`;
        }
      } else {
        gpuVramText.textContent = 'Shared Memory';
      }
      gpuStatusText.textContent = 'Active (Ready)';
    }

    // 4. Overall Capacity Evaluation
    const totalRamNum = parseFloat(totalGB);
    if (totalRamNum >= 15 && stats.cpu.cores >= 4) {
      capacityBadge.textContent = 'Excellent for 1080p & 4K';
      capacityBadge.className = 'capacity-tag tag-good';
      capacitySubtext.textContent = 'System has high CPU & RAM capacity for ultra-fast frame cutting and export.';
    } else if (totalRamNum >= 7) {
      capacityBadge.textContent = 'Great for 1080p';
      capacityBadge.className = 'capacity-tag tag-good';
      capacitySubtext.textContent = 'Comfortable headroom for 1080p HD video cutting and rendering.';
    } else {
      capacityBadge.textContent = 'Standard Entry Capacity';
      capacityBadge.className = 'capacity-tag tag-warning';
      capacitySubtext.textContent = 'Suitable for 720p or lightweight clips.';
    }
  }

  // Hook into live hardware listener
  if (window.api && window.api.onSystemStats) {
    window.api.onSystemStats(updateSystemStatsUI);
    window.api.getSystemStats().then(updateSystemStatsUI).catch(console.error);
  }

  // --- Load Video Handler ---

  async function loadVideo(filePath) {
    if (!filePath) return;
    try {
      console.log('Loading video:', filePath);
      const meta = await window.api.probeMedia(filePath);
      console.log('Probe metadata:', meta);

      currentVideoPath = filePath;
      videoMeta = meta;

      // Reset clips
      clips = [
        {
          id: nextClipId++,
          filePath: filePath,
          start: 0,
          end: meta.duration
        }
      ];
      selectedClipId = clips[0].id;

      // Update UI displays
      const fileName = filePath.split(/[\\/]/).pop();
      labelFilename.textContent = fileName;
      labelFilename.title = filePath;
      badgeCodec.textContent = meta.codec.toUpperCase();
      metaRes.textContent = `${meta.width} x ${meta.height}`;
      metaFps.textContent = `${meta.fps} fps`;
      metaDuration.textContent = formatTime(meta.duration, false);
      metaSize.textContent = formatBytes(meta.size);

      // Load into HTML5 video player
      const fileUrl = 'file:///' + filePath.replace(/\\/g, '/');
      video.src = fileUrl;
      video.load();

      // Hide empty canvas overlay, show center play button
      emptyCanvasOverlay.classList.add('hidden');
      centerPlayOverlay.classList.remove('hidden');

      // Enable actions
      btnReset.disabled = false;
      btnExportModal.disabled = false;

      // Pre-set default output path
      const baseDir = filePath.substring(0, filePath.lastIndexOf('\\') + 1) || filePath.substring(0, filePath.lastIndexOf('/') + 1);
      const pureName = fileName.includes('.') ? fileName.substring(0, fileName.lastIndexOf('.')) : fileName;
      outputFilePath = `${baseDir}${pureName}_edited.mp4`;
      inputOutputPath.value = outputFilePath;

      updateSummary();
      renderTimeline();

      // Switch to Clips inspector tab so user sees video stats
      switchTab('clips');

      // Update Play/Pause button states
      updatePlayPauseState(false);

    } catch (err) {
      alert(`Error opening video:\n${err.message}`);
    }
  }

  // --- Video Event Handlers ---

  video.addEventListener('loadedmetadata', () => {
    timeTotal.textContent = formatTime(video.duration);
    timeCurrent.textContent = formatTime(0);
    renderTimeline();
    updatePlayPauseState(false);
  });

  video.addEventListener('timeupdate', () => {
    if (isDraggingPlayhead) return;

    const currentTime = video.currentTime;
    timeCurrent.textContent = formatTime(currentTime);

    // Update scrubber
    if (video.duration > 0) {
      const pct = (currentTime / video.duration) * 100;
      scrubberFill.style.width = `${pct}%`;
      scrubberThumb.style.left = `${pct}%`;
    }

    // Live preview edit cut mode:
    if (previewCutMode && !video.paused && clips.length > 0) {
      const currentActiveClip = getCurrentClipAtTime(currentTime);

      if (!currentActiveClip) {
        // In a deleted / cut-out region: jump to next clip
        const nextClip = clips.find(c => c.start > currentTime);
        if (nextClip) {
          video.currentTime = nextClip.start;
          selectClip(nextClip.id);
        } else {
          // Reached end of all clips
          video.pause();
          updatePlayPauseState(false);
          if (clips.length > 0) {
            video.currentTime = clips[0].start;
            selectClip(clips[0].id);
          }
        }
      } else {
        // At the very end of the current clip
        if (currentTime >= currentActiveClip.end - 0.05) {
          const currentIdx = clips.findIndex(c => c.id === currentActiveClip.id);
          if (currentIdx < clips.length - 1) {
            const nextClip = clips[currentIdx + 1];
            video.currentTime = nextClip.start;
            selectClip(nextClip.id);
          } else {
            video.pause();
            updatePlayPauseState(false);
          }
        } else {
          if (selectedClipId !== currentActiveClip.id) {
            selectClip(currentActiveClip.id);
          }
        }
      }
    }

    updatePlayheadPosition();
  });

  function getCurrentClipAtTime(time) {
    return clips.find(c => time >= c.start && time < c.end);
  }

  function updatePlayheadPosition() {
    if (!videoMeta || videoMeta.duration <= 0) return;
    const laneWidth = clipsLane.scrollWidth;
    const pct = Math.min(1, Math.max(0, video.currentTime / videoMeta.duration));
    const leftPx = pct * laneWidth;
    playhead.style.left = `${leftPx}px`;
  }

  // --- SEPARATE DEDICATED PLAY, PAUSE, STOP CONTROLS ---

  function playVideo() {
    if (!video.src || !currentVideoPath) {
      // If no video loaded, load sample video automatically so Play works!
      handleLoadSample();
      return;
    }

    if (video.paused || video.ended) {
      if (clips.length > 0) {
        const lastClip = clips[clips.length - 1];
        if (video.currentTime >= lastClip.end - 0.05) {
          video.currentTime = clips[0].start;
        }
      }
      video.play().catch(e => console.log('Autoplay check:', e));
      updatePlayPauseState(true);
    }
  }

  function pauseVideo() {
    if (!video.src) return;
    video.pause();
    updatePlayPauseState(false);
  }

  function stopVideo() {
    if (!video.src) return;
    video.pause();
    const resetTime = (clips.length > 0 ? clips[0].start : 0);
    video.currentTime = resetTime;
    timeCurrent.textContent = formatTime(resetTime);
    updatePlayPauseState(false);
    updatePlayheadPosition();
  }

  function togglePlayPause() {
    if (video.paused || video.ended) {
      playVideo();
    } else {
      pauseVideo();
    }
  }

  function updatePlayPauseState(isPlaying) {
    if (isPlaying) {
      if (btnTimelinePlay) btnTimelinePlay.classList.add('is-active');
      if (btnTimelinePause) btnTimelinePause.classList.remove('is-active');

      // Center Overlay Icon
      centerPlayIcon.classList.add('hidden');
      centerPauseIcon.classList.remove('hidden');
      centerPlayLabel.textContent = 'Click to Pause (Space)';
      centerPlayOverlay.classList.remove('show-overlay');
      centerPlayOverlay.classList.remove('force-show');
    } else {
      if (btnTimelinePlay) btnTimelinePlay.classList.remove('is-active');
      if (btnTimelinePause) btnTimelinePause.classList.add('is-active');

      // Center Overlay Icon
      centerPlayIcon.classList.remove('hidden');
      centerPauseIcon.classList.add('hidden');
      centerPlayLabel.textContent = 'Click to Play (Space)';
      if (currentVideoPath) {
        centerPlayOverlay.classList.add('show-overlay');
      }
    }
  }

  // Hook up Play, Pause, Stop buttons
  if (btnTimelinePlay) btnTimelinePlay.addEventListener('click', playVideo);
  if (btnTimelinePause) btnTimelinePause.addEventListener('click', pauseVideo);
  if (btnTimelineStop) btnTimelineStop.addEventListener('click', stopVideo);

  centerPlayOverlay.addEventListener('click', togglePlayPause);
  video.addEventListener('click', togglePlayPause);

  video.addEventListener('play', () => updatePlayPauseState(true));
  video.addEventListener('pause', () => updatePlayPauseState(false));

  // Step frames (approx 1 frame = 1/30 sec)
  const FRAME_STEP = 1 / 30;

  btnStepPrev.addEventListener('click', () => {
    video.pause();
    video.currentTime = Math.max(0, video.currentTime - FRAME_STEP);
  });

  btnStepNext.addEventListener('click', () => {
    video.pause();
    video.currentTime = Math.min(video.duration, video.currentTime + FRAME_STEP);
  });

  btnSkipBack.addEventListener('click', () => {
    video.currentTime = Math.max(0, video.currentTime - 5);
  });

  btnSkipFwd.addEventListener('click', () => {
    video.currentTime = Math.min(video.duration, video.currentTime + 5);
  });

  // Scrubber seeking
  scrubberContainer.addEventListener('click', (e) => {
    if (!video.duration) return;
    const rect = scrubberContainer.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    video.currentTime = ratio * video.duration;
  });

  // Volume
  volumeSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    video.volume = val;
    video.muted = (val === 0);
    updateVolumeIcon();
  });

  btnMute.addEventListener('click', () => {
    video.muted = !video.muted;
    if (video.muted) {
      volumeSlider.value = 0;
    } else {
      volumeSlider.value = video.volume > 0 ? video.volume : 0.8;
      video.volume = volumeSlider.value;
    }
    updateVolumeIcon();
  });

  function updateVolumeIcon() {
    if (video.muted || video.volume === 0) {
      iconVolHigh.classList.add('hidden');
      iconVolMute.classList.remove('hidden');
    } else {
      iconVolHigh.classList.remove('hidden');
      iconVolMute.classList.add('hidden');
    }
  }

  // Speed
  selectSpeed.addEventListener('change', (e) => {
    video.playbackRate = parseFloat(e.target.value);
  });

  // Fullscreen
  btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      playerWrapper.requestFullscreen().catch(err => alert(err.message));
    } else {
      document.exitFullscreen();
    }
  });

  // --- Splitting & Trimming Logic ---

  function splitAtPlayhead() {
    if (!videoMeta || clips.length === 0) {
      showToast('Please open a video before splitting');
      return;
    }

    const currentT = video.currentTime;
    const clipIndex = clips.findIndex(c => currentT > c.start + 0.05 && currentT < c.end - 0.05);

    if (clipIndex === -1) {
      showToast('Cannot split here: move playhead inside a clip (at least 0.05s from edges)');
      return;
    }

    const targetClip = clips[clipIndex];

    const clipA = {
      id: nextClipId++,
      filePath: targetClip.filePath,
      start: targetClip.start,
      end: currentT
    };

    const clipB = {
      id: nextClipId++,
      filePath: targetClip.filePath,
      start: currentT,
      end: targetClip.end
    };

    clips.splice(clipIndex, 1, clipA, clipB);
    selectedClipId = clipB.id;

    updateSummary();
    renderTimeline();
    switchTab('clips');
    showToast(`Split successfully into 2 clips at ${formatTime(currentT)}`);
  }

  btnSplitAtPlayhead.addEventListener('click', splitAtPlayhead);
  btnTimelineSplit.addEventListener('click', splitAtPlayhead);

  // Delete selected clip
  function deleteSelectedClip() {
    if (!selectedClipId || clips.length === 0) return;

    if (clips.length === 1) {
      if (!confirm('This is the only clip remaining. Deleting it will leave the timeline empty. Proceed?')) {
        return;
      }
    }

    const idx = clips.findIndex(c => c.id === selectedClipId);
    if (idx === -1) return;

    const deleted = clips.splice(idx, 1)[0];

    if (clips.length > 0) {
      const nextIdx = Math.min(idx, clips.length - 1);
      selectedClipId = clips[nextIdx].id;
      video.currentTime = clips[nextIdx].start;
    } else {
      selectedClipId = null;
    }

    updateSummary();
    renderTimeline();
    showToast(`Clip deleted (${formatTime(deleted.start)} - ${formatTime(deleted.end)})`);
  }

  btnDeleteClip.addEventListener('click', deleteSelectedClip);
  btnTimelineDelete.addEventListener('click', deleteSelectedClip);

  // Move clip left / right
  btnMoveLeft.addEventListener('click', () => {
    if (!selectedClipId) return;
    const idx = clips.findIndex(c => c.id === selectedClipId);
    if (idx > 0) {
      const temp = clips[idx - 1];
      clips[idx - 1] = clips[idx];
      clips[idx] = temp;
      renderTimeline();
      updateSummary();
    }
  });

  btnMoveRight.addEventListener('click', () => {
    if (!selectedClipId) return;
    const idx = clips.findIndex(c => c.id === selectedClipId);
    if (idx < clips.length - 1) {
      const temp = clips[idx + 1];
      clips[idx + 1] = clips[idx];
      clips[idx] = temp;
      renderTimeline();
      updateSummary();
    }
  });

  btnJumpClipStart.addEventListener('click', () => {
    const clip = clips.find(c => c.id === selectedClipId);
    if (clip) {
      video.currentTime = clip.start;
    }
  });

  // Manual clip time adjustments
  inputClipStart.addEventListener('change', (e) => {
    const clip = clips.find(c => c.id === selectedClipId);
    if (!clip) return;
    const val = Math.max(0, parseFloat(e.target.value) || 0);
    if (val < clip.end) {
      clip.start = val;
      updateSummary();
      renderTimeline();
    } else {
      e.target.value = clip.start.toFixed(2);
    }
  });

  inputClipEnd.addEventListener('change', (e) => {
    const clip = clips.find(c => c.id === selectedClipId);
    if (!clip) return;
    const val = Math.min(videoMeta.duration, parseFloat(e.target.value) || clip.end);
    if (val > clip.start) {
      clip.end = val;
      updateSummary();
      renderTimeline();
    } else {
      e.target.value = clip.end.toFixed(2);
    }
  });

  // Reset all cuts
  btnReset.addEventListener('click', () => {
    if (!currentVideoPath || !videoMeta) return;
    if (confirm('Reset all splits and restore original uncut video?')) {
      clips = [
        {
          id: nextClipId++,
          filePath: currentVideoPath,
          start: 0,
          end: videoMeta.duration
        }
      ];
      selectedClipId = clips[0].id;
      video.currentTime = 0;
      updateSummary();
      renderTimeline();
    }
  });

  // --- Timeline Rendering ---

  function renderTimeline() {
    if (!videoMeta || videoMeta.duration <= 0) {
      clipsLane.innerHTML = '<div class="empty-lane-placeholder">Open a video above to see interactive clips timeline</div>';
      return;
    }

    clipsLane.innerHTML = '';

    const totalDur = videoMeta.duration;
    const zoom = zoomLevel;
    const baseWidth = timelineViewport.clientWidth - 32;
    const totalTrackWidth = Math.max(baseWidth, baseWidth * zoom);

    clipsLane.style.width = `${totalTrackWidth}px`;
    timelineTracks.style.width = `${totalTrackWidth}px`;
    rulerCanvas.width = totalTrackWidth;
    rulerCanvas.height = 28;

    drawRuler(totalTrackWidth, totalDur);

    // Render clips
    clips.forEach((clip, index) => {
      const clipDuration = clip.end - clip.start;
      const widthPct = (clipDuration / totalDur);
      const widthPx = Math.max(70, widthPct * totalTrackWidth);

      const clipEl = document.createElement('div');
      clipEl.className = 'timeline-clip' + (clip.id === selectedClipId ? ' selected' : '');
      clipEl.style.width = `${widthPx}px`;

      clipEl.innerHTML = `
        <div class="clip-header-row">
          <span class="clip-title-text" title="Clip ${index + 1}">Clip ${index + 1}</span>
          <button class="clip-del-btn" title="Delete this clip" data-clip-id="${clip.id}">×</button>
        </div>
        <div class="clip-waveform-sim"></div>
        <div class="clip-footer-row">
          <span>${formatTime(clip.start, false)}</span>
          <span class="clip-duration-pill">${clipDuration.toFixed(1)}s</span>
          <span>${formatTime(clip.end, false)}</span>
        </div>
      `;

      clipEl.addEventListener('click', (e) => {
        if (e.target.closest('.clip-del-btn')) {
          e.stopPropagation();
          selectedClipId = clip.id;
          deleteSelectedClip();
          return;
        }
        selectClip(clip.id);
        video.currentTime = clip.start;
        switchTab('clips');
      });

      clipsLane.appendChild(clipEl);
    });

    updateSelectedClipCard();
    updatePlayheadPosition();
  }

  function selectClip(clipId) {
    selectedClipId = clipId;
    document.querySelectorAll('.timeline-clip').forEach(el => el.classList.remove('selected'));
    
    const idx = clips.findIndex(c => c.id === clipId);
    if (idx !== -1) {
      const clipEls = clipsLane.querySelectorAll('.timeline-clip');
      if (clipEls[idx]) clipEls[idx].classList.add('selected');
    }
    updateSelectedClipCard();
  }

  function updateSelectedClipCard() {
    const clip = clips.find(c => c.id === selectedClipId);
    if (!clip) {
      labelClipIndex.textContent = '--';
      inputClipStart.value = '0.00';
      inputClipEnd.value = '0.00';
      labelClipDuration.textContent = '0.00s';
      btnDeleteClip.disabled = true;
      btnMoveLeft.disabled = true;
      btnMoveRight.disabled = true;
      return;
    }

    const idx = clips.findIndex(c => c.id === clip.id);
    labelClipIndex.textContent = `Clip #${idx + 1} of ${clips.length}`;
    inputClipStart.value = clip.start.toFixed(2);
    inputClipEnd.value = clip.end.toFixed(2);
    labelClipDuration.textContent = `${(clip.end - clip.start).toFixed(2)}s`;

    btnDeleteClip.disabled = false;
    btnMoveLeft.disabled = (idx === 0);
    btnMoveRight.disabled = (idx === clips.length - 1);
  }

  function updateSummary() {
    summaryClipsCount.textContent = clips.length;
    modalClipCount.textContent = `${clips.length} clip${clips.length === 1 ? '' : 's'}`;

    if (!videoMeta) {
      summaryOrigLen.textContent = '00:00.00';
      summaryNewLen.textContent = '00:00.00';
      summaryCutTime.textContent = '-00:00.00 (0%)';
      return;
    }

    const origDur = videoMeta.duration;
    summaryOrigLen.textContent = formatTime(origDur);

    let newDur = 0;
    clips.forEach(c => {
      newDur += Math.max(0, (c.end - c.start));
    });

    summaryNewLen.textContent = formatTime(newDur);
    modalFinalDuration.textContent = formatTime(newDur);

    const saved = Math.max(0, origDur - newDur);
    const savedPct = origDur > 0 ? Math.round((saved / origDur) * 100) : 0;
    summaryCutTime.textContent = `-${formatTime(saved)} (${savedPct}%)`;
    modalTimeSaved.textContent = `-${formatTime(saved)} (${savedPct}%)`;
  }

  function drawRuler(width, duration) {
    const ctx = rulerCanvas.getContext('2d');
    ctx.clearRect(0, 0, width, 28);

    ctx.fillStyle = '#64748b';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.strokeStyle = '#212c44';
    ctx.lineWidth = 1;

    let stepSec = 5;
    if (duration > 600) stepSec = 30;
    else if (duration > 180) stepSec = 15;
    else if (duration < 30) stepSec = 1;
    else if (duration < 60) stepSec = 2;

    const pixelsPerSec = width / duration;

    for (let sec = 0; sec <= duration; sec += stepSec) {
      const x = sec * pixelsPerSec;
      ctx.beginPath();
      ctx.moveTo(x, 18);
      ctx.lineTo(x, 28);
      ctx.stroke();

      ctx.fillText(formatTime(sec, false), x + 4, 14);

      const subTicks = 4;
      for (let j = 1; j < subTicks; j++) {
        const subSec = sec + (j * (stepSec / subTicks));
        if (subSec < duration) {
          const subX = subSec * pixelsPerSec;
          ctx.beginPath();
          ctx.moveTo(subX, 22);
          ctx.lineTo(subX, 28);
          ctx.stroke();
        }
      }
    }
  }

  // Timeline Click / Drag scrubbing
  timelineTracks.addEventListener('mousedown', handleTimelineClickOrDrag);
  rulerCanvas.addEventListener('mousedown', handleTimelineClickOrDrag);

  function handleTimelineClickOrDrag(e) {
    if (!videoMeta || videoMeta.duration <= 0) return;
    isDraggingPlayhead = true;
    seekTimelineFromEvent(e);

    function onMouseMove(moveEvent) {
      if (isDraggingPlayhead) {
        seekTimelineFromEvent(moveEvent);
      }
    }

    function onMouseUp() {
      isDraggingPlayhead = false;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    }

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function seekTimelineFromEvent(e) {
    const rect = clipsLane.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const totalWidth = clipsLane.scrollWidth;
    const ratio = Math.max(0, Math.min(1, clickX / totalWidth));
    const targetTime = ratio * videoMeta.duration;

    video.currentTime = targetTime;
    timeCurrent.textContent = formatTime(targetTime);
    updatePlayheadPosition();
  }

  timelineZoom.addEventListener('input', (e) => {
    zoomLevel = parseFloat(e.target.value);
    renderTimeline();
  });

  togglePreviewMode.addEventListener('change', (e) => {
    previewCutMode = e.target.checked;
  });

  // --- Keyboard Shortcuts ---

  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;

    if (e.code === 'Space') {
      e.preventDefault();
      togglePlayPause();
    } else if (e.code === 'KeyS') {
      e.preventDefault();
      splitAtPlayhead();
    } else if (e.code === 'Delete' || e.code === 'Backspace') {
      e.preventDefault();
      deleteSelectedClip();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      video.currentTime = Math.max(0, video.currentTime - (e.shiftKey ? 1 : 5));
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      video.currentTime = Math.min(video.duration, video.currentTime + (e.shiftKey ? 1 : 5));
    } else if (e.code === 'KeyM') {
      btnMute.click();
    }
  });

  // --- Open Video File Handlers ---

  async function handleOpenDialog() {
    const path = await window.api.openVideoDialog();
    if (path) {
      await loadVideo(path);
    }
  }

  btnOpenVideo.addEventListener('click', handleOpenDialog);
  btnBrowseFile.addEventListener('click', handleOpenDialog);

  async function handleLoadSample() {
    const sample = await window.api.getSampleVideo();
    if (sample) {
      await loadVideo(sample);
    } else {
      alert('Sample test video not found on disk. Please open your own video file.');
    }
  }

  btnSampleVideo.addEventListener('click', handleLoadSample);
  if (btnSampleDrop) {
    btnSampleDrop.addEventListener('click', handleLoadSample);
  }

  // Drag & drop onto empty canvas overlay or window
  emptyCanvasOverlay.addEventListener('dragover', (e) => {
    e.preventDefault();
    emptyCanvasOverlay.classList.add('dragover');
  });

  emptyCanvasOverlay.addEventListener('dragleave', () => {
    emptyCanvasOverlay.classList.remove('dragover');
  });

  emptyCanvasOverlay.addEventListener('drop', (e) => {
    e.preventDefault();
    emptyCanvasOverlay.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file && file.path) {
        loadVideo(file.path);
      }
    }
  });

  // --- Export Modal & Conversion Logic ---

  btnExportModal.addEventListener('click', () => {
    if (clips.length === 0) {
      alert('No clips on timeline to export.');
      return;
    }
    exportFormState.classList.remove('hidden');
    exportProgressState.classList.add('hidden');
    exportSuccessState.classList.add('hidden');
    exportModal.classList.remove('hidden');
    updateSummary();
  });

  btnCloseModal.addEventListener('click', () => {
    exportModal.classList.add('hidden');
  });

  btnCancelModal.addEventListener('click', () => {
    exportModal.classList.add('hidden');
  });

  btnFinishModal.addEventListener('click', () => {
    exportModal.classList.add('hidden');
  });

  btnBrowseOutput.addEventListener('click', async () => {
    const chosen = await window.api.saveVideoDialog(outputFilePath);
    if (chosen) {
      outputFilePath = chosen;
      inputOutputPath.value = chosen;
    }
  });

  btnStartExport.addEventListener('click', async () => {
    if (!outputFilePath) {
      const chosen = await window.api.saveVideoDialog();
      if (!chosen) return;
      outputFilePath = chosen;
      inputOutputPath.value = chosen;
    }

    if (clips.length === 0) {
      alert('Please have at least 1 clip on timeline.');
      return;
    }

    exportFormState.classList.add('hidden');
    exportProgressState.classList.remove('hidden');
    exportSuccessState.classList.add('hidden');

    progressBarFill.style.width = '0%';
    progressPercentText.textContent = '0%';
    progressStatusText.textContent = 'Initializing FFmpeg encoder...';
    pstatTime.textContent = '00:00 / 00:00';
    pstatSpeed.textContent = '--';
    pstatFps.textContent = '--';

    const payload = {
      clips: clips.map(c => ({
        filePath: c.filePath,
        start: c.start,
        end: c.end
      })),
      outputPath: outputFilePath,
      settings: {
        preset: exportPreset.value,
        resolution: exportResolution.value,
        hasAudio: videoMeta ? videoMeta.hasAudio : true
      }
    };

    try {
      const result = await window.api.exportVideo(payload);
      currentExportFilePath = result.outputPath;

      exportProgressState.classList.add('hidden');
      exportSuccessState.classList.remove('hidden');

      successFilePath.textContent = result.outputPath;
      successSize.textContent = `File Size: ${formatBytes(result.size)}`;
      successDur.textContent = `Duration: ${formatTime(result.duration)}`;

    } catch (err) {
      alert(`Export Failed:\n${err.message}`);
      exportFormState.classList.remove('hidden');
      exportProgressState.classList.add('hidden');
    }
  });

  window.api.onExportProgress((data) => {
    progressBarFill.style.width = `${data.percent}%`;
    progressPercentText.textContent = `${data.percent}%`;
    progressStatusText.textContent = data.status || 'Encoding and merging clips...';
    pstatTime.textContent = `${formatTime(data.currentSeconds, false)} / ${formatTime(data.totalSeconds, false)}`;
    pstatSpeed.textContent = data.speed || '1.0x';
    pstatFps.textContent = data.fps || '--';
  });

  btnAbortExport.addEventListener('click', async () => {
    if (confirm('Cancel active export rendering?')) {
      await window.api.cancelExport();
      exportProgressState.classList.add('hidden');
      exportFormState.classList.remove('hidden');
    }
  });

  btnRevealFile.addEventListener('click', () => {
    if (currentExportFilePath) {
      window.api.showItemInFolder(currentExportFilePath);
    }
  });

  btnPlayExported.addEventListener('click', () => {
    if (currentExportFilePath) {
      window.api.openPath(currentExportFilePath);
    }
  });

  function showToast(msg) {
    const existing = document.getElementById('studio-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'studio-toast';
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.background = 'rgba(16, 22, 35, 0.95)';
    toast.style.color = '#f8fafc';
    toast.style.padding = '8px 16px';
    toast.style.borderRadius = '8px';
    toast.style.fontSize = '12px';
    toast.style.fontWeight = '600';
    toast.style.border = '1px solid #35456b';
    toast.style.boxShadow = '0 8px 24px rgba(0,0,0,0.5)';
    toast.style.zIndex = '9999';
    toast.style.pointerEvents = 'none';
    toast.style.transition = 'opacity 0.2s ease';
    toast.textContent = msg;

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 200);
    }, 2500);
  }

  window.addEventListener('resize', () => {
    if (videoMeta) renderTimeline();
  });

})();
