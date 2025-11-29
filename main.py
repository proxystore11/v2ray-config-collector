#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRX11 – Ultimate Async Collector
ویژگی‌ها:
- تشخیص کشور واقعی بر اساس ایران (iplocation.ir)
- پینگ واقعی بر اساس ایران (jumpapi.ir + ping.ir)
- تشخیص کشور از روی hostname
- سازگار با GitHub Actions
- بدون Web UI
- پردازش کامل VMess / VLESS / Trojan / SS
"""

import asyncio
import aiohttp
import base64
import json
import yaml
import re
import os
import socket
import hashlib
import gzip
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


# ===================================================================
# Default Config
# ===================================================================

DEFAULT_CONFIG = {
    "project": {"name": "PRX11", "version": "8.0.0"},
    "settings": {
        "max_configs": 200,
        "timeout": 20,
        "ping_timeout": 5,
        "max_workers": 50
    },
    "remark": {"project_name": "PRX11"},
    "subscription_files": {
        "all": "PRX11-ALL.txt",
        "vmess": "PRX11-VMESS.txt",
        "vless": "PRX11-VLESS.txt",
        "shadowsocks": "PRX11-SS.txt",
        "trojan": "PRX11-TROJAN.txt",
        "working": "PRX11-WORKING.txt",
        "all_b64": "PRX11-ALL.b64.txt",
        "all_gzip_b64": "PRX11-ALL.gz.b64.txt",
    },
}

# Hidden + Extra Sources
HIDDEN_SOURCES = [
    "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA==",
]

# منبع VMess که خودت دادی
EXTRA_SOURCES = [
    "https://raw.githubusercontent.com/coldwater-10/V2rayCollector/main/vmess_iran.txt",
]

# Hostname Country detection
COUNTRY_KEYWORDS = {
    "de": "DE", "ger": "DE", "germany": "DE",
    "nl": "NL", "nld": "NL", "netherlands": "NL",
    "fr": "FR", "france": "FR",
    "ru": "RU", "rus": "RU", "russia": "RU",
    "ir": "IR", "irn": "IR", "iran": "IR",
    "us": "US", "usa": "US", "america": "US",
    "uk": "GB", "gb": "GB", "england": "GB",
    "ca": "CA", "can": "CA", "canada": "CA",
}


# ===================================================================
# Config Loader
# ===================================================================

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
    except:
        return DEFAULT_CONFIG


def ensure_dirs():
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)


# ===================================================================
# Base64 Utilities
# ===================================================================

def normalize_b64(data: str) -> bytes:
    missing = (-len(data)) % 4
    if missing:
        data += "=" * missing
    return base64.b64decode(data)


def decode_b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


# ===================================================================
# Config Extractor
# ===================================================================

def extract_configs(text: str) -> List[Dict[str, str]]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }

    out = []
    for typ, pat in patterns.items():
        matches = re.findall(pat, text)
        for m in matches:
            out.append({
                "raw": m,
                "type": typ,
                "hash": hashlib.md5(m.encode("utf-8")).hexdigest()
            })

    return out


def dedupe(arr: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for c in arr:
        if c["hash"] not in seen:
            seen.add(c["hash"])
            out.append(c)
    return out


# ===================================================================
# PING From IR (Iran Based Ping API)
# ===================================================================

async def ping_ir(host: str, session: aiohttp.ClientSession) -> Optional[float]:
    if not host or host == "unknown":
        return None

    # اول domain → IP
    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            ip = socket.gethostbyname(host)
        else:
            ip = host
    except:
        ip = host

    # بهترین API ایرانی:
    url = f"https://api.jumpapi.ir/ping/{ip}"
    try:
        async with session.get(url, timeout=4) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "ping" in data:
                    return float(data["ping"])
    except:
        pass

    # fallback ایرانی
    url2 = f"https://api.ping.ir/ping/{ip}"
    try:
        async with session.get(url2, timeout=4) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "ping" in data:
                    return float(data["ping"])
    except:
        pass

    return None


# ===================================================================
# GeoIP (Iran based)
# ===================================================================

async def geoip_ir(host: str, session: aiohttp.ClientSession) -> Optional[Tuple[str, str]]:
    """جستجوی کشور از سرویس iplocation.ir (از دید ایران – دقیق‌ترین)."""

    if not host:
        return None

    # domain → IP
    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            ip = socket.gethostbyname(host)
        else:
            ip = host
    except:
        return None

    url = f"https://iplocation.ir/{ip}"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            cc = data.get("country_code", "").upper()
            cn = data.get("country", "").strip()

            if cc:
                return cc, cn or cc

            return None
    except:
        return None


def detect_country_from_hostname(host: str) -> Optional[str]:
    host = host.lower()
    prefix = host.split(".")[0]
    if prefix in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[prefix]

    for key, cc in COUNTRY_KEYWORDS.items():
        if key in host:
            return cc

    tld = host.split(".")[-1]
    if tld in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[tld]

    return None


async def detect_country(host: str, session: aiohttp.ClientSession) -> Tuple[str, str]:
    """سیستم سه مرحله‌ای:  
    1) GeoIP ایران  
    2) Hostname Detection  
    3) fallback → US
    """

    # مرحله ۱: سرویس ایرانی
    geo = await geoip_ir(host, session)
    if geo:
        return geo[0], geo[1]

    # مرحله ۲: hostname detection
    cc = detect_country_from_hostname(host)
    if cc:
        return cc, cc

    # مرحله ۳:
    return "US", "Unknown"


# ===================================================================
# Extract host & port
# ===================================================================

def extract_server(cfg: Dict[str, str]) -> Tuple[str, int]:
    raw = cfg["raw"]
    typ = cfg["type"]

    try:
        if typ == "vmess":
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            return data.get("add", "unknown"), int(data.get("port", 443))

        m = re.search(r"@([^:#?]+)(?::(\d+))?", raw)
        if m:
            host = m.group(1)
            port = int(m.group(2)) if m.group(2) else 443
            return host, port

    except:
        pass

    return "unknown", 443


# ===================================================================
# Process config
# ===================================================================

async def process_config(cfg, index, country_counter, project, ping_timeout, session):
    host, port = extract_server(cfg)

    ping_task = asyncio.create_task(ping_ir(host, session))
    country_task = asyncio.create_task(detect_country(host, session))

    ping_value = await ping_task
    cc, cname = await country_task

    country_counter[cc] = country_counter.get(cc, 0) + 1
    num = country_counter[cc]

    ping_label = f"{int(ping_value)}ms" if ping_value else "❓ms"
    remark = f"{cname} | {num:02d} | {ping_label} | {project}"

    raw = cfg["raw"]
    typ = cfg["type"]

    # VMess rewrite
    if typ == "vmess":
        try:
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            data["ps"] = remark
            new_payload = base64.b64encode(json.dumps(data).encode()).decode().rstrip("=")
            final = "vmess://" + new_payload
        except:
            final = raw
    else:
        from urllib.parse import quote
        base = raw.split("#")[0]
        final = f"{base}#{quote(remark)}"

    status = "working" if ping_value and ping_value < 1000 else "unknown"

    return {
        "final": final,
        "protocol": typ,
        "country": cc,
        "remark": remark,
        "ping": ping_value,
        "status": status,
    }


# ===================================================================
# Collector
# ===================================================================

async def run_collector():
    cfg = load_config()
    ensure_dirs()

    timeout = cfg["settings"]["timeout"]
    ping_timeout = cfg["settings"]["ping_timeout"]
    max_configs = cfg["settings"]["max_configs"]

    sources = [decode_b64(s) for s in HIDDEN_SOURCES] + EXTRA_SOURCES

    all_configs = []
    print("📥 Collecting configs...")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:

        # جمع‌آوری از همه سورس‌ها
        for url in sources:
            try:
                async with session.get(url) as r:
                    if r.status == 200:
                        text = await r.text()
                        configs = extract_configs(text)
                        all_configs.extend(configs)
                        print(f"✔ Source OK: {url} ({len(configs)})")
                    else:
                        print(f"✖ Source Failed: {url} ({r.status})")
            except Exception as e:
                print(f"✖ Error: {url} → {e}")

        all_configs = dedupe(all_configs)
        print(f"✔ Total unique configs: {len(all_configs)}")

        subset = all_configs[:max_configs]
        print("⚙ Processing (GeoIP IR + Ping IR)...")

        country_counter = {}
        tasks = [
            process_config(
                c, i + 1, country_counter,
                cfg["remark"]["project_name"],
                ping_timeout, session
            )
            for i, c in enumerate(subset)
        ]

        results = await asyncio.gather(*tasks)

    # -----------------------------
    # Save outputs
    # -----------------------------
    print("💾 Saving subscription files...")

    subs = cfg["subscription_files"]

    def save(name, text):
        with open(f"output/subscriptions/{name}", "w", encoding="utf-8") as f:
            f.write(text)

    all_urls = [r["final"] for r in results]
    vmess = [r["final"] for r in results if r["protocol"] == "vmess"]
    vless = [r["final"] for r in results if r["protocol"] == "vless"]
    trojan = [r["final"] for r in results if r["protocol"] == "trojan"]
    ss = [r["final"] for r in results if r["protocol"] == "ss"]
    working = [r["final"] for r in results if r["status"] == "working"]

    save(subs["all"], "\n".join(all_urls))
    save(subs["vmess"], "\n".join(vmess))
    save(subs["vless"], "\n".join(vless))
    save(subs["shadowsocks"], "\n".join(ss))
    save(subs["trojan"], "\n".join(trojan))
    save(subs["working"], "\n".join(working))

    # Base64
    save(subs["all_b64"], base64.b64encode("\n".join(all_urls).encode()).decode())

    # Gzip + B64
    gz = gzip.compress("\n".join(all_urls).encode())
    save(subs["all_gzip_b64"], base64.b64encode(gz).decode())

    # Summary
    summary = {
        "last_update": datetime.utcnow().isoformat(),
        "total_configs": len(results),
        "working": len(working),
    }

    with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("✔ Done.")


# ===================================================================
# MAIN
# ===================================================================

def main():
    asyncio.run(run_collector())


if __name__ == "__main__":
    main()
