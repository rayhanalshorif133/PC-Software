# 💻 PC Software Hub

> **Single GitHub Repo • Branch-Isolated Portable Softwares • Auto-Discovery & 1-Click Clone**

🌐 **Live GitHub Pages Portal:** [https://rayhanalshorif133.github.io/PC-Software/](https://rayhanalshorif133.github.io/PC-Software/)

---

## ⚡ Auto Branch Discovery (অটোমেটিক ব্রাঞ্চ ডিটেকশন)

এই প্রজেক্টে **সম্পূর্ণ অটোমেশন** সেটআপ করা হয়েছে:
- আপনি যখনই গিটহাবে কোনো নতুন ব্রাঞ্চ বানিয়ে পুশ করবেন (`git push origin <branch-name>`), **লাইভ `index.html` পেজে সেটি স্বয়ংক্রিয়ভাবে চলে আসবে!**
- কোনো কোড বা HTML/JS ফাইল ম্যানুয়ালি এডিট করার প্রয়োজন নেই।
- পেজটি সরাসরি **GitHub REST API** ও **GitHub Actions** এর মাধ্যমে লাইভ ব্রাঞ্চ লিস্ট স্ক্যান করে রেন্ডার করে।

---

## 🚀 How It Works (কিভাবে কাজ করে)

1. **1-Click Clone & Switch:** কার্ডের **"⚡ Copy Clone"** বাটনে এক ক্লিক করলেই কমান্ড কপি হবে। টার্মিনালে এন্টার দিলেই শুধু ওই সফটওয়্যারটির ব্রাঞ্চ ক্লোন হয়ে যাবে।
2. **Direct ZIP:** গিট ছাড়া সরাসরি ব্রাউজারে জিপ ফাইল ডাউনলোড করা যায়।
3. **Auto Sync:** নতুন ব্রাঞ্চ পুশ করার পর ওয়েবসাইটে ঢুকলেই তা স্বয়ংক্রিয়ভাবে কার্ড আকারে যোগ হয়ে যায়।

---

## ➕ নতুন কোনো সফটওয়্যার যোগ করার নিয়ম (মাত্র ২টি স্টেপ):

### পদ্ধতি ১: অটোমেটিক উইন্ডোজ স্ক্রিপ্ট (সবচেয়ে সহজ)
1. ফোল্ডারে থাকা **`add-software.bat`** ডাবল ক্লিক করে রান করুন।
2. সফটওয়্যারের ব্রাঞ্চের নাম দিন (যেমন: `obs-studio`)।
3. আপনার সফটওয়্যার বা ফাইলগুলো ফোল্ডারে রেখে এন্টার দিলেই এটি স্বয়ংক্রিয়ভাবে পুশ করে দেবে!

### পদ্ধতি ২: সরাসরি গিট কমান্ড (CLI)
```bash
# ১. নতুন অনাথ (orphan) ব্রাঞ্চ তৈরি করুন
git checkout --orphan obs-studio

# ২. আগের ফাইল পরিষ্কার করে আপনার সফটওয়্যারের ফাইল পেস্ট করুন
git rm -rf .
# (আপনার ফাইল রাখুন)

# ৩. কমিট এবং পুশ করুন
git add .
git commit -m "Add OBS Studio portable"
git push -u origin obs-studio

# ৪. ওয়েবসাইটের মেইন ব্রাঞ্চে ফেরত যান
git checkout main
```
> 🎉 **পুশ শেষ হওয়ার সাথে সাথে লাইভ ওয়েবসাইটে রিফ্রেশ দিন — স্বয়ংক্রিয়ভাবে নতুন সফটওয়্যারটি দেখতে পাবেন!**

---

### 🎨 কাস্টম ইনফো দিতে চাইলে (Optional `software.json`):
আপনার ব্রাঞ্চের মধ্যে যদি একটি `software.json` রাখেন, তবে সাইট সেটি রিড করে কাস্টম টাইটেল ও ডেসক্রিপশন দেখাবে (যা `add-software.bat` নিজে থেকেই বানিয়ে দেয়):
```json
{
  "name": "OBS Studio Portable",
  "version": "v30.2",
  "category": "media",
  "description": "Free and open source software for video recording and live streaming.",
  "tags": ["Recording", "Streaming", "Open Source"]
}
```
*(এই ফাইল না থাকলেও সমস্যা নেই — ব্রাঞ্চের নাম অনুযায়ী সাইট নিজে থেকেই সুন্দর ফরম্যাট করে নেবে!)*

---

## 🛠️ GitHub Pages চালু করার নিয়ম

1. যান: [https://github.com/rayhanalshorif133/PC-Software/settings/pages](https://github.com/rayhanalshorif133/PC-Software/settings/pages)
2. **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: **`main`** (অথবা `gh-pages`), Folder: **`/ (root)`**
3. **Save** ক্লিক করুন।
4. ওয়েবসাইট লাইভ হবে: **`https://rayhanalshorif133.github.io/PC-Software/`**
