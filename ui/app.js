// Pro Downloader - Frontend Application Controller
document.addEventListener('DOMContentLoaded', () => {
  // Application State
  let currentLibrary = { downloaded: [], settings: {} };
  let currentFetchedVideo = null;
  let runningDownloads = {}; // id -> download_info
  let currentPlayingFile = null;

  // DOM Elements - Sidebar & Nav
  const sidebar = document.getElementById('sidebar');
  const btnCollapseSidebar = document.getElementById('btnCollapseSidebar');
  const btnPro = document.getElementById('btnPro');
  const navHome = document.getElementById('navHome');
  const navDownloaded = document.getElementById('navDownloaded');
  const downloadedBadge = document.getElementById('downloadedBadge');
  const btnSidebarSettings = document.getElementById('btnSidebarSettings');
  const btnSettings = document.getElementById('btnSettings');
  const btnOpenDownloadsFolderTop = document.getElementById('btnOpenDownloadsFolderTop');
  const btnOpenFolderCompleted = document.getElementById('btnOpenFolderCompleted');

  // DOM Elements - Views
  const viewHome = document.getElementById('viewHome');
  const viewDownloaded = document.getElementById('viewDownloaded');

  // DOM Elements - Home Search & Analysis
  const urlInput = document.getElementById('urlInput');
  const btnPasteClipboard = document.getElementById('btnPasteClipboard');
  const btnClear = document.getElementById('btnClear');
  const btnSearch = document.getElementById('btnSearch');
  const btnDirectDownload = document.getElementById('btnDirectDownload');

  // Playlist Suggestion Prompt Banner
  const playlistSuggestionBanner = document.getElementById('playlistSuggestionBanner');
  const btnChoiceSingle = document.getElementById('btnChoiceSingle');
  const btnChoicePlaylist = document.getElementById('btnChoicePlaylist');
  const btnClosePlaylistBanner = document.getElementById('btnClosePlaylistBanner');

  // Analyzed Card
  const analyzedCard = document.getElementById('analyzedCard');
  const btnCloseAnalyzed = document.getElementById('btnCloseAnalyzed');
  const analyzedThumb = document.getElementById('analyzedThumb');
  const analyzedDuration = document.getElementById('analyzedDuration');
  const analyzedTitle = document.getElementById('analyzedTitle');
  const analyzedChannel = document.getElementById('analyzedChannel');
  const analyzedQuality = document.getElementById('analyzedQuality');
  const btnAnalyzedDownload = document.getElementById('btnAnalyzedDownload');
  const btnAnalyzedOptions = document.getElementById('btnAnalyzedOptions');

  // Playlist Section Elements
  const playlistSection = document.getElementById('playlistSection');
  const btnClosePlaylistSection = document.getElementById('btnClosePlaylistSection');
  const playlistTitle = document.getElementById('playlistTitle');
  const playlistTotalCountBadge = document.getElementById('playlistTotalCountBadge');
  const playlistSelectedCountBadge = document.getElementById('playlistSelectedCountBadge');
  const playlistSelectAll = document.getElementById('playlistSelectAll');
  const btnInvertSelection = document.getElementById('btnInvertSelection');
  const playlistQualitySelect = document.getElementById('playlistQualitySelect');
  const btnDownloadSelectedPlaylist = document.getElementById('btnDownloadSelectedPlaylist');
  const btnDownloadSelectedText = document.getElementById('btnDownloadSelectedText');
  const playlistItemsList = document.getElementById('playlistItemsList');
  let currentPlaylistData = null;
  let selectedPlaylistIndices = new Set();

  // DOM Elements - Downloads View
  const runningCountBadge = document.getElementById('runningCountBadge');
  const runningDownloadsList = document.getElementById('runningDownloadsList');
  const emptyRunningCard = document.getElementById('emptyRunningCard');
  const completedCountBadge = document.getElementById('completedCountBadge');
  const completedDownloadsList = document.getElementById('completedDownloadsList');

  // DOM Elements - Download Modal
  const downloadModal = document.getElementById('downloadModal');
  const btnCloseDownloadModal = document.getElementById('btnCloseDownloadModal');
  const btnCancelModal = document.getElementById('btnCancelModal');
  const btnStartDownload = document.getElementById('btnStartDownload');
  const modalThumb = document.getElementById('modalThumb');
  const modalTitle = document.getElementById('modalTitle');
  const modalChannel = document.getElementById('modalChannel');
  const modalDuration = document.getElementById('modalDuration');
  const qualityOptions = document.getElementById('qualityOptions');

  // DOM Elements - Player Modal
  const playerModal = document.getElementById('playerModal');
  const btnClosePlayer = document.getElementById('btnClosePlayer');
  const playerVideoTitle = document.getElementById('playerVideoTitle');
  const videoPlayerElement = document.getElementById('videoPlayerElement');
  const btnOpenCurrentFolder = document.getElementById('btnOpenCurrentFolder');

  // DOM Elements - Settings Modal
  const settingsModal = document.getElementById('settingsModal');
  const btnCloseSettings = document.getElementById('btnCloseSettings');
  const btnCancelSettings = document.getElementById('btnCancelSettings');
  const btnSaveSettings = document.getElementById('btnSaveSettings');
  const settingsDownloadFolder = document.getElementById('settingsDownloadFolder');
  const btnBrowseFolder = document.getElementById('btnBrowseFolder');
  const settingsDefaultQuality = document.getElementById('settingsDefaultQuality');

  // Unified API Call with PyWebView + REST Fallback
  async function callApi(fnName, ...args) {
    // 1. Try PyWebView API
    if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[fnName] === 'function') {
      try {
        return await window.pywebview.api[fnName](...args);
      } catch (err) {
        console.error(`PyWebView API ${fnName} error:`, err);
      }
    }

    // 2. HTTP REST Endpoints Fallback
    try {
      if (fnName === 'fetch_info') {
        const res = await fetch('/api/fetch_info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: args[0], mode: args[1] || 'auto' })
        });
        return await res.json();
      } else if (fnName === 'start_download') {
        const res = await fetch('/api/start_download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(args[0])
        });
        return await res.json();
      } else if (fnName === 'start_playlist_download') {
        const res = await fetch('/api/start_playlist_download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(args[0])
        });
        return await res.json();
      } else if (fnName === 'cancel_download') {
        const res = await fetch('/api/cancel_download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: args[0] })
        });
        return await res.json();
      } else if (fnName === 'cancel_all_downloads') {
        const res = await fetch('/api/cancel_all', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        return await res.json();
      } else if (fnName === 'get_active_downloads') {
        const res = await fetch('/api/active_downloads');
        return await res.json();
      } else if (fnName === 'get_library') {
        const res = await fetch('/api/library');
        return await res.json();
      } else if (fnName === 'delete_item') {
        const res = await fetch('/api/delete_item', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: args[0], delete_file: args[1] })
        });
        return await res.json();
      } else if (fnName === 'clear_download_history') {
        const res = await fetch('/api/clear_history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ delete_files: args[0] || false })
        });
        return await res.json();
      } else if (fnName === 'get_settings') {
        const res = await fetch('/api/settings');
        return await res.json();
      } else if (fnName === 'save_settings') {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(args[0])
        });
        return await res.json();
      } else if (fnName === 'open_in_folder') {
        const res = await fetch('/api/open_folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filepath: args[0] })
        });
        return await res.json();
      }
    } catch (httpErr) {
      console.error(`HTTP API fallback failed for ${fnName}:`, httpErr);
    }
    return null;
  }

  // Toast Notifications
  function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    let icon = '⚡';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '✕';
    if (type === 'warning') icon = '⚠️';

    toast.innerHTML = `<span style="font-size:14px;">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s, transform 0.3s';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 4200);
  }

  // Fallback SVG Thumbnail Banner
  function getFallbackThumbnail(title, type = 'video') {
    const safeTitle = (title || 'Pro Media').replace(/[<>&"]/g, '');
    const isAudio = type === 'audio' || safeTitle.toLowerCase().includes('mp3');
    const symbol = isAudio ? '🎵' : (type === 'playlist' ? '📑' : '🎬');
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225">
        <defs>
          <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="${isAudio ? '#4c1d95' : (type === 'playlist' ? '#1e1b4b' : '#0f172a')}"/>
            <stop offset="100%" stop-color="${isAudio ? '#7c3aed' : (type === 'playlist' ? '#4f46e5' : '#2563eb')}"/>
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g)"/>
        <circle cx="200" cy="95" r="36" fill="rgba(255,255,255,0.12)"/>
        <text x="200" y="105" fill="#ffffff" font-size="28" text-anchor="middle">${symbol}</text>
        <text x="200" y="165" fill="#ffffff" font-family="system-ui" font-size="14" font-weight="700" text-anchor="middle">${safeTitle.slice(0, 32)}</text>
        <text x="200" y="190" fill="#38bdf8" font-family="system-ui" font-size="11" font-weight="800" text-anchor="middle" letter-spacing="1">PRO DOWNLOADER</text>
      </svg>
    `;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }

  // Detect if a URL belongs to a Playlist
  function hasPlaylistParameter(url) {
    if (!url) return false;
    const match = url.match(/[?&]list=([a-zA-Z0-9_-]+)/);
    return Boolean(match && match[1]);
  }

  // Check URL input for playlist on change/paste
  function checkUrlForPlaylistPrompt() {
    const url = urlInput.value.trim();
    if (hasPlaylistParameter(url) && (url.includes('watch?v=') || url.includes('youtu.be/') || url.includes('/shorts/'))) {
      playlistSuggestionBanner.style.display = 'flex';
    } else {
      playlistSuggestionBanner.style.display = 'none';
    }
  }

  urlInput.addEventListener('input', checkUrlForPlaylistPrompt);
  urlInput.addEventListener('paste', () => setTimeout(checkUrlForPlaylistPrompt, 50));

  // Banner Choice Buttons
  btnChoiceSingle.addEventListener('click', () => {
    playlistSuggestionBanner.style.display = 'none';
    analyzeUrl('single');
  });

  btnChoicePlaylist.addEventListener('click', () => {
    playlistSuggestionBanner.style.display = 'none';
    analyzeUrl('playlist');
  });

  btnClosePlaylistBanner.addEventListener('click', () => {
    playlistSuggestionBanner.style.display = 'none';
  });

  // Navigation Switcher (Home vs Downloaded)
  function switchTab(tabName) {
    navHome.classList.remove('active');
    navDownloaded.classList.remove('active');
    viewHome.style.display = 'none';
    viewDownloaded.style.display = 'none';

    if (tabName === 'home') {
      navHome.classList.add('active');
      viewHome.style.display = 'flex';
    } else if (tabName === 'downloaded') {
      navDownloaded.classList.add('active');
      viewDownloaded.style.display = 'flex';
      refreshRunningDownloads();
      loadLibraryData();
    }
  }

  navHome.addEventListener('click', () => switchTab('home'));
  navDownloaded.addEventListener('click', () => switchTab('downloaded'));

  // Sidebar Collapse
  if (btnCollapseSidebar) {
    btnCollapseSidebar.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  if (btnPro) {
    btnPro.addEventListener('click', () => {
      showToast('⚡ Unlimited Mode is active! Maximum speeds unlocked.', 'success');
    });
  }

  // Paste Link from Clipboard
  btnPasteClipboard.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && (text.includes('youtube.com') || text.includes('youtu.be') || text.startsWith('http'))) {
        urlInput.value = text.trim();
        showToast('Link pasted from clipboard!', 'success');
        checkUrlForPlaylistPrompt();
        
        // If playlist detected, let user choose via banner; otherwise auto analyze
        if (!hasPlaylistParameter(urlInput.value)) {
          btnSearch.click();
        }
      } else if (text) {
        urlInput.value = text.trim();
        showToast('Pasted into search box.', 'info');
      } else {
        showToast('Clipboard is empty. Copy a YouTube link first.', 'warning');
      }
    } catch (e) {
      showToast('Press Ctrl+V to paste link.', 'info');
      urlInput.focus();
    }
  });

  // Clear URL Input
  btnClear.addEventListener('click', () => {
    urlInput.value = '';
    playlistSuggestionBanner.style.display = 'none';
    analyzedCard.style.display = 'none';
    urlInput.focus();
  });

  urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      btnSearch.click();
    }
  });

  if (btnCloseAnalyzed) {
    btnCloseAnalyzed.addEventListener('click', () => {
      analyzedCard.style.display = 'none';
    });
  }

  // Analyze URL Function (mode: 'auto' | 'single' | 'playlist')
  async function analyzeUrl(mode = 'auto') {
    const url = urlInput.value.trim();
    if (!url) {
      showToast('Please enter a YouTube video or playlist link.', 'warning');
      urlInput.focus();
      return;
    }

    btnSearch.disabled = true;
    const originalText = btnSearch.innerHTML;
    btnSearch.innerHTML = `
      <span style="display:inline-block; animation:spin 0.8s linear infinite;">⏳</span>
      <span>Analyzing...</span>
    `;

    const info = await callApi('fetch_info', url, mode);
    btnSearch.disabled = false;
    btnSearch.innerHTML = originalText;

    if (!info || !info.success) {
      showToast(info?.error || 'Failed to analyze link. Please check the URL.', 'error');
      return;
    }

    info.url = info.url || url;
    currentFetchedVideo = info;

    if (info.is_playlist) {
      // Hide single card & show full playlist checklist
      analyzedCard.style.display = 'none';
      renderPlaylistSection(info);
      showToast(`Playlist analyzed: ${info.count} videos found!`, 'success');
    } else {
      // Single Video Mode
      playlistSection.style.display = 'none';
      const fallback = getFallbackThumbnail(info.title, 'video');
      analyzedThumb.src = info.thumbnail || fallback;
      analyzedThumb.onerror = () => { analyzedThumb.src = fallback; };
      analyzedTitle.textContent = info.title;
      analyzedChannel.textContent = info.channel || 'YouTube';
      analyzedDuration.textContent = info.duration_string || `${info.duration || 0}s`;
      analyzedQuality.textContent = 'Best Quality (Original)';
      btnAnalyzedDownload.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
        <span>Download Best Quality</span>
      `;
      analyzedCard.style.display = 'block';
      analyzedCard.scrollIntoView({ behavior: 'smooth' });
      showToast('Video analyzed successfully!', 'success');
    }
  }

  // Render Playlist Section with Checkboxes
  function renderPlaylistSection(playlistInfo) {
    currentPlaylistData = playlistInfo;
    const entries = playlistInfo.entries || [];
    selectedPlaylistIndices = new Set(entries.map((_, i) => i));

    playlistTitle.textContent = playlistInfo.title || 'YouTube Playlist';
    playlistTotalCountBadge.textContent = `${entries.length} Videos`;
    playlistSelectAll.checked = true;

    playlistItemsList.innerHTML = '';

    entries.forEach((entry, idx) => {
      const fallback = getFallbackThumbnail(entry.title, 'video');
      const row = document.createElement('div');
      row.className = 'playlist-item-row selected';
      row.id = `pl_item_${idx}`;
      row.innerHTML = `
        <div class="pl-item-left">
          <div class="pl-checkbox-wrap">
            <input type="checkbox" class="pl-item-checkbox" data-index="${idx}" checked />
          </div>
          <span class="pl-item-index">#${idx + 1}</span>
          <div class="pl-item-thumb-wrap">
            <img src="${entry.thumbnail || fallback}" alt="Thumb" class="pl-item-thumb" onerror="this.src='${fallback}'"/>
            <span class="pl-item-duration">${entry.duration || '00:00'}</span>
          </div>
          <div class="pl-item-details">
            <span class="pl-item-title" title="${entry.title}">${entry.title}</span>
            <span class="pl-item-meta">Episode ${idx + 1} • Duration: ${entry.duration || 'Unknown'}</span>
          </div>
        </div>
        <div class="pl-item-actions">
          <button class="btn-pl-single-dl" data-index="${idx}" title="Download only this video">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>Single</span>
          </button>
        </div>
      `;

      // Checkbox click toggle
      const chk = row.querySelector('.pl-item-checkbox');
      chk.addEventListener('change', (e) => {
        e.stopPropagation();
        togglePlaylistRowSelection(idx, chk.checked);
      });

      // Row click toggle
      row.addEventListener('click', (e) => {
        if (e.target.closest('.btn-pl-single-dl') || e.target.closest('.pl-item-checkbox')) return;
        chk.checked = !chk.checked;
        togglePlaylistRowSelection(idx, chk.checked);
      });

      // Single Video direct download button inside playlist
      row.querySelector('.btn-pl-single-dl').addEventListener('click', (e) => {
        e.stopPropagation();
        const selQuality = playlistQualitySelect.value || 'best';
        const plTitle = currentPlaylistData ? currentPlaylistData.title : '';
        triggerDownload(entry, selQuality, plTitle);
      });

      playlistItemsList.appendChild(row);
    });

    updatePlaylistSelectionSummary();
    playlistSection.style.display = 'flex';
    playlistSection.scrollIntoView({ behavior: 'smooth' });
  }

  function togglePlaylistRowSelection(index, isSelected) {
    const row = document.getElementById(`pl_item_${index}`);
    if (isSelected) {
      selectedPlaylistIndices.add(index);
      if (row) row.classList.add('selected');
    } else {
      selectedPlaylistIndices.delete(index);
      if (row) row.classList.remove('selected');
    }
    updatePlaylistSelectionSummary();
  }

  function updatePlaylistSelectionSummary() {
    if (!currentPlaylistData || !currentPlaylistData.entries) return;
    const total = currentPlaylistData.entries.length;
    const count = selectedPlaylistIndices.size;

    playlistSelectedCountBadge.textContent = `${count} Selected`;
    btnDownloadSelectedText.textContent = `Download Selected (${count})`;

    if (count === 0) {
      btnDownloadSelectedPlaylist.disabled = true;
      btnDownloadSelectedPlaylist.style.opacity = '0.5';
      btnDownloadSelectedPlaylist.style.cursor = 'not-allowed';
      playlistSelectAll.checked = false;
      document.getElementById('selectAllLabelText').textContent = 'Select None';
    } else {
      btnDownloadSelectedPlaylist.disabled = false;
      btnDownloadSelectedPlaylist.style.opacity = '1';
      btnDownloadSelectedPlaylist.style.cursor = 'pointer';
      playlistSelectAll.checked = (count === total);
      document.getElementById('selectAllLabelText').textContent = (count === total) ? 'Select All' : 'Select All';
    }
  }

  // Select All Toggle
  playlistSelectAll.addEventListener('change', () => {
    if (!currentPlaylistData || !currentPlaylistData.entries) return;
    const isChecked = playlistSelectAll.checked;
    const checkboxes = playlistItemsList.querySelectorAll('.pl-item-checkbox');

    checkboxes.forEach((chk, idx) => {
      chk.checked = isChecked;
      const row = document.getElementById(`pl_item_${idx}`);
      if (isChecked) {
        selectedPlaylistIndices.add(idx);
        if (row) row.classList.add('selected');
      } else {
        selectedPlaylistIndices.delete(idx);
        if (row) row.classList.remove('selected');
      }
    });

    updatePlaylistSelectionSummary();
  });

  // Invert Selection
  btnInvertSelection.addEventListener('click', () => {
    if (!currentPlaylistData || !currentPlaylistData.entries) return;
    const checkboxes = playlistItemsList.querySelectorAll('.pl-item-checkbox');

    checkboxes.forEach((chk, idx) => {
      chk.checked = !chk.checked;
      const row = document.getElementById(`pl_item_${idx}`);
      if (chk.checked) {
        selectedPlaylistIndices.add(idx);
        if (row) row.classList.add('selected');
      } else {
        selectedPlaylistIndices.delete(idx);
        if (row) row.classList.remove('selected');
      }
    });

    updatePlaylistSelectionSummary();
  });

  // Close Playlist Section
  if (btnClosePlaylistSection) {
    btnClosePlaylistSection.addEventListener('click', () => {
      playlistSection.style.display = 'none';
    });
  }

  // Download Selected Videos in Playlist (3-Worker Parallel Execution into Dedicated Subfolder)
  btnDownloadSelectedPlaylist.addEventListener('click', async () => {
    if (!currentPlaylistData || !currentPlaylistData.entries) return;
    const selectedEntries = currentPlaylistData.entries.filter((_, idx) => selectedPlaylistIndices.has(idx));

    if (selectedEntries.length === 0) {
      showToast('Please select at least 1 video to download.', 'warning');
      return;
    }

    const selectedQuality = playlistQualitySelect.value || 'best';
    await triggerPlaylistDownload({
      title: currentPlaylistData.title || 'Playlist',
      entries: selectedEntries
    }, selectedQuality);
  });

  // Trigger search button
  btnSearch.addEventListener('click', () => analyzeUrl('auto'));

  // Start Download from Analyzed Card
  btnAnalyzedDownload.addEventListener('click', async () => {
    if (!currentFetchedVideo) return;
    if (currentFetchedVideo.is_playlist) {
      triggerPlaylistDownload(currentFetchedVideo, 'best');
    } else {
      triggerDownload(currentFetchedVideo, 'best');
    }
  });

  // Open Options Modal from Analyzed Card
  btnAnalyzedOptions.addEventListener('click', () => {
    if (!currentFetchedVideo) return;
    openDownloadModal(currentFetchedVideo);
  });

  // Fast Download (1-Click Instant Download)
  btnDirectDownload.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
      showToast('Please enter a YouTube link first.', 'warning');
      urlInput.focus();
      return;
    }

    btnDirectDownload.disabled = true;
    const orig = btnDirectDownload.innerHTML;
    btnDirectDownload.innerHTML = 'Connecting...';

    let info = currentFetchedVideo;
    if (!info || (info.url !== url && !url.includes(info.id || '___'))) {
      info = await callApi('fetch_info', url, 'auto');
    }

    btnDirectDownload.disabled = false;
    btnDirectDownload.innerHTML = orig;

    if (!info || !info.success) {
      showToast(info?.error || 'Failed to fetch video details.', 'error');
      return;
    }

    info.url = info.url || url;
    currentFetchedVideo = info;

    if (info.is_playlist) {
      renderPlaylistSection(info);
    } else {
      triggerDownload(info, 'best');
    }
  });

  // Open Modal to select Quality
  function openDownloadModal(info) {
    const fallback = getFallbackThumbnail(info.title, info.is_playlist ? 'playlist' : 'video');
    modalThumb.src = info.thumbnail || fallback;
    modalThumb.onerror = () => { modalThumb.src = fallback; };
    modalTitle.textContent = info.title;
    modalChannel.textContent = info.channel || (info.is_playlist ? 'Playlist' : 'YouTube');
    modalDuration.textContent = info.duration_string || `${info.duration || 0}s`;

    downloadModal.style.display = 'flex';
  }

  // Trigger Single Video Download
  async function triggerDownload(info, quality = 'best', playlistTitle = '') {
    const payload = {
      url: info.url || urlInput.value.trim(),
      quality: quality,
      title: info.title,
      thumbnail: info.thumbnail,
      duration: info.duration_secs || info.duration || 0,
      playlist_title: playlistTitle || (info.playlist_title || '')
    };

    const res = await callApi('start_download', payload);
    if (res && res.success) {
      const dl = res.download || {
        id: res.download_id,
        title: info.title,
        thumbnail: info.thumbnail,
        quality: quality,
        status: 'downloading',
        progress: 0,
        speed: 'Connecting...',
        eta: 'Calculating...',
        downloaded: '0 MB',
        total: 'Calculating...'
      };
      runningDownloads[res.download_id] = dl;
      showToast(`Started download: ${info.title.slice(0, 25)}...`, 'success');

      switchTab('downloaded');
      renderRunningDownloads();
    } else {
      showToast(res?.error || 'Failed to start download.', 'error');
    }
  }

  // Trigger Entire / Selected Playlist Download (3 Parallel Workers into Subfolder)
  async function triggerPlaylistDownload(info, quality = 'best') {
    const entries = info.entries || [];
    const plTitle = info.title || (currentPlaylistData ? currentPlaylistData.title : 'Playlist');
    const payload = {
      title: plTitle,
      entries: entries,
      quality: quality
    };

    const res = await callApi('start_playlist_download', payload);
    if (res && res.success) {
      showToast(`Downloading ${entries.length} videos into folder "${plTitle.slice(0, 22)}..." (3 parallel processes)!`, 'success');
      switchTab('downloaded');
      refreshRunningDownloads();
    } else {
      showToast(res?.error || 'Failed to start playlist download.', 'error');
    }
  }

  // Quality chip selection in modal
  qualityOptions.addEventListener('change', (e) => {
    if (e.target.name === 'quality') {
      document.querySelectorAll('.quality-chip').forEach(c => c.classList.remove('selected'));
      e.target.closest('.quality-chip').classList.add('selected');
    }
  });

  btnStartDownload.addEventListener('click', async () => {
    if (!currentFetchedVideo) return;
    const selectedQuality = document.querySelector('input[name="quality"]:checked')?.value || 'best';
    downloadModal.style.display = 'none';

    if (currentFetchedVideo.is_playlist) {
      triggerPlaylistDownload(currentFetchedVideo, selectedQuality);
    } else {
      triggerDownload(currentFetchedVideo, selectedQuality);
    }
  });

  btnCloseDownloadModal.addEventListener('click', () => downloadModal.style.display = 'none');
  btnCancelModal.addEventListener('click', () => downloadModal.style.display = 'none');

  // Cancel Running Download
  async function cancelDownload(id) {
    const res = await callApi('cancel_download', id);
    if (res && res.success) {
      delete runningDownloads[id];
      renderRunningDownloads();
      showToast('Download cancelled.', 'info');
    }
  }

  // Render Running Downloads List
  function renderRunningDownloads() {
    const list = Object.values(runningDownloads);
    const count = list.length;
    runningCountBadge.textContent = count;

    const btnCancelAll = document.getElementById('btnCancelAllRunning');
    if (count > 0) {
      downloadedBadge.textContent = count;
      downloadedBadge.style.display = 'inline-block';
      emptyRunningCard.style.display = 'none';
      if (btnCancelAll) btnCancelAll.style.display = 'inline-flex';
    } else {
      downloadedBadge.style.display = 'none';
      emptyRunningCard.style.display = 'block';
      if (btnCancelAll) btnCancelAll.style.display = 'none';
    }

    Array.from(runningDownloadsList.children).forEach(child => {
      if (child !== emptyRunningCard) child.remove();
    });

    list.forEach(item => {
      const fallback = getFallbackThumbnail(item.title, item.quality === 'mp3' ? 'audio' : 'video');
      const card = document.createElement('div');
      card.className = 'running-download-card';
      card.id = `running_card_${item.id}`;
      
      let statsText = '';
      if (item.status === 'queued') {
        statsText = `⏳ In Queue • Waiting (3 Parallel active)`;
      } else if (item.status === 'processing') {
        statsText = `⚡ Merging & Finalizing...`;
      } else {
        statsText = `${item.progress || 0}% • ${item.speed || '0 MB/s'} • ETA: ${item.eta || 'Calculating...'} • ${item.downloaded || '0 MB'} / ${item.total || '0 MB'}`;
      }

      card.innerHTML = `
        <div class="running-top-row">
          <div class="running-info-left">
            <img src="${item.thumbnail || fallback}" alt="Thumb" class="running-thumb" onerror="this.src='${fallback}'"/>
            <div class="running-title-col">
              <span class="running-title" title="${item.title}">${item.title}</span>
              <span class="running-stats-row" id="stats_${item.id}">
                ${statsText}
              </span>
            </div>
          </div>
          <button class="btn-cancel-running" title="Cancel Download" data-id="${item.id}">✕</button>
        </div>
        <div class="running-progress-track">
          <div class="running-progress-fill" id="fill_${item.id}" style="width: ${Math.min(item.progress || 0, 100)}%;"></div>
        </div>
      `;

      card.querySelector('.btn-cancel-running').addEventListener('click', () => cancelDownload(item.id));
      runningDownloadsList.appendChild(card);
    });
  }

  // Update existing card progress smoothly without re-rendering DOM
  function updateRunningCard(data) {
    if (!data || !data.id) return;
    if (runningDownloads[data.id]) {
      Object.assign(runningDownloads[data.id], data);
    } else {
      runningDownloads[data.id] = data;
      renderRunningDownloads();
      return;
    }

    const fill = document.getElementById(`fill_${data.id}`);
    const stats = document.getElementById(`stats_${data.id}`);
    if (fill) fill.style.width = `${Math.min(data.progress || 0, 100)}%`;
    if (stats) {
      if (data.status === 'queued') {
        stats.textContent = `⏳ In Queue • Waiting (3 Parallel active)`;
      } else if (data.status === 'processing') {
        stats.textContent = `⚡ Merging & Finalizing...`;
      } else {
        stats.textContent = `${data.progress || 0}% • ${data.speed || '0 MB/s'} • ETA: ${data.eta || '0s'} • ${data.downloaded || ''} / ${data.total || ''}`;
      }
    }
  }

  // Render Completed Downloads List (Auto-clears items older than 10 minutes)
  function renderCompletedDownloads(downloaded) {
    const nowSec = Date.now() / 1000;
    const validItems = (downloaded || []).filter(item => {
      if (!item.completed_at) return true;
      return (nowSec - Number(item.completed_at)) <= 600;
    });

    completedCountBadge.textContent = validItems.length;
    completedDownloadsList.innerHTML = '';

    if (validItems.length === 0) {
      completedDownloadsList.innerHTML = `
        <div class="empty-state-card">
          <span class="empty-icon">📥</span>
          <h4>No recent completed downloads</h4>
          <p>Downloaded videos appear here (history automatically clears after 10 minutes).</p>
        </div>
      `;
      return;
    }

    validItems.forEach(item => {
      const fallback = getFallbackThumbnail(item.title, item.type || 'video');
      const row = document.createElement('div');
      row.className = 'download-item-card';

      let autoClearText = '';
      if (item.completed_at) {
        const remainingSec = Math.max(0, 600 - Math.floor(nowSec - Number(item.completed_at)));
        const remMins = Math.ceil(remainingSec / 60);
        autoClearText = ` • <span style="color:#a78bfa; font-weight:600;">⏱️ Clears in ${remMins}m</span>`;
      }

      row.innerHTML = `
        <div class="dl-item-left">
          <img src="${item.thumbnail || fallback}" alt="Thumb" class="dl-item-thumb" onerror="this.src='${fallback}'"/>
          <div class="dl-item-details">
            <span class="dl-item-title" title="${item.title}">${item.title}</span>
            <span class="dl-item-meta">${item.duration || ''} • ${item.date || ''} • ${item.quality ? item.quality.toUpperCase() : 'HD'}${autoClearText}</span>
          </div>
        </div>
        <div class="dl-item-actions">
          <button class="btn-primary-small btn-folder-item" title="Open containing folder in Windows Explorer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            <span>Show in Folder</span>
          </button>
          <button class="btn-secondary btn-del-item" style="height: 34px; padding: 0 12px; color: #f43f5e;" title="Remove from history">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      `;

      row.querySelector('.btn-folder-item').addEventListener('click', () => callApi('open_in_folder', item.file_path));
      row.querySelector('.btn-del-item').addEventListener('click', async () => {
        if (confirm(`Remove "${item.title}" from history?`)) {
          const res = await callApi('delete_item', item.id, false);
          if (res && res.success) {
            loadLibraryData();
            showToast('Item removed from history.', 'info');
          }
        }
      });

      completedDownloadsList.appendChild(row);
    });
  }

  // Load Library Data
  async function loadLibraryData() {
    const lib = await callApi('get_library');
    if (lib) {
      currentLibrary = lib;
      renderCompletedDownloads(lib.downloaded || []);
    }
  }

  // Refresh Running Downloads from Backend
  async function refreshRunningDownloads() {
    const res = await callApi('get_active_downloads');
    if (res && res.success && res.downloads) {
      const activeMap = {};
      res.downloads.forEach(dl => { activeMap[dl.id] = dl; });
      runningDownloads = activeMap;
      renderRunningDownloads();
    }
  }

  // Video Player Modal
  function playVideo(item) {
    currentPlayingFile = item.file_path;
    playerVideoTitle.textContent = item.title || 'Pro Downloader Player';

    if (item.file_path) {
      const streamUrl = `/stream?path=${encodeURIComponent(item.file_path)}`;
      videoPlayerElement.src = streamUrl;
      playerModal.style.display = 'flex';
      videoPlayerElement.play().catch(e => console.log('Autoplay handled:', e));
    } else if (item.url) {
      showToast(`Opening online video: ${item.title}`, 'info');
      window.open(item.url, '_blank');
    } else {
      showToast('No media file found for this video.', 'warning');
    }
  }

  btnClosePlayer.addEventListener('click', () => {
    videoPlayerElement.pause();
    videoPlayerElement.src = '';
    playerModal.style.display = 'none';
  });

  btnOpenCurrentFolder.addEventListener('click', () => {
    if (currentPlayingFile) {
      callApi('open_in_folder', currentPlayingFile);
    }
  });

  if (btnOpenDownloadsFolderTop) {
    btnOpenDownloadsFolderTop.addEventListener('click', () => callApi('open_in_folder', ''));
  }
  if (btnOpenFolderCompleted) {
    btnOpenFolderCompleted.addEventListener('click', () => callApi('open_in_folder', ''));
  }

  // Stop All Running / Queued Downloads
  const btnCancelAllRunning = document.getElementById('btnCancelAllRunning');
  if (btnCancelAllRunning) {
    btnCancelAllRunning.addEventListener('click', async () => {
      const activeKeys = Object.keys(runningDownloads);
      if (activeKeys.length === 0) return;
      if (confirm(`Stop and cancel all ${activeKeys.length} running and queued downloads?`)) {
        await callApi('cancel_all_downloads');
        runningDownloads = {};
        renderRunningDownloads();
        showToast('All downloads stopped.', 'info');
      }
    });
  }

  // Clear All Completed Download History
  const btnClearAllHistory = document.getElementById('btnClearAllHistory');
  if (btnClearAllHistory) {
    btnClearAllHistory.addEventListener('click', async () => {
      const histCount = (currentLibrary.downloaded || []).length;
      if (histCount === 0) {
        showToast('Download history is already empty.', 'info');
        return;
      }
      if (confirm(`Clear all ${histCount} completed download history items? (Downloaded files will remain safely on your computer)`)) {
        const res = await callApi('clear_download_history', false);
        if (res && res.success) {
          loadLibraryData();
          showToast('Completed download history cleared.', 'success');
        }
      }
    });
  }

  // Settings Handlers
  function openSettingsModal() {
    callApi('get_settings').then(settings => {
      if (settings) {
        settingsDownloadFolder.value = settings.download_folder || '';
        settingsDefaultQuality.value = settings.default_quality || 'best';
      }
      settingsModal.style.display = 'flex';
    });
  }

  btnSettings.addEventListener('click', openSettingsModal);
  if (btnSidebarSettings) btnSidebarSettings.addEventListener('click', openSettingsModal);

  btnBrowseFolder.addEventListener('click', async () => {
    const folder = await callApi('select_download_folder');
    if (folder) {
      settingsDownloadFolder.value = folder;
    }
  });

  btnSaveSettings.addEventListener('click', async () => {
    const newSettings = {
      download_folder: settingsDownloadFolder.value,
      default_quality: settingsDefaultQuality.value
    };
    await callApi('save_settings', newSettings);
    showToast('Preferences saved.', 'success');
    settingsModal.style.display = 'none';
  });

  btnCloseSettings.addEventListener('click', () => settingsModal.style.display = 'none');
  btnCancelSettings.addEventListener('click', () => settingsModal.style.display = 'none');

  // Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      downloadModal.style.display = 'none';
      settingsModal.style.display = 'none';
      if (playerModal.style.display === 'flex') {
        btnClosePlayer.click();
      }
    }
    if (e.code === 'Space' && playerModal.style.display === 'flex' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      if (videoPlayerElement.paused) videoPlayerElement.play();
      else videoPlayerElement.pause();
    }
  });

  // Real-Time Download Hooks from Python Backend
  window.onDownloadProgress = function (data) {
    if (!data) return;
    updateRunningCard(data);
  };

  window.onDownloadComplete = function (data) {
    if (data && data.id && runningDownloads[data.id]) {
      delete runningDownloads[data.id];
    }
    renderRunningDownloads();
    showToast(data.message || 'Download completed successfully!', 'success');
    loadLibraryData();
  };

  window.onDownloadError = function (data) {
    if (data && data.id && runningDownloads[data.id]) {
      delete runningDownloads[data.id];
    }
    renderRunningDownloads();
    showToast(`Download failed: ${data.error}`, 'error');
  };

  // Periodic status & history auto-clean poll
  setInterval(() => {
    if (Object.keys(runningDownloads).length > 0 || viewDownloaded.style.display === 'flex') {
      refreshRunningDownloads();
      loadLibraryData();
    }
  }, 3000);

  // Initialize
  window.addEventListener('pywebviewready', () => {
    loadLibraryData();
    refreshRunningDownloads();
  });

  setTimeout(() => {
    loadLibraryData();
    refreshRunningDownloads();
  }, 400);
});
