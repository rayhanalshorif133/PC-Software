/**
 * PC Software Hub - Interactive Client Logic
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

  // State
  let currentSearch = "";
  let currentCategory = "all";
  let currentCloneMode = "single"; // 'single' | 'cd' | 'standard'
  let toastTimeout = null;

  if (softwareCountEl && Array.isArray(SOFTWARE_LIST)) {
    softwareCountEl.textContent = SOFTWARE_LIST.length;
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

    const filtered = SOFTWARE_LIST.filter(item => {
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

    resultsCount.textContent = `Showing ${filtered.length} software`;

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

  // Initial render
  renderSoftwareCards();
});
