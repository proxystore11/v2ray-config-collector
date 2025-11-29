#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRX11 – Async Collector (GeoIP + Real Ping Edition)
نسخه بهینه‌شده برای GitHub Auto-Update
بدون Web UI – پینگ واقعی – تشخیص کشور دقیق
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
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


# -------------------------------
# تنظیمات پیش‌فرض
# -------------------------------

DEFAULT_CONFIG = {
    "project": {
        "name": "PRX11",
        "version": "6.0.0",
    },
    "settings": {
        "max_configs": 200,
        "timeout": 30,
        "ping_timeout": 3,
        "max_workers": 40
    },
    "countries": {},

    "remark": {
        "project_name": "PRX11"
    },

    "subscription_files": {
        "all": "PRX11-ALL.txt",
        "vmess": "PRX11-VMESS.txt",
        "vless": "PRX11-VLESS.txt",
        "shadowsocks": "PRX11-SS.txt",
        "trojan": "PRX11-TROJAN.txt",
        "working": "PRX11-WORKING.txt",
        "all_b64": "PRX11-ALL.b64.txt",
        "all_gzip_b64": "PRX11-ALL.gz.b64.txt",
    }
}

HIDDEN_SOURCES = [
    "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA==",
]


# -------------------------------
# Helper functions
# -------------------------------

def load_config() -> Dict[str, Any]:
    if not os.path.exists("config.yaml"):
        return DEFAULT_CONFIG

    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        merged = DEFAULT_CONFIG.copy()
        merged.update(cfg)
        return merged
    except:
        return DEFAULT_CONFIG


def ensure_dirs():
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)


def decode_b64_url(b64: str) -> str:
    return base64.b64decode(b64).decode("utf-8")


def extract_configs(text: str) -> List[Dict[str, str]]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }
    result = []
    for typ, pat in patterns.items():
        for match in re.findall(pat, text):
            h = hashlib.md5(match.encode()).hexdigest()
            result.append({"raw": match, "type": typ, "hash": h})
    return result


def dedupe(configs: List[Dict]) -> List[Dict]:
    seen = set()
    final = []
    for c in configs:
        if c["hash"] not in seen:
            final.append(c)
            seen.add(c["hash"])
    return final


def normalize_b64(payload: str) -> bytes:
    payload = payload.strip()
    pad = (-len(payload)) % 4
    if pad:
        payload += "=" * pad
    return base64.b64decode(payload)


# -------------------------------
# REAL PING (Exact Linux Ping)
# -------------------------------

async def real_ping(host: str, timeout=3) -> Optional[float]:
    """پینگ واقعی از سیستم (GitHub Actions)"""
    if not host or host.lower() == "unknown":
        return None

    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            host = socket.gethostbyname(host)
    except:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(timeout),
            host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        out = out.decode()

        m = re.search(r"time=([\d\.]+)\s*ms", out)
        if m:
            return float(m.group(1))
        return None

    except Exception:
        return None


# -------------------------------
# GEOIP – بهترین سرویس دنیا (ip-api)
# -------------------------------

async def geoip(ip: str) -> Optional[Dict]:
    """دقیق‌ترین سرویس تشخیص کشور"""
    if not ip:
        return None

    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            ip = socket.gethostbyname(ip)
    except:
        return None

    url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as res:
                if res.status != 200:
                    return None
                data = await res.json()
                if data.get("status") != "success":
                    return None
                return data
    except:
        return None


# -------------------------------
# Extract server for protocols
# -------------------------------

def extract_server_address(cfg: Dict) -> str:
    raw = cfg["raw"]
    typ = cfg["type"]

    try:
        if typ == "vmess":
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            return str(data.get("add", "unknown"))

        # Common for vless/trojan
        if "@" in raw:
            m = re.search(r"@([^:#?]+)", raw)
            if m:
                return m.group(1)

        return "unknown"

    except:
        return "unknown"


# -------------------------------
# Processor
# -------------------------------

async def process_config(cfg: Dict, index: int, country_count: Dict[str, int], project_name: str):
    server = extract_server_address(cfg)

    # 1) پینگ دقیق
    ping_value = await real_ping(server)

    # 2) تشخیص کشور دقیق
    g = await geoip(server)
    if g:
        cc = g.get("countryCode", "US")
        cname = g.get("country", "United States")
        flag = ""
    else:
        cc = "US"
        cname = "Unknown"
        flag = ""

    # شمارش کشور
    country_count[cc] = country_count.get(cc, 0) + 1
    num = country_count[cc]

    # ساخت Remark جدید
    ping_str = f"{int(ping_value)}ms" if ping_value else "❓ms"
    remark = f"{flag} {cname} | {num:02d} | {ping_str} | {project_name}"

    # ساخت لینک خروجی
    typ = cfg["type"]
    raw = cfg["raw"]

    if typ == "vmess":
        try:
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            data["ps"] = remark
            new_payload = base64.b64encode(json.dumps(data).encode()).decode()
            new_payload = new_payload.rstrip("=")
            final = f"vmess://{new_payload}"
        except:
            final = raw

    else:
        # برای vless/trojan/ss
        if "#" in raw:
            base = raw.split("#")[0]
            from urllib.parse import quote
            final = f"{base}#{quote(remark)}"
        else:
            from urllib.parse import quote
            final = f"{raw}#{quote(remark)}"

    status = "working" if ping_value and ping_value < 1000 else "unknown"

    return {
        "final": final,
        "protocol": typ,
        "country": cc,
        "remark": remark,
        "ping": ping_value,
        "status": status
    }


# -------------------------------
# Collector
# -------------------------------

async def run_collector():
    cfg = load_config()
    ensure_dirs()

    sources = [decode_b64_url(x) for x in HIDDEN_SOURCES]

    print("📥 Collecting configs from hidden sources...")

    all_configs = []

    async with aiohttp.ClientSession() as session:
        for url in sources:
            try:
                async with session.get(url, timeout=cfg["settings"]["timeout"]) as r:
                    if r.status == 200:
                        text = await r.text()
                        all_configs.extend(extract_configs(text))
                        print(f"✔ Source OK: {url}")
                    else:
                        print(f"✖ Source Failed: {url}")
            except:
                print(f"✖ Error loading: {url}")

    all_configs = dedupe(all_configs)
    print(f"✔ Total unique configs: {len(all_configs)}")

    subset = all_configs[: cfg["settings"]["max_configs"]]

    print("⚙ Processing with REAL ping + GeoIP ...")
    country_count = {}

    tasks = [
        process_config(
            c,
            i + 1,
            country_count,
            cfg["remark"]["project_name"]
        )
        for i, c in enumerate(subset)
    ]

    results = await asyncio.gather(*tasks)

    # ساخت فایل‌های Sub
    print("💾 Writing subscription files...")

    vmess = [r["final"] for r in results if r["protocol"] == "vmess"]
    vless = [r["final"] for r in results if r["protocol"] == "vless"]
    trojan = [r["final"] for r in results if r["protocol"] == "trojan"]
    ss = [r["final"] for r in results if r["protocol"] == "ss"]
    working = [r["final"] for r in results if r["status"] == "working"]
    all_out = [r["final"] for r in results]

    def save(name, lines):
        with open(f"output/subscriptions/{name}", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    scfg = cfg["subscription_files"]

    save(scfg["all"], all_out)
    save(scfg["vmess"], vmess)
    save(scfg["vless"], vless)
    save(scfg["shadowsocks"], ss)
    save(scfg["trojan"], trojan)
    save(scfg["working"], working)

    # Base64
    b64 = base64.b64encode("\n".join(all_out).encode()).decode()
    save(scfg["all_b64"], [b64])

    # Gzip + Base64
    import gzip
    gz = gzip.compress("\n".join(all_out).encode())
    gz_b64 = base64.b64encode(gz).decode()
    save(scfg["all_gzip_b64"], [gz_b64])

    # گزارش
    summary = {
        "last_update": datetime.now().isoformat(),
        "total_configs": len(results),
        "working": len(working),
    }

    with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("✔ Completed.")


# -------------------------------
# MAIN
# -------------------------------

def main():
    asyncio.run(run_collector())

if __name__ == "__main__":
    main()
