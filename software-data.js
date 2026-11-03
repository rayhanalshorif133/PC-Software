// Central configuration and software list
// You can easily add, edit or remove software from this list!

const REPO_CONFIG = {
  repoUrl: "https://github.com/rayhanalshorif133/PC-Software.git",
  githubBaseUrl: "https://github.com/rayhanalshorif133/PC-Software",
  owner: "rayhanalshorif133",
  repoName: "PC-Software"
};

const SOFTWARE_LIST = [
  {
    id: "idm-downloader",
    name: "Internet Download Manager (Portable)",
    branch: "idm-downloader",
    category: "utilities",
    categoryLabel: "Utilities",
    version: "v6.42",
    icon: "⚡",
    description: "High-speed multi-threaded download accelerator and download management tool.",
    tags: ["Downloader", "Accelerator", "Portable", "Fast"],
    folderName: "IDM-Portable",
    featured: true
  },
  {
    id: "vlc-media-player",
    name: "VLC Media Player (Portable)",
    branch: "vlc-media-player",
    category: "media",
    categoryLabel: "Media Player",
    version: "v3.0.20",
    icon: "🎬",
    description: "Universal open-source multimedia player that plays most video and audio codecs.",
    tags: ["Video Player", "Audio", "All Codecs", "Open Source"],
    folderName: "VLC-Portable",
    featured: true
  },
  {
    id: "vscode-portable",
    name: "VS Code Portable Suite",
    branch: "vscode-portable",
    category: "development",
    categoryLabel: "Development",
    version: "v1.95",
    icon: "💻",
    description: "Lightweight and powerful code editor with essential developer extensions & config.",
    tags: ["Code Editor", "IDE", "Extensions", "Developer"],
    folderName: "VSCode-Portable",
    featured: true
  },
  {
    id: "7zip-archiver",
    name: "7-Zip Archiver & Tools",
    branch: "7zip-archiver",
    category: "utilities",
    categoryLabel: "Utilities",
    version: "v24.08",
    icon: "📦",
    description: "High compression ratio file archiver with 7z, ZIP, RAR, TAR and GZ support.",
    tags: ["Archiver", "Zip / Rar", "Compression", "Lightweight"],
    folderName: "7Zip-Utility",
    featured: false
  },
  {
    id: "git-quick-tools",
    name: "Git Quick Tools & Scripts",
    branch: "git-quick-tools",
    category: "development",
    categoryLabel: "Dev Tools",
    version: "v2.1",
    icon: "🛠️",
    description: "Handy Windows automation scripts, terminal helpers, and Git productivity enhancers.",
    tags: ["Terminal", "Automation", "Batch/PS", "Productivity"],
    folderName: "Git-QuickTools",
    featured: false
  }
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { REPO_CONFIG, SOFTWARE_LIST };
}
