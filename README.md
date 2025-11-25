# 🛡️ PRX11 V2Ray Config Collector

<div align="center">

![GitHub Actions](https://img.shields.io/badge/🔄-Auto%20Update%20Every%206%20Hours-blue)
![Python](https://img.shields.io/badge/🐍-Python%203.8%2B-green)
![Configs](https://img.shields.io/badge/🎯-Smart%20Country%20Detection-orange)
![Format](https://img.shields.io/badge/✨-Beautiful%20Formatting-purple)

**پروژه پیشرفته جمع‌آوری هوشمند کانفیگ‌های V2Ray با تشخیص کشور دقیق**

</div>

## ✨ ویژگی‌های منحصر به فرد

| ویژگی | توضیح |
|-------|--------|
| 🎯 **تشخیص هوشمند کشور** | تشخیص دقیق کشور با ۳ روش مختلف (TLD, API, Keywords) |
| 🏷️ **فرمت‌بندی زیبا** | ریمارک‌های زیبا با ایموجی: `🇺🇸 | آمریکا | 01 | PRX11` |
| 📊 **منابع طبقه‌بندی شده** | جدا کردن منابع بر اساس پروتکل (VMess, VLess, Shadowsocks, Trojan) |
| 🔄 **آپدیت خودکار** | اجرای خودکار هر ۶ ساعت در GitHub Actions |
| 📈 **آمار پیشرفته** | نمایش آمار زیبا از کشورها و پروتکل‌ها |
| 🚀 **عملکرد بهینه** | کش کردن و بهینه‌سازی برای سرعت بیشتر |

## 📥 لینک اشتراک

<div align="center">

### 🎯 فایل اشتراک اصلی PRX11
[**PRX11-FREE.txt**](https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-FREE.txt)

</div>

## 🏗️ ساختار منابع

| پروتکل | منابع |
|--------|--------|
| **VMess** | `freev2ray`, `ELiV2-RAY`, `vmess_iran` |
| **VLess** | `vless.html`, `mixed_iran` |
| **Shadowsocks** | `ss.html`, `mixarshia_ss` |
| **Trojan** | `v2ray-configs.txt` |

## 🛠️ راه‌اندازی محلی

```bash
# 1. کلون کردن پروژه
git clone https://github.com/proxystore11/v2ray-config-collector.git
cd v2ray-config-collector

# 2. نصب dependencies
pip install -r requirements.txt

# 3. اجرای پروژه
python main.py
