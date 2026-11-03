/**
 * PC Software Hub - Auto-Discovery & Interactive Client Logic
 * Automatically detects and renders branches pushed to GitHub repository
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const softwareGrid = document.getElementById("software-grid");
  const searchInput = document.getElementById("search-input");
  const clearSearchBtn = document.getElementById("clear-search");
  const categoryChips = document.querySelectorAll(".chip");
  const cloneModeRadios = document.querySelectorAll('input[name="clone-mode"]');
  const resultsCount = document.getElementById("results-count");
  const noResults = document.getElementById("no-results");
  const resetFilterBtn = document.getElementById("btn-reset-filter");
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toast-message");
  const guideModal = document.getElementById("guide-modal");
  const btnOpenGuide = document.getElementById("btn-open-guide");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnModalOk = document.getElementById("btn-modal-ok");
  const softwareCountEl = document.getElementById("software-count");
  const syncIndicator = document.getElementById("sync-indicator");
  const syncStatusText = document.getElementById("sync-status-text");
  const btnSyncBranches = document.getElementById("btn-sync-branches");
  const btnRefreshGrid = document.getElementById("btn-refresh-grid");

  // State
  let softwareItems = [];
  let currentSearch = "";
  let currentCategory = "all";
  let currentCloneMode = "single"; // 'single' | 'cd' | 'standard'
  let toastTimeout = null;

  // Local Storage Cache Keys
  const CACHE_KEY = "pc_software_cached_branches_v2";

  // Helper: Format branch name into clean display title
  function formatBranchTitle(branch) {
    // Known acronyms to capitalize
    const acronyms = ["vlc", "idm", "ide", "gui", "cli", "api", "obs", "sdk", "zip", "rar", "7z", "os", "pc"];

    return branch
      .replace(/[-_]+/g, " ")
      .split(" ")
      .map(word => {
        const lower = word.toLowerCase();
        if (acronyms.includes(lower)) return lower.toUpperCase();
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      })
      .join(" ");
  }

  // Helper: Auto-detect category and icon from branch name
  function autoDetectMetadata(branch) {
    const lower = branch.toLowerCase();

    // Media
    if (/vlc|player|media|video|audio|music|sound|mp3|mp4|stream|obs|camera|screen/i.test(lower)) {
      return {
        category: "media",
        categoryLabel: "Media Player",
        icon: "🎬"
      };
    }

    // Development
    if (/code|git|dev|ide|editor|studio|terminal|cmd|python|node|compiler|cpp|java/i.test(lower)) {
      return {
        category: "development",
        categoryLabel: "Development",
        icon: "💻"
      };
    }

    // Utilities & Archivers
    if (/zip|rar|7z|tar|compress|archiver/i.test(lower)) {
      return {
        category: "utilities",
        categoryLabel: "Archiver",
        icon: "📦"
      };
    }

    if (/download|idm|accelerator|torrent|fetch/i.test(lower)) {
      return {
        category: "utilities",
        categoryLabel: "Downloader",
        icon: "⚡"
      };
    }

    if (/tool|util|script|cleaner|driver|system|benchmark|manager/i.test(lower)) {
      return {
        category: "utilities",
        categoryLabel: "Utilities",
        icon: "🛠️"
      };
    }

    // Default
    return {
      category: "utilities",
      categoryLabel: "Utilities",
      icon: "🚀"
    };
  }

  // Fetch branches from GitHub API (Live) with fallback to branches.json and localStorage
  async function loadBranches(forceRefresh = false) {
    setSyncStatus(true, "Scanning GitHub branches...");

    let branchNames = [];

    // 1. Try Live GitHub REST API
    try {
      const response = await fetch(REPO_CONFIG.apiBranchesUrl, {
        headers: { Accept: "application/vnd.github.v3+json" }
      });

      if (response.ok) {
        const apiData = await response.json();
        if (Array.isArray(apiData)) {
          branchNames = apiData
            .map(b => b.name)
            .filter(name => !SYSTEM_BRANCHES.includes(name));

          // Save to local cache
          localStorage.setItem(CACHE_KEY, JSON.stringify(branchNames));
          setSyncStatus(false, "Live Auto-Sync Active");
        }
      } else {
        throw new Error(`GitHub API Status: ${response.status}`);
      }
    } catch (apiErr) {
      console.warn("GitHub live API unavailable (possible rate limit), falling back:", apiErr);

      // 2. Try branches.json static fallback
      try {
        const jsonResp = await fetch("branches.json?t=" + Date.now());
        if (jsonResp.ok) {
          const jsonData = await jsonResp.json();
          if (Array.isArray(jsonData) && jsonData.length > 0) {
            branchNames = jsonData.filter(name => !SYSTEM_BRANCHES.includes(name));
            setSyncStatus(false, "Static branches.json Sync");
          }
        }
      } catch (jsonErr) {
        console.warn("branches.json unavailable:", jsonErr);
      }

      // 3. Try localStorage cache
      if (branchNames.length === 0) {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          try {
            branchNames = JSON.parse(cached);
            setSyncStatus(false, "Cached Sync");
          } catch (e) {}
        }
      }

      // 4. Default fallback: Curated software list
      if (branchNames.length === 0 && typeof CURATED_SOFTWARE !== "undefined") {
        branchNames = Object.keys(CURATED_SOFTWARE);
        setSyncStatus(false, "Default Catalog");
      }
    }

    // Build items from branchNames
    softwareItems = await buildSoftwareItems(branchNames);

    if (softwareCountEl) {
      softwareCountEl.textContent = softwareItems.length;
    }

    renderSoftwareCards();

    if (forceRefresh) {
      showToast(`Synced with GitHub! Found ${softwareItems.length} software branches.`);
    }
  }

  // Set Sync indicator status in header
  function setSyncStatus(isSyncing, text) {
    if (syncIndicator) {
      if (isSyncing) syncIndicator.classList.add("syncing");
      else syncIndicator.classList.remove("syncing");
    }
    if (syncStatusText) {
      syncStatusText.textContent = text;
    }
  }

  // Build software card models for all detected branches
  async function buildSoftwareItems(branchNames) {
    const items = [];

    for (const branch of branchNames) {
      // Check if we have curated metadata
      if (typeof CURATED_SOFTWARE !== "undefined" && CURATED_SOFTWARE[branch]) {
        const curated = CURATED_SOFTWARE[branch];
        items.push({
          id: branch,
          branch: branch,
          name: curated.name || formatBranchTitle(branch),
          category: curated.category || "utilities",
          categoryLabel: curated.categoryLabel || "Utilities",
          version: curated.version || "Latest",
          icon: curated.icon || "💻",
          description: curated.description || `Portable standalone version of ${curated.name || branch}.`,
          tags: curated.tags || ["Portable", "Windows"],
          folderName: curated.folderName || branch
        });
      } else {
        // Auto-generate metadata dynamically from branch name
        const detected = autoDetectMetadata(branch);
        const title = formatBranchTitle(branch);
        const tags = branch
          .split(/[-_]+/)
          .filter(t => t.length > 1)
          .map(t => t.charAt(0).toUpperCase() + t.slice(1));

        items.push({
          id: branch,
          branch: branch,
          name: title,
          category: detected.category,
          categoryLabel: detected.categoryLabel,
          version: "Latest",
          icon: detected.icon,
          description: `Portable standalone version of ${title}. Ready to clone and use.`,
          tags: tags.length > 0 ? tags : ["Portable", "Windows"],
          folderName: branch
        });
      }
    }

    return items;
  }

  // Generate Git Clone command string based on current mode
  function generateCloneCommand(item) {
    const repo = REPO_CONFIG.repoUrl;
    const branch = item.branch;
    const folder = item.folderName || item.branch;

    switch (currentCloneMode) {
      case "cd":
        return `git clone -b ${branch} --single-branch ${repo} ${folder} && cd ${folder}`;
      case "standard":
        return `git clone -b ${branch} ${repo} ${folder}`;
      case "single":
      default:
        return `git clone -b ${branch} --single-branch ${repo} ${folder}`;
    }
  }

  // Generate direct ZIP download URL from GitHub
  function generateZipUrl(branch) {
    return `${REPO_CONFIG.githubBaseUrl}/archive/refs/heads/${branch}.zip`;
  }

  // Generate GitHub branch view URL
  function generateBranchUrl(branch) {
    return `${REPO_CONFIG.githubBaseUrl}/tree/${branch}`;
  }

  // Render cards
  function renderSoftwareCards() {
    softwareGrid.innerHTML = "";

    const filtered = softwareItems.filter(item => {
      // Category match
      const categoryMatch = currentCategory === "all" || item.category === currentCategory;

      // Search match
      const searchMatch = !currentSearch || (
        item.name.toLowerCase().includes(currentSearch) ||
        item.description.toLowerCase().includes(currentSearch) ||
        item.branch.toLowerCase().includes(currentSearch) ||
        item.tags.some(tag => tag.toLowerCase().includes(currentSearch))
      );

      return categoryMatch && searchMatch;
    });

    resultsCount.textContent = `Showing ${filtered.length} of ${softwareItems.length} software`;

    if (filtered.length === 0) {
      noResults.hidden = false;
      return;
    }
    noResults.hidden = true;

    filtered.forEach(item => {
      const card = document.createElement("article");
      card.className = "software-card";
      card.setAttribute("data-id", item.id);

      const command = generateCloneCommand(item);
      const zipUrl = generateZipUrl(item.branch);
      const branchUrl = generateBranchUrl(item.branch);

      card.innerHTML = `
        <div>
          <div class="card-top">
            <div class="card-icon-box" aria-hidden="true">${item.icon || "💻"}</div>
            <div class="card-badges">
              <span class="version-pill">${item.version || "Latest"}</span>
              <span class="branch-badge" title="Git Branch Name">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="6" y1="3" x2="6" y2="15"></line>
                  <circle cx="18" cy="6" r="3"></circle>
                  <circle cx="6" cy="18" r="3"></circle>
                  <path d="M18 9a9 9 0 0 1-9 9"></path>
                </svg>
                ${item.branch}
              </span>
            </div>
          </div>

          <div class="card-info">
            <h4 class="card-title">${item.name}</h4>
            <p class="card-desc">${item.description}</p>
            <div class="card-tags">
              ${item.tags.map(t => `<span class="tag-pill">#${t}</span>`).join("")}
            </div>
          </div>

          <div class="command-preview" title="Double click or use Copy button below">
            <code class="command-code" title="${command}">${command}</code>
          </div>
        </div>

        <div class="card-actions">
          <button type="button" class="btn btn-clone" data-action="copy-clone" data-command="${command}">
            <span class="btn-icon">⚡</span>
            <span class="btn-text">Copy Clone</span>
          </button>
          <a href="${zipUrl}" class="btn btn-zip" title="Direct download ZIP of this branch from GitHub" target="_blank" rel="noopener noreferrer">
            <span class="btn-icon">📥</span>
            <span>ZIP</span>
          </a>
          <a href="${branchUrl}" class="btn btn-branch-view" title="Inspect branch files on GitHub" target="_blank" rel="noopener noreferrer">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
          </a>
        </div>
      `;

      softwareGrid.appendChild(card);
    });

    // Attach click listener for copy buttons
    attachCardActionListeners();
  }

  // Handle clipboard copy
  function attachCardActionListeners() {
    const copyBtns = softwareGrid.querySelectorAll('button[data-action="copy-clone"]');
    copyBtns.forEach(btn => {
      btn.addEventListener("click", async () => {
        const command = btn.getAttribute("data-command");
        const success = await copyToClipboard(command);

        if (success) {
          const originalText = btn.innerHTML;
          btn.classList.add("copied");
          btn.innerHTML = `<span class="btn-icon">✓</span><span class="btn-text">Copied!</span>`;

          showToast("Command copied! Paste in your Terminal / CMD to clone and enter this branch.");

          setTimeout(() => {
            btn.classList.remove("copied");
            btn.innerHTML = originalText;
          }, 2200);
        } else {
          showToast("Failed to copy. Please copy manually from the box.");
        }
      });
    });
  }

  // Clipboard Helper with fallback
  async function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (err) {
        console.warn("Clipboard API failed, using fallback:", err);
      }
    }

    // Fallback
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      const successful = document.execCommand("copy");
      textArea.remove();
      return successful;
    } catch (err) {
      textArea.remove();
      return false;
    }
  }

  // Show Toast
  function showToast(message) {
    if (!toast) return;

    if (toastTimeout) {
      clearTimeout(toastTimeout);
    }

    toastMessage.textContent = message;
    toast.classList.add("show");
    toast.setAttribute("aria-hidden", "false");

    toastTimeout = setTimeout(() => {
      toast.classList.remove("show");
      toast.setAttribute("aria-hidden", "true");
    }, 3500);
  }

  // Search input handler
  searchInput.addEventListener("input", (e) => {
    currentSearch = e.target.value.trim().toLowerCase();
    clearSearchBtn.hidden = !currentSearch;
    renderSoftwareCards();
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    currentSearch = "";
    clearSearchBtn.hidden = true;
    searchInput.focus();
    renderSoftwareCards();
  });

  // Category filter handlers
  categoryChips.forEach(chip => {
    chip.addEventListener("click", () => {
      categoryChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      currentCategory = chip.getAttribute("data-category");
      renderSoftwareCards();
    });
  });

  // Clone Mode handlers
  cloneModeRadios.forEach(radio => {
    radio.addEventListener("change", (e) => {
      if (e.target.checked) {
        currentCloneMode = e.target.value;
        renderSoftwareCards();
        showToast(`Command format updated to: ${e.target.parentElement.textContent.trim()}`);
      }
    });
  });

  // Reset Filters
  if (resetFilterBtn) {
    resetFilterBtn.addEventListener("click", () => {
      searchInput.value = "";
      currentSearch = "";
      clearSearchBtn.hidden = true;
      currentCategory = "all";
      categoryChips.forEach(c => {
        if (c.getAttribute("data-category") === "all") c.classList.add("active");
        else c.classList.remove("active");
      });
      renderSoftwareCards();
    });
  }

  // Guide Modal Dialog Handling
  if (guideModal && btnOpenGuide) {
    btnOpenGuide.addEventListener("click", () => {
      guideModal.showModal();
    });

    if (btnCloseModal) {
      btnCloseModal.addEventListener("click", () => {
        guideModal.close();
      });
    }

    if (btnModalOk) {
      btnModalOk.addEventListener("click", () => {
        guideModal.close();
      });
    }

    // Close when clicking dialog backdrop
    guideModal.addEventListener("click", (e) => {
      const rect = guideModal.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        guideModal.close();
      }
    });
  }

  // Sync branches manually
  function triggerManualSync(button) {
    if (button) {
      const icon = button.querySelector(".icon");
      if (icon) icon.classList.add("spin-icon");
      setTimeout(() => {
        if (icon) icon.classList.remove("spin-icon");
      }, 1200);
    }
    loadBranches(true);
  }

  if (btnSyncBranches) {
    btnSyncBranches.addEventListener("click", () => triggerManualSync(btnSyncBranches));
  }

  if (btnRefreshGrid) {
    btnRefreshGrid.addEventListener("click", () => triggerManualSync(btnRefreshGrid));
  }

  // Initial load
  loadBranches(false);
});
