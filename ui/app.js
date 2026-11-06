/**
 * V-EDITOR - MOBILE VIDEO EDITOR JAVASCRIPT ENGINE
 * Replicates demo.jpeg mobile UI & exact center needle cutting workflow
 */

(function () {
    'use strict';

    // --- APPLICATION STATE ---
    const state = {
        videoSrc: null,
        videoPath: null,
        videoDuration: 0,
        videoWidth: 0,
        videoHeight: 0,
        
        // List of clips on the timeline
        clips: [],
        activeClipIndex: 0,
        
        // Playback state
        currentTime: 0,      // Global project time (0 to totalProjectDuration)
        isPlaying: false,
        isMuted: false,
        
        // Timeline metrics
        pixelsPerSecond: 60, // Scale for timeline width
        isScrubbing: false,
        isTrimming: false,
        
        // History for Undo / Redo
        history: [],
        historyIndex: -1,
        maxHistory: 50,
        
        // Export settings
        exportPath: '',
        exportResolution: 'original'
    };

    // --- DOM REFERENCES ---
    const previewContainer = document.getElementById('previewContainer');
    const mainVideo = document.getElementById('mainVideo');
    const videoFrameBox = document.getElementById('videoFrameBox');
    const gestureHint = document.getElementById('gestureHint');
    const emptyState = document.getElementById('emptyState');
    const playOverlay = document.getElementById('playOverlay');
    const overlayIcon = document.getElementById('overlayIcon');
    
    // Top bar
    const btnClose = document.getElementById('btnClose');
    const btnSave = document.getElementById('btnSave');
    const btnMenu = document.getElementById('btnMenu');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const menuOpenVideo = document.getElementById('menuOpenVideo');
    const menuLoadSample = document.getElementById('menuLoadSample');
    const menuExport = document.getElementById('menuExport');
    const menuShortcuts = document.getElementById('menuShortcuts');
    const menuAbout = document.getElementById('menuAbout');

    // Sub-controls
    const btnPlayPause = document.getElementById('btnPlayPause');
    const iconPlay = document.getElementById('iconPlay');
    const iconPause = document.getElementById('iconPause');
    const currentTimeEl = document.getElementById('currentTime');
    const totalDurationEl = document.getElementById('totalDuration');
    const btnUndo = document.getElementById('btnUndo');
    const btnRedo = document.getElementById('btnRedo');

    // Timeline
    const btnMuteToggle = document.getElementById('btnMuteToggle');
    const iconAudioOn = document.getElementById('iconAudioOn');
    const iconAudioMuted = document.getElementById('iconAudioMuted');
    const timelineViewportWrapper = document.getElementById('timelineViewportWrapper');
    const timelineViewport = document.getElementById('timelineViewport');
    const timelineScrollTrack = document.getElementById('timelineScrollTrack');
    const clipsStrip = document.getElementById('clipsStrip');
    const padStart = document.getElementById('padStart');
    const padEnd = document.getElementById('padEnd');
    const btnAddMedia = document.getElementById('btnAddMedia');

    // Bottom tools
    const btnBackTool = document.getElementById('btnBackTool');
    const btnCut = document.getElementById('btnCut');
    const btnToolSpeed = document.getElementById('btnToolSpeed');
    const btnToolVolume = document.getElementById('btnToolVolume');
    const btnToolReverse = document.getElementById('btnToolReverse');
    const btnToolDelete = document.getElementById('btnToolDelete');

    // Tool drawers
    const toolSubpanel = document.getElementById('toolSubpanel');
    const panelSpeed = document.getElementById('panelSpeed');
    const panelVolume = document.getElementById('panelVolume');
    const speedValBadge = document.getElementById('speedValBadge');
    const volumeValBadge = document.getElementById('volumeValBadge');
    const volumeSlider = document.getElementById('volumeSlider');
    const btnVolReset = document.getElementById('btnVolReset');

    // Modals
    const saveModal = document.getElementById('saveModal');
    const btnCloseSaveModal = document.getElementById('btnCloseSaveModal');
    const btnCancelSave = document.getElementById('btnCancelSave');
    const saveFilePathInput = document.getElementById('saveFilePathInput');
    const btnBrowseSavePath = document.getElementById('btnBrowseSavePath');
    const btnConfirmExport = document.getElementById('btnConfirmExport');
    const modalExportForm = document.getElementById('modalExportForm');
    const modalExportProgress = document.getElementById('modalExportProgress');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressStatusTitle = document.getElementById('progressStatusTitle');
    const progressStatusDesc = document.getElementById('progressStatusDesc');
    const exportCompleteActions = document.getElementById('exportCompleteActions');
    const btnOpenExportedFolder = document.getElementById('btnOpenExportedFolder');
    const btnPlayExportedVideo = document.getElementById('btnPlayExportedVideo');
    const btnDoneExport = document.getElementById('btnDoneExport');
    const summaryDuration = document.getElementById('summaryDuration');
    const summaryClipsCount = document.getElementById('summaryClipsCount');

    const shortcutsModal = document.getElementById('shortcutsModal');
    const btnCloseShortcutsModal = document.getElementById('btnCloseShortcutsModal');

    // Prompts
    const btnOpenVideoPrompt = document.getElementById('btnOpenVideoPrompt');
    const btnLoadSamplePrompt = document.getElementById('btnLoadSamplePrompt');
    const hiddenFileInput = document.getElementById('hiddenFileInput');

    const statusText = document.getElementById('statusText');
    const statusRes = document.getElementById('statusRes');

    let exportedFilePath = '';
    let animFrameId = null;

    // --- INITIALIZATION ---
    function init() {
        bindEvents();
        updateTimelinePadding();
        updateVideoFrameSize();
        window.addEventListener('resize', () => {
            updateVideoFrameSize();
            updateTimelinePadding();
            seekToProjectTime(state.currentTime, true);
        });
        checkInitialVideo();
    }

    // --- DYNAMIC VIDEO FRAME ADAPTATION ---
    // Automatically sizes the yellow frame box to match the loaded video's exact size & aspect ratio
    function updateVideoFrameSize() {
        if (!state.videoWidth || !state.videoHeight) {
            videoFrameBox.style.width = '280px';
            videoFrameBox.style.height = '460px';
            return;
        }

        const containerW = (previewContainer.clientWidth || 800) - 48;
        const containerH = (previewContainer.clientHeight || 450) - 32;
        if (containerW <= 0 || containerH <= 0) return;

        const videoAspect = state.videoWidth / state.videoHeight;
        const containerAspect = containerW / containerH;

        let targetW, targetH;
        if (videoAspect > containerAspect) {
            // Landscape video (16:9, 21:9, etc.)
            targetW = containerW;
            targetH = containerW / videoAspect;
        } else {
            // Portrait / Square video (9:16, 4:5, 1:1, etc.)
            targetH = containerH;
            targetW = containerH * videoAspect;
        }

        videoFrameBox.style.width = `${Math.round(targetW)}px`;
        videoFrameBox.style.height = `${Math.round(targetH)}px`;
    }

    async function checkInitialVideo() {
        try {
            if (window.pywebview && window.pywebview.api) {
                // 1. Restore previously opened video path if available
                const lastPath = await window.pywebview.api.get_last_video_path();
                if (lastPath) {
                    console.log('[V-Editor] Restoring last video path:', lastPath);
                    loadVideoFile(lastPath);
                    return;
                }
                const samplePath = await window.pywebview.api.get_sample_path();
                if (samplePath) {
                    loadVideoFile(samplePath);
                    return;
                }
            }
        } catch (e) {
            console.warn('Pywebview API check:', e);
        }

        const localSaved = localStorage.getItem('veditor_last_video_path');
        if (localSaved && localSaved !== 'test_sample.mp4') {
            loadVideoFile(localSaved);
            return;
        }

        // Fallback: load /test_sample.mp4 via HTTP server
        fetch('/test_sample.mp4', { method: 'HEAD' })
            .then(res => {
                if (res.ok) {
                    state.videoPath = 'test_sample.mp4';
                    loadVideoUrl('/test_sample.mp4', 'Demo Sample Video');
                }
            })
            .catch(() => {});
    }

    // --- TIMELINE PADDING & NEEDLE MATH ---
    // Ensure the center needle (at 50% of viewport wrapper) aligns with t=0 when scrollLeft=0
    function updateTimelinePadding() {
        const halfWidth = (timelineViewport.clientWidth || 300) / 2;
        padStart.style.width = halfWidth + 'px';
        padEnd.style.width = halfWidth + 'px';
    }

    function timeToPixels(t) {
        return t * state.pixelsPerSecond;
    }

    function pixelsToTime(px) {
        return px / state.pixelsPerSecond;
    }

    function getTotalDuration() {
        if (!state.clips.length) return 0;
        return state.clips.reduce((sum, c) => sum + getClipEffectiveDuration(c), 0);
    }

    function getClipEffectiveDuration(clip) {
        const rawDur = Math.max(0.1, clip.sourceEnd - clip.sourceStart);
        return rawDur / (clip.speed || 1.0);
    }

    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) seconds = 0;
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // --- VIDEO LOADING ---
    async function loadVideoFile(filePath) {
        state.videoPath = filePath;
        localStorage.setItem('veditor_last_video_path', filePath);
        if (window.pywebview && window.pywebview.api) {
            try {
                window.pywebview.api.set_last_video_path(filePath);
            } catch (e) {}
        }
        const encoded = encodeURIComponent(filePath);
        fetch(`/ensure_thumbnails?path=${encoded}`).catch(() => {});
        const streamUrl = `/video_stream?path=${encoded}`;
        loadVideoUrl(streamUrl, filePath);
    }

    function loadVideoUrl(url, label) {
        pause();
        state.videoSrc = url;
        if (!state.videoPath) {
            state.videoPath = label || 'test_sample.mp4';
        }

        mainVideo.src = url;
        mainVideo.load();

        mainVideo.onloadedmetadata = () => {
            state.videoDuration = mainVideo.duration;
            state.videoWidth = mainVideo.videoWidth;
            state.videoHeight = mainVideo.videoHeight;
            
            // Adjust pixel scale so the timeline fits comfortably
            if (state.videoDuration > 60) {
                state.pixelsPerSecond = Math.max(20, Math.min(80, 600 / state.videoDuration));
            } else if (state.videoDuration < 5) {
                state.pixelsPerSecond = 100;
            } else {
                state.pixelsPerSecond = 70;
            }

            state.clips = [{
                id: 'clip_' + Date.now(),
                sourceStart: 0,
                sourceEnd: state.videoDuration,
                speed: 1.0,
                volume: 1.0,
                reverse: false
            }];
            state.activeClipIndex = 0;
            state.currentTime = 0;

            state.history = [];
            state.historyIndex = -1;
            pushHistory('Load Video');

            emptyState.style.display = 'none';
            const fileName = String(label).split(/[/\\]/).pop();
            gestureHint.textContent = `Clip: ${fileName}`;
            
            if (statusRes) {
                statusRes.textContent = `Resolution: ${state.videoWidth}x${state.videoHeight}`;
            }
            if (statusText) {
                statusText.textContent = `Ready • ${state.videoDuration.toFixed(1)}s`;
            }

            updateVideoFrameSize();
            updateTimelinePadding();
            renderTimeline();
            seekToProjectTime(0, true);
            updateUI();
        };

        mainVideo.onerror = () => {
            console.error('Failed to load video:', url);
            alert('Could not load video. Please select a valid MP4 / WebM / MOV file.');
        };
    }

    // --- HISTORY SYSTEM (UNDO / REDO) ---
    function pushHistory(desc = '') {
        if (state.historyIndex < state.history.length - 1) {
            state.history = state.history.slice(0, state.historyIndex + 1);
        }

        const snapshot = {
            desc,
            clips: JSON.parse(JSON.stringify(state.clips)),
            activeClipIndex: state.activeClipIndex,
            currentTime: state.currentTime
        };

        state.history.push(snapshot);
        if (state.history.length > state.maxHistory) {
            state.history.shift();
        } else {
            state.historyIndex++;
        }

        updateUndoRedoButtons();
    }

    function undo() {
        if (state.historyIndex > 0) {
            pause();
            state.historyIndex--;
            const snap = state.history[state.historyIndex];
            state.clips = JSON.parse(JSON.stringify(snap.clips));
            state.activeClipIndex = Math.min(snap.activeClipIndex, state.clips.length - 1);
            state.currentTime = Math.min(snap.currentTime, getTotalDuration());
            
            renderTimeline();
            seekToProjectTime(state.currentTime, true);
            updateUI();
            updateUndoRedoButtons();
        }
    }

    function redo() {
        if (state.historyIndex < state.history.length - 1) {
            pause();
            state.historyIndex++;
            const snap = state.history[state.historyIndex];
            state.clips = JSON.parse(JSON.stringify(snap.clips));
            state.activeClipIndex = Math.min(snap.activeClipIndex, state.clips.length - 1);
            state.currentTime = Math.min(snap.currentTime, getTotalDuration());

            renderTimeline();
            seekToProjectTime(state.currentTime, true);
            updateUI();
            updateUndoRedoButtons();
        }
    }

    function updateUndoRedoButtons() {
        btnUndo.disabled = state.historyIndex <= 0;
        btnRedo.disabled = state.historyIndex >= state.history.length - 1;
    }

    // --- TIMELINE RENDERING ---
    function renderTimeline() {
        clipsStrip.innerHTML = '';
        const totalDur = getTotalDuration();
        totalDurationEl.textContent = formatTime(totalDur);

        state.clips.forEach((clip, index) => {
            const effDur = getClipEffectiveDuration(clip);
            const clipWidth = timeToPixels(effDur);

            const clipBox = document.createElement('div');
            clipBox.className = 'clip-box' + (index === state.activeClipIndex ? ' active' : '');
            clipBox.style.width = `${clipWidth}px`;
            clipBox.dataset.index = index;

            const thumbsContainer = document.createElement('div');
            thumbsContainer.className = 'clip-thumbs';
            clipBox.appendChild(thumbsContainer);

            generateClipThumbnails(clip, thumbsContainer, clipWidth);

            const badge = document.createElement('div');
            badge.className = 'clip-duration-badge';
            badge.textContent = `${effDur.toFixed(1)}s`;
            clipBox.appendChild(badge);

            if (clip.reverse) {
                const revBadge = document.createElement('div');
                revBadge.className = 'clip-reverse-badge';
                revBadge.textContent = 'REV';
                clipBox.appendChild(revBadge);
            }

            if (index === state.activeClipIndex) {
                const leftHandle = document.createElement('div');
                leftHandle.className = 'trim-handle trim-handle-left';
                leftHandle.title = 'Drag to trim start';
                attachTrimHandler(leftHandle, index, 'left');
                clipBox.appendChild(leftHandle);

                const rightHandle = document.createElement('div');
                rightHandle.className = 'trim-handle trim-handle-right';
                rightHandle.title = 'Drag to trim end';
                attachTrimHandler(rightHandle, index, 'right');
                clipBox.appendChild(rightHandle);
            }

            clipBox.addEventListener('click', (e) => {
                if (e.target.classList.contains('trim-handle')) return;
                setActiveClip(index);
            });

            clipsStrip.appendChild(clipBox);
        });

        updateTimelinePadding();
    }

    function setActiveClip(index) {
        if (index < 0 || index >= state.clips.length) return;
        const prevIndex = state.activeClipIndex;
        state.activeClipIndex = index;
        renderTimeline();
        updateDrawerValues();

        if (prevIndex !== index) {
            let clipStart = 0;
            for (let i = 0; i < index; i++) {
                clipStart += getClipEffectiveDuration(state.clips[i]);
            }
            const clipEnd = clipStart + getClipEffectiveDuration(state.clips[index]);

            if (state.currentTime < clipStart || state.currentTime >= clipEnd) {
                seekToProjectTime(clipStart, true);
            }
        }
    }

    function generateClipThumbnails(clip, container, width) {
        container.innerHTML = '';
        const thumbWidth = 50; // Dense frame width in pixels for continuous filmstrip
        const frameCount = Math.max(1, Math.round(width / thumbWidth));
        const encodedPath = encodeURIComponent(state.videoPath || 'test_sample.mp4');

        for (let i = 0; i < frameCount; i++) {
            const frameRatio = (i + 0.5) / frameCount;
            const sourceTime = clip.reverse 
                ? clip.sourceEnd - frameRatio * (clip.sourceEnd - clip.sourceStart)
                : clip.sourceStart + frameRatio * (clip.sourceEnd - clip.sourceStart);

            const img = document.createElement('img');
            img.className = 'thumb-frame';
            img.alt = '';
            img.draggable = false;
            img.loading = 'lazy';

            const thumbUrl = `/thumb?path=${encodedPath}&t=${sourceTime.toFixed(2)}`;
            img.src = thumbUrl;

            img.onerror = () => {
                setTimeout(() => {
                    if (!img.complete || img.naturalWidth === 0) {
                        img.src = `${thumbUrl}&_r=${Date.now()}`;
                    }
                }, 800);
            };

            container.appendChild(img);
        }
    }

    // --- DRAGGING TRIM HANDLES `[` and `]` ---
    function attachTrimHandler(handle, clipIndex, side) {
        handle.addEventListener('pointerdown', (e) => {
            e.stopPropagation();
            state.isTrimming = true;
            pause();

            const clip = state.clips[clipIndex];
            const startX = e.clientX;
            const initialStart = clip.sourceStart;
            const initialEnd = clip.sourceEnd;
            const speed = clip.speed || 1.0;

            function onPointerMove(moveEvent) {
                const deltaX = moveEvent.clientX - startX;
                const deltaTime = pixelsToTime(deltaX) * speed;

                if (side === 'left') {
                    const newStart = Math.max(0, Math.min(clip.sourceEnd - 0.2, initialStart + deltaTime));
                    clip.sourceStart = newStart;
                    mainVideo.currentTime = newStart;
                } else {
                    const newEnd = Math.min(state.videoDuration, Math.max(clip.sourceStart + 0.2, initialEnd + deltaTime));
                    clip.sourceEnd = newEnd;
                    mainVideo.currentTime = newEnd;
                }

                const effDur = getClipEffectiveDuration(clip);
                const clipBox = clipsStrip.children[clipIndex];
                if (clipBox) {
                    clipBox.style.width = `${timeToPixels(effDur)}px`;
                    const badge = clipBox.querySelector('.clip-duration-badge');
                    if (badge) badge.textContent = `${effDur.toFixed(1)}s`;
                }

                totalDurationEl.textContent = formatTime(getTotalDuration());
            }

            function onPointerUp() {
                state.isTrimming = false;
                window.removeEventListener('pointermove', onPointerMove);
                window.removeEventListener('pointerup', onPointerUp);
                pushHistory(`Trim ${side} handle`);
                renderTimeline();
                seekToProjectTime(state.currentTime, true);
            }

            window.addEventListener('pointermove', onPointerMove);
            window.addEventListener('pointerup', onPointerUp);
        });
    }

    // --- PLAYHEAD SEEK & CENTER NEEDLE ALIGNMENT ---
    // Finds which clip covers global project time t and sets video currentTime
    function seekToProjectTime(t, syncScroll = true) {
        if (!state.clips.length) return;
        const totalDur = getTotalDuration();
        t = Math.max(0, Math.min(totalDur, t));
        state.currentTime = t;
        currentTimeEl.textContent = formatTime(t);

        let accumulated = 0;
        let matchedIndex = 0;
        let timeInClip = 0;

        for (let i = 0; i < state.clips.length; i++) {
            const clipDur = getClipEffectiveDuration(state.clips[i]);
            if (t < accumulated + clipDur || i === state.clips.length - 1) {
                matchedIndex = i;
                timeInClip = (t - accumulated) * (state.clips[i].speed || 1.0);
                break;
            }
            accumulated += clipDur;
        }

        const activeClip = state.clips[matchedIndex];
        if (activeClip) {
            let targetSourceTime;
            if (activeClip.reverse) {
                targetSourceTime = activeClip.sourceEnd - timeInClip;
            } else {
                targetSourceTime = activeClip.sourceStart + timeInClip;
            }
            targetSourceTime = Math.max(0, Math.min(state.videoDuration, targetSourceTime));
            
            if (!state.isPlaying || Math.abs(mainVideo.currentTime - targetSourceTime) > 0.15) {
                mainVideo.currentTime = targetSourceTime;
            }
            mainVideo.playbackRate = activeClip.speed || 1.0;
            mainVideo.volume = state.isMuted ? 0 : (activeClip.volume !== undefined ? activeClip.volume : 1.0);
        }

        if (state.activeClipIndex !== matchedIndex) {
            state.activeClipIndex = matchedIndex;
            Array.from(clipsStrip.children).forEach((box, idx) => {
                box.classList.toggle('active', idx === matchedIndex);
            });
        }

        // Align timeline track so time t is right under the center needle
        if (syncScroll && !state.isScrubbing) {
            const scrollPos = timeToPixels(t);
            timelineViewport.scrollLeft = scrollPos;
        }
    }

    // --- TIMELINE USER SCRUBBING ---
    timelineViewport.addEventListener('scroll', () => {
        if (!state.isPlaying && !state.isTrimming) {
            const scrollLeft = timelineViewport.scrollLeft;
            const t = pixelsToTime(scrollLeft);
            seekToProjectTime(t, false);
        }
    });

    let isPointerDownOnTrack = false;
    let trackStartX = 0;
    let initialScrollLeft = 0;

    timelineViewport.addEventListener('pointerdown', (e) => {
        if (e.target.classList.contains('trim-handle')) return;
        isPointerDownOnTrack = true;
        state.isScrubbing = true;
        trackStartX = e.clientX;
        initialScrollLeft = timelineViewport.scrollLeft;
        pause();

        function onPointerMove(moveEvent) {
            if (!isPointerDownOnTrack) return;
            const dx = moveEvent.clientX - trackStartX;
            timelineViewport.scrollLeft = initialScrollLeft - dx;
        }

        function onPointerUp() {
            isPointerDownOnTrack = false;
            state.isScrubbing = false;
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerup', onPointerUp);
        }

        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
    });

    // --- PLAYBACK ENGINE ---
    function togglePlay() {
        if (state.isPlaying) {
            pause();
        } else {
            play();
        }
    }

    function play() {
        if (!state.clips.length) return;
        const totalDur = getTotalDuration();
        if (state.currentTime >= totalDur - 0.05) {
            seekToProjectTime(0, true);
        }

        mainVideo.play().then(() => {
            state.isPlaying = true;
            iconPlay.style.display = 'none';
            iconPause.style.display = 'block';
            showPlayIndicator('play');
            startPlaybackLoop();
        }).catch(err => {
            console.warn('Playback error:', err);
        });
    }

    function pause() {
        state.isPlaying = false;
        mainVideo.pause();
        iconPlay.style.display = 'block';
        iconPause.style.display = 'none';
        if (animFrameId) {
            cancelAnimationFrame(animFrameId);
            animFrameId = null;
        }
    }

    function startPlaybackLoop() {
        let lastTimestamp = performance.now();

        function loop(timestamp) {
            if (!state.isPlaying) return;
            const deltaSec = (timestamp - lastTimestamp) / 1000;
            lastTimestamp = timestamp;

            const totalDur = getTotalDuration();
            const newTime = state.currentTime + deltaSec;

            if (newTime >= totalDur) {
                seekToProjectTime(totalDur, true);
                pause();
                return;
            }

            seekToProjectTime(newTime, true);
            animFrameId = requestAnimationFrame(loop);
        }

        animFrameId = requestAnimationFrame(loop);
    }

    function showPlayIndicator(type) {
        overlayIcon.innerHTML = type === 'play' 
            ? '<polygon points="5 3 19 12 5 21 5 3"></polygon>'
            : '<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>';
        playOverlay.classList.add('show');
        setTimeout(() => playOverlay.classList.remove('show'), 350);
    }

    // --- CUT / SPLIT ACTION (`][`) ---
    function cutAtNeedle() {
        if (!state.clips.length) return;
        pause();

        const needleTime = state.currentTime;
        let accumulated = 0;
        let targetIndex = -1;
        let splitOffset = 0;

        for (let i = 0; i < state.clips.length; i++) {
            const effDur = getClipEffectiveDuration(state.clips[i]);
            if (needleTime > accumulated && needleTime < accumulated + effDur) {
                targetIndex = i;
                splitOffset = (needleTime - accumulated) * (state.clips[i].speed || 1.0);
                break;
            }
            accumulated += effDur;
        }

        if (targetIndex === -1) {
            alert('Move the center needle inside a clip to cut/split it.');
            return;
        }

        const originalClip = state.clips[targetIndex];
        const splitSourceTime = originalClip.reverse 
            ? originalClip.sourceEnd - splitOffset
            : originalClip.sourceStart + splitOffset;

        if (splitSourceTime - originalClip.sourceStart < 0.1 || originalClip.sourceEnd - splitSourceTime < 0.1) {
            alert('Cannot cut too close to clip boundary.');
            return;
        }

        const clipA = {
            ...originalClip,
            id: 'clip_' + Date.now() + '_a',
            sourceStart: originalClip.sourceStart,
            sourceEnd: splitSourceTime
        };

        const clipB = {
            ...originalClip,
            id: 'clip_' + Date.now() + '_b',
            sourceStart: splitSourceTime,
            sourceEnd: originalClip.sourceEnd
        };

        state.clips.splice(targetIndex, 1, clipA, clipB);
        state.activeClipIndex = targetIndex + 1;

        pushHistory('Cut / Split Clip');
        renderTimeline();
        seekToProjectTime(needleTime, true);
        updateUI();

        btnCut.classList.add('active');
        setTimeout(() => btnCut.classList.remove('active'), 250);
    }

    // --- SPEED ADJUSTMENT ---
    function setClipSpeed(speed) {
        const clip = state.clips[state.activeClipIndex];
        if (!clip) return;
        clip.speed = parseFloat(speed);
        speedValBadge.textContent = `${speed}x`;
        
        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.classList.toggle('active', parseFloat(btn.dataset.speed) === clip.speed);
        });

        pushHistory(`Speed ${speed}x`);
        renderTimeline();
        seekToProjectTime(state.currentTime, true);
    }

    // --- VOLUME ADJUSTMENT ---
    function setClipVolume(volPercent) {
        const clip = state.clips[state.activeClipIndex];
        if (!clip) return;
        clip.volume = volPercent / 100;
        volumeValBadge.textContent = `${volPercent}%`;
        volumeSlider.value = volPercent;

        if (!state.isMuted) {
            mainVideo.volume = clip.volume;
        }
    }

    // --- REVERSE CLIP ---
    function toggleClipReverse() {
        const clip = state.clips[state.activeClipIndex];
        if (!clip) return;
        clip.reverse = !clip.reverse;
        pushHistory('Toggle Reverse');
        renderTimeline();
        seekToProjectTime(state.currentTime, true);
    }

    // --- DELETE CLIP ---
    function deleteActiveClip() {
        if (!state.clips.length) return;
        if (state.clips.length === 1) {
            if (confirm('Delete the entire video clip?')) {
                state.clips = [];
                state.activeClipIndex = -1;
                pushHistory('Delete all clips');
                renderTimeline();
                emptyState.style.display = 'flex';
                updateUI();
            }
            return;
        }

        pause();
        const deleteIndex = state.activeClipIndex;
        if (deleteIndex < 0 || deleteIndex >= state.clips.length) return;

        // Calculate the project start time of the clip being deleted
        let clipStartTime = 0;
        for (let i = 0; i < deleteIndex; i++) {
            clipStartTime += getClipEffectiveDuration(state.clips[i]);
        }

        // Remove the active clip
        state.clips.splice(deleteIndex, 1);

        let newActiveIndex;
        let targetTime;

        if (deleteIndex < state.clips.length) {
            // There IS a next part (which now sits at deleteIndex):
            // Place the playhead at the 1st frame (start) of this next part
            newActiveIndex = deleteIndex;
            targetTime = clipStartTime;
        } else {
            // The deleted clip was the last one; select the preceding clip and seek to its end
            newActiveIndex = state.clips.length - 1;
            targetTime = getTotalDuration();
        }

        state.activeClipIndex = newActiveIndex;
        state.currentTime = targetTime;

        pushHistory('Delete Clip');
        renderTimeline();
        seekToProjectTime(targetTime, true);
        updateUI();
    }

    // --- SUB-PANEL DRAWER (Speed, Volume) ---
    function toggleToolDrawer(panelName) {
        const isOpen = toolSubpanel.classList.contains('open');
        const isSpeed = panelName === 'speed';
        const isVol = panelName === 'volume';

        if (isOpen && ((isSpeed && panelSpeed.style.display === 'block') || (isVol && panelVolume.style.display === 'block'))) {
            closeToolDrawer();
            return;
        }

        toolSubpanel.classList.add('open');
        panelSpeed.style.display = isSpeed ? 'block' : 'none';
        panelVolume.style.display = isVol ? 'block' : 'none';

        btnToolSpeed.classList.toggle('active', isSpeed);
        btnToolVolume.classList.toggle('active', isVol);

        updateDrawerValues();
    }

    function closeToolDrawer() {
        toolSubpanel.classList.remove('open');
        btnToolSpeed.classList.remove('active');
        btnToolVolume.classList.remove('active');
    }

    function updateDrawerValues() {
        const clip = state.clips[state.activeClipIndex];
        if (!clip) return;

        const speed = clip.speed || 1.0;
        speedValBadge.textContent = `${speed}x`;
        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.classList.toggle('active', parseFloat(btn.dataset.speed) === speed);
        });

        const volPercent = Math.round((clip.volume !== undefined ? clip.volume : 1.0) * 100);
        volumeValBadge.textContent = `${volPercent}%`;
        volumeSlider.value = volPercent;
    }

    // --- SAVE & EXPORT MODAL ---
    async function openSaveModal() {
        pause();
        summaryDuration.textContent = formatTime(getTotalDuration());
        summaryClipsCount.textContent = state.clips.length;

        // Obtain default full save path from Python backend (uses current PC Downloads or persisted folder)
        try {
            if (window.pywebview && window.pywebview.api) {
                const videoTitle = state.videoPath ? state.videoPath.split(/[/\\]/).pop() : '';
                const defaultPath = await window.pywebview.api.get_default_save_path(videoTitle);
                if (defaultPath) {
                    state.exportPath = defaultPath;
                }
            }
        } catch (e) {
            console.warn('Default save path fetch error:', e);
        }

        if (!state.exportPath) {
            const dateStr = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
            const savedFolder = localStorage.getItem('veditor_saved_export_folder') || 'Downloads';
            state.exportPath = `${savedFolder}\\V_Editor_Export_${dateStr}.mp4`;
        }
        saveFilePathInput.value = state.exportPath;

        modalExportForm.style.display = 'block';
        modalExportProgress.style.display = 'none';
        exportCompleteActions.style.display = 'none';
        document.querySelector('.progress-spinner-box').style.display = 'flex';
        saveModal.style.display = 'flex';
    }

    function closeSaveModal() {
        saveModal.style.display = 'none';
    }

    async function handleBrowseSavePath() {
        try {
            if (window.pywebview && window.pywebview.api) {
                const currentVal = saveFilePathInput.value || '';
                const chosen = await window.pywebview.api.choose_save_path(currentVal);
                if (chosen) {
                    state.exportPath = chosen;
                    saveFilePathInput.value = chosen;
                    const folder = chosen.substring(0, Math.max(chosen.lastIndexOf('\\'), chosen.lastIndexOf('/')));
                    if (folder) {
                        localStorage.setItem('veditor_saved_export_folder', folder);
                    }
                }
            } else {
                const chosen = prompt('Enter destination file path for MP4:', saveFilePathInput.value);
                if (chosen) {
                    state.exportPath = chosen;
                    saveFilePathInput.value = chosen;
                }
            }
        } catch (e) {
            console.error('File dialog error:', e);
        }
    }

    async function startExport() {
        if (!state.exportPath) {
            await handleBrowseSavePath();
            if (!state.exportPath) return;
        }

        modalExportForm.style.display = 'none';
        modalExportProgress.style.display = 'block';
        progressStatusTitle.textContent = 'Exporting Video...';
        progressStatusDesc.textContent = 'Applying cuts, filters and encoding with FFmpeg...';
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        exportCompleteActions.style.display = 'none';
        document.querySelector('.progress-spinner-box').style.display = 'flex';

        const exportPayload = {
            sourcePath: state.videoPath,
            outputPath: state.exportPath,
            resolution: state.exportResolution,
            clips: state.clips
        };

        try {
            if (window.pywebview && window.pywebview.api) {
                const result = await window.pywebview.api.export_video(exportPayload);
                if (result && result.success) {
                    onExportFinished(result.outputPath);
                } else {
                    onExportFailed(result ? result.error : 'Export failed.');
                }
            } else {
                simulateExportProgress();
            }
        } catch (err) {
            onExportFailed(err.message);
        }
    }

    function simulateExportProgress() {
        let pct = 0;
        const interval = setInterval(() => {
            pct += 10;
            updateExportProgress(pct, `Encoding frame ${pct * 24}...`);
            if (pct >= 100) {
                clearInterval(interval);
                onExportFinished(state.exportPath);
            }
        }, 300);
    }

    window.updateExportProgress = function (percent, desc) {
        progressBarFill.style.width = `${percent}%`;
        progressPercent.textContent = `${Math.round(percent)}%`;
        if (desc) progressStatusDesc.textContent = desc;
    };

    function onExportFinished(outPath) {
        exportedFilePath = outPath;
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';
        progressStatusTitle.textContent = 'Export Complete!';
        progressStatusDesc.textContent = `Video successfully saved to: ${outPath}`;
        exportCompleteActions.style.display = 'flex';
        document.querySelector('.progress-spinner-box').style.display = 'none';
    }

    function onExportFailed(errMsg) {
        progressStatusTitle.textContent = 'Export Failed';
        progressStatusDesc.textContent = errMsg || 'An error occurred during video rendering.';
        progressBarFill.style.background = '#e53e3e';
        exportCompleteActions.style.display = 'flex';
        btnOpenExportedFolder.style.display = 'none';
        btnPlayExportedVideo.style.display = 'none';
        document.querySelector('.progress-spinner-box').style.display = 'none';
    }

    // --- EVENT BINDINGS ---
    function bindEvents() {
        btnPlayPause.addEventListener('click', togglePlay);
        videoFrameBox.addEventListener('click', (e) => {
            if (e.target.closest('#emptyState')) return;
            togglePlay();
        });

        btnSave.addEventListener('click', openSaveModal);
        btnClose.addEventListener('click', () => {
            if (confirm('Start a new project / reset?')) {
                state.clips = [];
                emptyState.style.display = 'flex';
                updateUI();
            }
        });

        btnMenu.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });
        document.addEventListener('click', () => dropdownMenu.classList.remove('show'));

        menuOpenVideo.addEventListener('click', handleOpenVideo);
        menuLoadSample.addEventListener('click', () => {
            state.videoPath = 'test_sample.mp4';
            loadVideoUrl('/test_sample.mp4', 'Demo Sample Video');
        });
        menuExport.addEventListener('click', openSaveModal);
        menuShortcuts.addEventListener('click', () => shortcutsModal.style.display = 'flex');
        menuAbout.addEventListener('click', () => {
            alert('V-Editor v1.0.0\nA modern mobile-style video editor for desktop with pixel-accurate cutting & FFmpeg rendering engine.');
        });

        btnUndo.addEventListener('click', undo);
        btnRedo.addEventListener('click', redo);

        btnMuteToggle.addEventListener('click', () => {
            state.isMuted = !state.isMuted;
            mainVideo.muted = state.isMuted;
            iconAudioOn.style.display = state.isMuted ? 'none' : 'block';
            iconAudioMuted.style.display = state.isMuted ? 'block' : 'none';
        });

        btnAddMedia.addEventListener('click', handleOpenVideo);
        btnOpenVideoPrompt.addEventListener('click', handleOpenVideo);
        btnLoadSamplePrompt.addEventListener('click', () => {
            state.videoPath = 'test_sample.mp4';
            loadVideoUrl('/test_sample.mp4', 'Demo Sample Video');
        });

        btnBackTool.addEventListener('click', closeToolDrawer);
        btnCut.addEventListener('click', cutAtNeedle);
        btnToolSpeed.addEventListener('click', () => toggleToolDrawer('speed'));
        btnToolVolume.addEventListener('click', () => toggleToolDrawer('volume'));
        btnToolReverse.addEventListener('click', toggleClipReverse);
        btnToolDelete.addEventListener('click', deleteActiveClip);

        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.addEventListener('click', () => setClipSpeed(btn.dataset.speed));
        });

        volumeSlider.addEventListener('input', (e) => setClipVolume(e.target.value));
        volumeSlider.addEventListener('change', () => pushHistory('Adjust Volume'));
        btnVolReset.addEventListener('click', () => {
            setClipVolume(100);
            pushHistory('Reset Volume 100%');
        });

        btnCloseSaveModal.addEventListener('click', closeSaveModal);
        btnCancelSave.addEventListener('click', closeSaveModal);
        btnBrowseSavePath.addEventListener('click', handleBrowseSavePath);
        btnConfirmExport.addEventListener('click', startExport);
        btnDoneExport.addEventListener('click', closeSaveModal);

        btnOpenExportedFolder.addEventListener('click', () => {
            if (window.pywebview && window.pywebview.api && exportedFilePath) {
                window.pywebview.api.open_folder(exportedFilePath);
            }
        });

        btnPlayExportedVideo.addEventListener('click', () => {
            if (window.pywebview && window.pywebview.api && exportedFilePath) {
                window.pywebview.api.play_exported_file(exportedFilePath);
            }
        });

        document.querySelectorAll('.quality-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.exportResolution = btn.dataset.res;
            });
        });

        btnCloseShortcutsModal.addEventListener('click', () => shortcutsModal.style.display = 'none');

        window.addEventListener('dragover', (e) => e.preventDefault());
        window.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('video/')) {
                const url = URL.createObjectURL(files[0]);
                loadVideoUrl(url, files[0].name);
            }
        });

        hiddenFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                loadVideoUrl(url, file.name);
            }
        });

        window.addEventListener('keydown', handleKeyboardShortcuts);
    }

    async function handleOpenVideo() {
        try {
            if (window.pywebview && window.pywebview.api) {
                const chosen = await window.pywebview.api.open_video_dialog();
                if (chosen) {
                    loadVideoFile(chosen);
                    return;
                }
            }
        } catch (e) {
            console.warn('Native open dialog fallback:', e);
        }
        hiddenFileInput.click();
    }

    function handleKeyboardShortcuts(e) {
        if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

        if (e.code === 'Space') {
            e.preventDefault();
            togglePlay();
        } else if (e.code === 'KeyC' || e.code === 'KeyS') {
            if (!e.ctrlKey) {
                e.preventDefault();
                cutAtNeedle();
            }
        } else if (e.ctrlKey && e.code === 'KeyZ') {
            e.preventDefault();
            undo();
        } else if (e.ctrlKey && (e.code === 'KeyY' || (e.shiftKey && e.code === 'KeyZ'))) {
            e.preventDefault();
            redo();
        } else if (e.code === 'Delete' || e.code === 'Backspace') {
            e.preventDefault();
            deleteActiveClip();
        } else if (e.ctrlKey && e.code === 'KeyS') {
            e.preventDefault();
            openSaveModal();
        } else if (e.ctrlKey && e.code === 'KeyO') {
            e.preventDefault();
            handleOpenVideo();
        } else if (e.code === 'ArrowLeft') {
            e.preventDefault();
            pause();
            seekToProjectTime(state.currentTime - 0.1, true);
        } else if (e.code === 'ArrowRight') {
            e.preventDefault();
            pause();
            seekToProjectTime(state.currentTime + 0.1, true);
        }
    }

    function updateUI() {
        currentTimeEl.textContent = formatTime(state.currentTime);
        totalDurationEl.textContent = formatTime(getTotalDuration());
        updateUndoRedoButtons();
    }

    window.addEventListener('DOMContentLoaded', init);
})();
