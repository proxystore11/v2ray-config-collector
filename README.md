# 🛡️ PRX11 V2Ray Config Collector - Advanced

<div align="center">

![Version](https://img.shields.io/badge/Version-4.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Auto Update](https://img.shields.io/badge/Auto_Update-6_Hours-orange)
![Ping Test](https://img.shields.io/badge/Ping_Test-Enabled-success)

**پروژه پیشرفته جمع‌آوری، فیلترسازی و تست کانفیگ‌های V2Ray**

</div>

## 📋 فهرست مطالب

- [✨ ویژگی‌ها](#-ویژگیها)
- [📁 لینک‌های اشتراک](#-لینکهای-اشتراک)
- [🛠️ راه‌اندازی](#️-راهاندازی)
- [📊 خروجی‌ها](#-خروجیها)
- [🤖 اتوماسیون](#-اتوماسیون)
- [🔧 پیکربندی](#-پیکربندی)
- [🐛 عیب‌یابی](#-عیبیابی)

## ✨ ویژگی‌ها

### 🎯 فیلترسازی پیشرفته
- **جداسازی بر اساس پروتکل** (VMess, VLess, Shadowsocks, Trojan)
- **تشخیص هوشمند کشور** با ۳ روش مختلف
- **تست پینگ اتوماتیک** برای شناسایی کانفیگ‌های کارکرده
- **فرمت‌بندی زیبا** با ایموجی و اطلاعات کامل

### 📊 لینک‌های ساب جداگانه
| فایل | توضیح |
|------|--------|
| `PRX11-ALL.txt` | تمام کانفیگ‌های جمع‌آوری شده |
| `PRX11-VMESS.txt` | فقط کانفیگ‌های VMess |
| `PRX11-VLESS.txt` | فقط کانفیگ‌های VLess |
| `PRX11-SS.txt` | فقط کانفیگ‌های Shadowsocks |
| `PRX11-TROJAN.txt` | فقط کانفیگ‌های Trojan |
| `PRX11-WORKING.txt` | فقط کانفیگ‌های کارکرده (تست پینگ موفق) |

### 🚀 عملکرد بهینه
- **پینگ همزمان** با ۱۰ thread
- **کش کردن نتایج** برای عملکرد بهتر
- **مدیریت خطا** پیشرفته
- **گزارش‌گیری دقیق** از آمار و نتایج

## 📁 لینک‌های اشتراک

### 🎯 لینک‌های اصلی
<div align="center">

| نوع | لینک مستقیم |
|-----|-------------|
| **همه کانفیگ‌ها** | [PRX11-ALL.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-ALL.txt) |
| **فقط VMess** | [PRX11-VMESS.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-VMESS.txt) |
| **فقط VLess** | [PRX11-VLESS.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-VLESS.txt) |
| **فقط Shadowsocks** | [PRX11-SS.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-SS.txt) |
| **فقط Trojan** | [PRX11-TROJAN.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-TROJAN.txt) |
| **کانفیگ‌های کارکرده** | [PRX11-WORKING.txt](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-WORKING.txt) |

</div>

## 🛠️ راه‌اندازی

### 📦 نصب و اجرای محلی
```bash
# 1. کلون کردن پروژه
git clone https://github.com/proxystore11/v2ray-config-collector.git
cd v2ray-config-collector

# 2. نصب dependencies
pip install -r requirements.txt

# 3. اجرای پروژه
python main.py
