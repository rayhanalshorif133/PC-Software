# 💻 PC Software Hub

> **Single GitHub Repo • Branch-Isolated Portable Softwares • 1-Click Clone & Direct Download**

🌐 **Live GitHub Pages Portal:** [https://rayhanalshorif133.github.io/PC-Software/](https://rayhanalshorif133.github.io/PC-Software/)

---

## 🚀 How It Works (কিভাবে কাজ করে)

এই রিপোজিটরিতে একাধিক পিসি সফটওয়্যার আলাদা আলাদা **Git Branch**-এ রাখা হয়েছে। লাইভ ওয়েবসাইটে গিয়ে যে কোনো সফটওয়্যার এর পাশে **"⚡ Copy Clone"** বাটনে এক ক্লিক করলেই কমান্ড কপি হয়ে যাবে। টার্মিনালে রান করলেই সরাসরি সেই সফটওয়্যারের ব্রাঞ্চ ক্লোন হয়ে যাবে!

এছাড়া ব্রাউজার থেকে সরাসরি **"📥 Download ZIP"** এ ক্লিক করে কোনো গিট ছাড়াই সফটওয়্যার ডাউনলোড করা যাবে।

### ⚡ 1-Click Git Clone Commands (প্রত্যেক ব্রাঞ্চের জন্য)

| Software Name | Branch Name | Direct Git Clone Command | Direct ZIP |
| :--- | :--- | :--- | :--- |
| **IDM Downloader** | `idm-downloader` | `git clone -b idm-downloader --single-branch https://github.com/rayhanalshorif133/PC-Software.git IDM-Portable` | [Download ZIP](https://github.com/rayhanalshorif133/PC-Software/archive/refs/heads/idm-downloader.zip) |
| **VLC Media Player** | `vlc-media-player` | `git clone -b vlc-media-player --single-branch https://github.com/rayhanalshorif133/PC-Software.git VLC-Portable` | [Download ZIP](https://github.com/rayhanalshorif133/PC-Software/archive/refs/heads/vlc-media-player.zip) |
| **VS Code Portable** | `vscode-portable` | `git clone -b vscode-portable --single-branch https://github.com/rayhanalshorif133/PC-Software.git VSCode-Portable` | [Download ZIP](https://github.com/rayhanalshorif133/PC-Software/archive/refs/heads/vscode-portable.zip) |
| **7-Zip Archiver** | `7zip-archiver` | `git clone -b 7zip-archiver --single-branch https://github.com/rayhanalshorif133/PC-Software.git 7Zip-Utility` | [Download ZIP](https://github.com/rayhanalshorif133/PC-Software/archive/refs/heads/7zip-archiver.zip) |
| **Git Quick Tools** | `git-quick-tools` | `git clone -b git-quick-tools --single-branch https://github.com/rayhanalshorif133/PC-Software.git Git-QuickTools` | [Download ZIP](https://github.com/rayhanalshorif133/PC-Software/archive/refs/heads/git-quick-tools.zip) |

---

## 🛠️ GitHub Pages চালু করার নিয়ম (Enable GitHub Pages)

1. এই রিপোজিটরিটি গিটহাবে পুশ করার পর আপনার রিপোজিটরি লিংকে যান:  
   `https://github.com/rayhanalshorif133/PC-Software`
2. উপরে **Settings** ট্যাবে ক্লিক করুন।
3. বাম পাশের মেন্যু থেকে **Pages** এ ক্লিক করুন।
4. **Build and deployment** সেকশনে:
   - Source: **Deploy from a branch**
   - Branch: **`main`** (অথবা `gh-pages`), Folder: **`/ (root)`**
5. **Save** বাটনে ক্লিক করুন।
6. ১-২ মিনিট পর আপনার ওয়েবসাইট লাইভ হয়ে যাবে:  
   👉 **`https://rayhanalshorif133.github.io/PC-Software/`**

---

## ➕ নতুন কোনো সফটওয়্যারের ব্রাঞ্চ কিভাবে যুক্ত করবেন?

### অটোমেটিক পদ্ধতি (Windows Helper Script):
1. ডিরেক্টরিতে থাকা `add-software.bat` ডাবল ক্লিক করে রান করুন।
2. ব্রাঞ্চ নাম দিন (যেমন: `obs-studio`), স্ক্রিপ্ট নিজে থেকেই ব্রাঞ্চ বানিয়ে ক্লিন করে দেবে।
3. আপনার ফাইলগুলো পেস্ট করে পুশ করে দিন!

### ম্যানুয়াল পদ্ধতি (Git CLI):
```bash
# ১. সম্পূর্ণ ফ্রেশ/অনাথ ব্রাঞ্চ তৈরি করুন
git checkout --orphan obs-studio

# ২. আগের ফাইল পরিষ্কার করুন
git rm -rf .

# ৩. আপনার সফটওয়্যারের ফাইলগুলো এই ফোল্ডারে রাখুন এবং কমিট করুন
git add .
git commit -m "Add OBS Studio portable"
git push -u origin obs-studio

# ৪. এবার ওয়েবসাইটের মেইন ব্রাঞ্চে ফেরত যান
git checkout main

# ৫. software-data.js ফাইলে নতুন সফটওয়্যারের তথ্য যোগ করে পুশ করুন:
git add software-data.js
git commit -m "Add OBS Studio to portal list"
git push origin main
```

---

## 💡 সুবিধা (Advantages)
- **Zero Space Bloat**: `--single-branch` এর কারণে ব্যবহারকারী শুধু তার কাঙ্ক্ষিত সফটওয়্যারটিই পাবে, পুরো রিপোর মেমোরি খরচ হবে না।
- **Auto Branch Switch**: ক্লোন হওয়ার সাথে সাথেই গিট ওই ব্রাঞ্চটিকে সিলেক্ট করে রাখে।
- **Organized**: সব সফটওয়্যার একটিমাত্র গিট রিপোজিটরির অধীনে সাজানো।
