// Central repository configuration and curated metadata
// Whenever you push a branch to GitHub, the website will AUTOMATICALLY discover it!
// You can optionally add custom curated descriptions here, but it's 100% optional!

const REPO_CONFIG = {
  owner: "rayhanalshorif133",
  repoName: "PC-Software",
  repoUrl: "https://github.com/rayhanalshorif133/PC-Software.git",
  githubBaseUrl: "https://github.com/rayhanalshorif133/PC-Software",
  apiBranchesUrl: "https://api.github.com/repos/rayhanalshorif133/PC-Software/branches",
  rawContentBaseUrl: "https://raw.githubusercontent.com/rayhanalshorif133/PC-Software"
};

// Ignored system branches that are not software
const SYSTEM_BRANCHES = ["main", "gh-pages", "master"];

// Optional curated metadata for known software
// Any branch NOT listed here will still be auto-discovered and displayed dynamically!
const CURATED_SOFTWARE = {
  "idm-downloader": {
    name: "Internet Download Manager (Portable)",
    category: "utilities",
    categoryLabel: "Utilities",
    version: "v6.42",
    icon: "⚡",
    description: "High-speed multi-threaded download accelerator and download management tool.",
    tags: ["Downloader", "Accelerator", "Portable", "Fast"],
    folderName: "IDM-Portable"
  },
  "vlc-media-player": {
    name: "VLC Media Player (Portable)",
    category: "media",
    categoryLabel: "Media Player",
    version: "v3.0.20",
    icon: "🎬",
    description: "Universal open-source multimedia player that plays most video and audio codecs.",
    tags: ["Video Player", "Audio", "All Codecs", "Open Source"],
    folderName: "VLC-Portable"
  },
  "vscode-portable": {
    name: "VS Code Portable Suite",
    category: "development",
    categoryLabel: "Development",
    version: "v1.95",
    icon: "💻",
    description: "Lightweight and powerful code editor with essential developer extensions & config.",
    tags: ["Code Editor", "IDE", "Extensions", "Developer"],
    folderName: "VSCode-Portable"
  },
  "7zip-archiver": {
    name: "7-Zip Archiver & Tools",
    category: "utilities",
    categoryLabel: "Utilities",
    version: "v24.08",
    icon: "📦",
    description: "High compression ratio file archiver with 7z, ZIP, RAR, TAR and GZ support.",
    tags: ["Archiver", "Zip / Rar", "Compression", "Lightweight"],
    folderName: "7Zip-Utility"
  },
  "git-quick-tools": {
    name: "Git Quick Tools & Scripts",
    category: "development",
    categoryLabel: "Dev Tools",
    version: "v2.1",
    icon: "🛠️",
    description: "Handy Windows automation scripts, terminal helpers, and Git productivity enhancers.",
    tags: ["Terminal", "Automation", "Batch/PS", "Productivity"],
    folderName: "Git-QuickTools"
  }
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { REPO_CONFIG, SYSTEM_BRANCHES, CURATED_SOFTWARE };
}
