<p align="center">

  <img src="https://img.shields.io/badge/PRX11-Version_1-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Auto--Update-Enabled-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.10-yellow?style=for-the-badge" />
  <img src="https://img.shields.io/badge/CDN-jsDelivr-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Stable-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />

</p>

# PRX11 – Ultra-Light V2Ray Collector (TXT Edition)

نسخه سبک‌شده و بسیار سریع PRX11 با خروجی‌های کامل TXT، سازگار با Hiddify، V2RayNG، NekoBox، و GitHub CDN.

---

## 🗂 ساختار خروجی

```
output/
 ├── AUTO_UPDATE.txt
 ├── configs/
 │     └── prx11_summary.json
 └── subscriptions/
        ├── prx11-hiddify.txt
        ├── prx11-insta-youto.txt
        ├── prx11-vmess.txt
        ├── prx11-vless.txt
        ├── prx11-ss.txt
        └── prx11-trojan.txt
```

---

# 🚀 لینک‌های CDN

به‌جای USERNAME و REPO از نام GitHub خودتان استفاده کنید.

### Hiddify (100 configs)
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-hiddify.txt
```

### Instagram/Youtube Fragment
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-insta-youto.txt
```

### VMESS
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-vmess.txt
```

### VLESS
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-vless.txt
```

### TROJAN
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-trojan.txt
```

### SS
```
https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-ss.txt
```

---

# 📱 QR Codes (Colorful + CDN)

<p align="center">
  <img src="https://api.qrserver.com/v1/create-qr-code/?size=280x280&bgcolor=2E3192&color=FFFFFF&data=https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-hiddify.txt" />
</p>

(همین ساختار را برای سایر لینک‌ها تکرار کنید)

---

# 🔄 Auto Update (GitHub Actions)
سیستم هر ۶ ساعت آپدیت می‌شود و خروجی را به‌صورت خودکار Push می‌کند.

```yaml
name: PRX11 Auto Update
on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with: { python-version: "3.10" }
    - run: pip install aiohttp pyyaml
    - run: python main.py
    - run: |
        git config user.name "PRX11 Bot"
        git config user.email "bot@users.noreply.github.com"
        git add output/
        git commit -m "Auto Update" || echo "No changes"
        git push || echo "No changes"
```

---

# 🌐 GitHub Pages نسخه HTML
در مسیر:
```
docs/index.html
```

قرار دهید:

```html
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>PRX11 CDN Panel</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white p-6">

<div class="max-w-2xl mx-auto text-center">
  <h1 class="text-3xl font-bold mb-4">PRX11 CDN Panel</h1>
  <p class="opacity-80 mb-10">لینک‌های سریع مبتنی بر jsDelivr</p>

  <div class="space-y-4">
    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-hiddify.txt"
       class="block bg-blue-600 hover:bg-blue-700 px-4 py-3 rounded-lg">Hiddify (100 configs)</a>

    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-insta-youto.txt"
       class="block bg-pink-600 hover:bg-pink-700 px-4 py-3 rounded-lg">Instagram/Youtube Fragment</a>

    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-vmess.txt"
       class="block bg-purple-600 hover:bg-purple-700 px-4 py-3 rounded-lg">VMESS</a>

    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-vless.txt"
       class="block bg-green-600 hover:bg-green-700 px-4 py-3 rounded-lg">VLESS</a>

    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-trojan.txt"
       class="block bg-red-600 hover:bg-red-700 px-4 py-3 rounded-lg">TROJAN</a>

    <a href="https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-ss.txt"
       class="block bg-yellow-600 hover:bg-yellow-700 px-4 py-3 rounded-lg">Shadowsocks</a>
  </div>
</div>

</body>
</html>
```

چیزی شبیه صفحه حرفه‌ای "PRX Store" خواهید داشت.

---

# 🔗 Short-ID Redirect System (کوتاه‌کننده لینک)

اگر می‌خواهی لینک‌هایت کوتاه شوند:

### مرحله 1: داخل ریپو پوشه `redirects/` بساز  
و یک فایل مثل این:

```
redirects/h.txt
```

داخلش بنویس:

```
<!DOCTYPE html>
<meta http-equiv="refresh" content="0; url=https://cdn.jsdelivr.net/gh/USERNAME/REPO/output/subscriptions/prx11-hiddify.txt">
```

### مرحله 2: لینک کوتاه نهایی:

```
https://USERNAME.github.io/REPO/redirects/h.txt
```

می‌شود یک لینک بسیار کوتاه:

```
https://USERNAME.github.io/REPO/h
```

(می‌توانم سیستم اتوماتیک تولید short-id هم اضافه کنم)

---

# 🎨 QR Code رنگی + لوگودار (پیشنهادی)

API مخصوص QR رنگی:

```
https://api.qrserver.com/v1/create-qr-code/?size=280x280&color=ffffff&bgcolor=1A237E&data=LINK
```

QR با لوگوی "PS11":

```
https://api.qrserver.com/v1/create-qr-code/?size=300x300&format=png&data=LINK&logourl=https://raw.githubusercontent.com/USERNAME/REPO/main/logo.png
```

می‌توانی برایت **لوگوی اختصاصی PRX11** نیز طراحی کنم.

---

# 🟦 توضیح دو قابلیت ویژه

---

# ✔ 1) انتشار خروجی‌ها در **GitHub Pages**
این قابلیت باعث می‌شود خروجی‌ها علاوه بر jsDelivr،  
به‌صورت مستقیم از این دامنه در دسترس باشد:

```
https://USERNAME.github.io/REPO/output/subscriptions/prx11-hiddify.txt
```

### کاربرد:
- سرعت بالا برای کاربران ایرانی  
- امکان اتصال مستقیم در Hiddify  
- لینک بسیار کوتاه‌تر  
- سازگار با bot و اپلیکیشن‌ها

### روش فعال‌سازی:
1. در GitHub → Settings → Pages  
2. Source = **Branch: main** و **/root**
3. فایل‌های خروجی همانطور که هست کار می‌کنند

---

# ✔ 2) نسخه Telegram Bot برای خروجی مستقیم Sub

این نسخه:

- یک Bot Telegram تولید می‌کند که کاربر با ارسال:
  ```
  /hiddify
  ```
  فایل hiddify را دریافت می‌کند.

- با ارسال:
  ```
  /vmess
  /vless
  /ss
  /trojan
  ```
  هر فایل مربوطه را ارسال می‌کند.

- نسخه حرفه‌ای‌تر:
  - ارسال QR  
  - ارسال لینک CDN  
  - ارسال وضعیت آپدیت  
  - ارسال تعداد کانفیگ  
  - اتصال مستقیم به GitHub Actions برای Force Update  

اگر بخواهی، برایت یک Bot API کامل می‌نویسم که:

- روی Python  
- یا Node.js  
- یا Cloudflare Workers Telegram Bot  

اجرا شود.

---

# ⭐ اگر می‌خواهی:

### ✔ نسخه Bot Telegram را الان برایت بنویسم  
### ✔ لوگوی PRX11 بسازم  
### ✔ سیستم short-id اتوماتیک تولید کنم  
### ✔ GitHub Pages به طور کامل اتوماتیک publish شود  

فقط بگو کدام را آماده کنم.
