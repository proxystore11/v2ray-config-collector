import asyncio
import aiohttp
import base64
import json
import yaml
import re
import os
import hashlib
import gzip
import random
from datetime import datetime
from typing import Dict, Any, List
from zoneinfo import ZoneInfo  # برای ساعت ایران


# ======================================================
# تنظیمات پیش‌فرض
# ======================================================
DEFAULT_CONFIG = {
    "project": {"name": "PRX11", "version": "9.1.0"},
    "settings": {
        "max_configs": 500,
        "timeout": 20,
        "max_workers": 50,
    },
    "remark": {"project_name": "PRX11"},
    "subscription_files": {
        "all": "PRX11-ALL.txt",
        "vmess": "PRX11-VMESS.txt",
        "vless": "PRX11-VLESS.txt",
        "shadowsocks": "PRX11-SS.txt",
        "trojan": "PRX11-TROJAN.txt",
        # عمداً working / all_b64 / all_gzip_b64 وجود ندارند (ساخته نمی‌شوند)
    },
}

# ======================================================
# منابع مخفی (Base64)
# (فقط منابع جدید که خودت دادی)
# ======================================================
HIDDEN_SOURCES = [
    # https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vless.txt
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZsZXNzLnR4dA==",
    # https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vmess.txt
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZtZXNzLnR4dA==",
    # https://raw.githubusercontent.com/GFW-knocker/gfw_resist_HTTPS_proxy/refs/heads/main/multiple_config.json
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0dGVy1rbm9ja2VyL2dmd19yZXNpc3RfSFRUUFNfcHJveHkvcmVmcy9oZWFkcy9tYWluL211bHRpcGxlX2NvbmZpZy5qc29u",
    # https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/ss.txt
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3NzLnR4dA==",
    # https://raw.githubusercontent.com/ircfspace/warpsub/main/export/warp
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lyY2ZzcGFjZS93YXJwc3ViL21haW4vZXhwb3J0L3dhcnA=",
]


# ======================================================
# کمک‌کننده‌ها
# ======================================================
def load_config() -> Dict[str, Any]:
    if not os.path.exists("config.yaml"):
        return DEFAULT_CONFIG
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = DEFAULT_CONFIG.copy()
        for k, v in user_cfg.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        return cfg
    except Exception:
        return DEFAULT_CONFIG


def ensure_dirs():
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)
    os.makedirs("output", exist_ok=True)


def decode_b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


def normalize_b64(data: str) -> bytes:
    missing = (-len(data)) % 4
    if missing:
        data += "=" * missing
    return base64.b64decode(data)


# ======================================================
# استخراج کانفیگ‌ها
# ======================================================
def extract_configs(text: str) -> List[Dict[str, str]]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }
    out: List[Dict[str, str]] = []
    for typ, pat in patterns.items():
        matches = re.findall(pat, text)
        for m in matches:
            out.append(
                {
                    "raw": m,
                    "type": typ,
                    "hash": hashlib.md5(m.encode("utf-8")).hexdigest(),
                }
            )
    return out


def dedupe(arr: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for c in arr:
        if c["hash"] not in seen:
            seen.add(c["hash"])
            out.append(c)
    return out


# ======================================================
# ریمارک پیشرفته با ایموجی رندوم
# الگو: 🚀join@proxystore11 | freeconfig😍 | PRX11 #xxx
# ======================================================
EMOJI_POOL = [
    "🚀", "🔥", "⚡", "🌐", "⭐", "💎", "✨",
    "🎯", "🎉", "🛰️", "💥", "😎", "😍", "🤩", "🎈",
]


def build_remark(index: int, proto: str, project: str) -> str:
    start_emoji = random.choice(EMOJI_POOL)
    end_emoji = random.choice(EMOJI_POOL)
    # متن وسط ثابت، ایموجی ها رندوم
    return f"{start_emoji}join@proxystore11 | freeconfig{end_emoji} | {project} #{index:03d}"


# ======================================================
# پردازش کانفیگ
# ======================================================
async def process_config(cfg: Dict[str, str], index: int, project: str) -> Dict[str, Any]:
    raw = cfg["raw"]
    typ = cfg["type"]
    remark = build_remark(index, typ, project)

    if typ == "vmess":
        # vmess://base64(JSON)
        try:
            payload = raw[len("vmess://") :]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            data["ps"] = remark
            new_payload = base64.b64encode(
                json.dumps(data, ensure_ascii=False).encode("utf-8")
            ).decode("utf-8")
            new_payload = new_payload.rstrip("=")
            final_url = "vmess://" + new_payload
        except Exception:
            final_url = raw
    else:
        # vless / trojan / ss – اضافه کردن ریمارک بعد از #
        from urllib.parse import quote

        base = raw.split("#", 1)[0]
        final_url = f"{base}#{quote(remark)}"

    return {
        "final": final_url,
        "protocol": typ,
        "remark": remark,
    }


# ======================================================
# Collector اصلی
# ======================================================
async def run_collector() -> None:
    cfg = load_config()
    ensure_dirs()

    timeout = cfg["settings"]["timeout"]
    max_configs = cfg["settings"]["max_configs"]

    # decode منابع مخفی
    sources = [decode_b64(x) for x in HIDDEN_SOURCES]

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session:
        all_configs: List[Dict[str, str]] = []

        print("📥 دریافت کانفیگ‌ها از منابع مخفی...")

        for url in sources:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        # اگر JSON بود، سعی می‌کنیم متن را بخوانیم
                        content_type = resp.headers.get("Content-Type", "")
                        text = await resp.text()
                        # منبع JSON (مثلاً multiple_config.json) هم شامل لینک‌هاست
                        cfgs = extract_configs(text)
                        all_configs.extend(cfgs)
                        print(f"✔ {url} → {len(cfgs)} کانفیگ")
                    else:
                        print(f"✖ {url} → HTTP {resp.status}")
            except Exception as e:
                print(f"✖ خطا در خواندن {url}: {e}")

    all_configs = dedupe(all_configs)
    print(f"✔ تعداد کانفیگ یکتا: {len(all_configs)}")

    subset = all_configs[:max_configs]
    print("⚙ ساخت ریمارک و لینک‌های نهایی...")

    tasks = [
        process_config(c, i + 1, cfg["remark"]["project_name"])
        for i, c in enumerate(subset)
    ]
    results = await asyncio.gather(*tasks)

    # ======================================================
    # ذخیره فایل‌های خروجی
    # ======================================================
    subs = cfg["subscription_files"]

    def save_sub(name: str, lines: List[str]) -> None:
        path = os.path.join("output", "subscriptions", name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    all_urls = [r["final"] for r in results]
    vmess_urls = [r["final"] for r in results if r["protocol"] == "vmess"]
    vless_urls = [r["final"] for r in results if r["protocol"] == "vless"]
    trojan_urls = [r["final"] for r in results if r["protocol"] == "trojan"]
    ss_urls = [r["final"] for r in results if r["protocol"] == "ss"]

    save_sub(subs["all"], all_urls)
    save_sub(subs["vmess"], vmess_urls)
    save_sub(subs["vless"], vless_urls)
    save_sub(subs["shadowsocks"], ss_urls)
    save_sub(subs["trojan"], trojan_urls)

    # هیچ فایل working / all_b64 / all_gzip_b64 ساخته نمی‌شود

    # ======================================================
    # گزارش و زمان ایران
    # ======================================================
    tehran_tz = ZoneInfo("Asia/Tehran")
    now_ir = datetime.now(tehran_tz)
    timestamp_str = now_ir.strftime("%Y-%m-%d %H:%M:%S")

    summary = {
        "last_update": timestamp_str,
        "timezone": "Asia/Tehran",
        "total_configs": len(results),
        "project": cfg["project"],
    }

    summary_path = os.path.join("output", "configs", "PRX11_SUMMARY.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # فایل Auto Update در پوشه output
    auto_update_path = os.path.join("output", "AUTO_UPDATE.txt")
    with open(auto_update_path, "w", encoding="utf-8") as f:
        f.write(f"Auto Update: {timestamp_str}\n")

    print("✔ کار پایان یافت.")
    print(f"🕒 زمان آخرین به‌روزرسانی (ایران): {timestamp_str}")


# ======================================================
# MAIN
# ======================================================
def main():
    asyncio.run(run_collector())


if __name__ == "__main__":
    main()
