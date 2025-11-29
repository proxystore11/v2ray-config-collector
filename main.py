#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRX11 – Async Collector
نسخه جدید با:
- پینگ واقعی (Real Ping)
- تشخیص کشور Hybrid (Hostname + GeoIP)
- سازگار با GitHub Actions
- بدون Web UI
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


# -----------------------------
# Default config
# -----------------------------
DEFAULT_CONFIG = {
    "project": {
        "name": "PRX11",
        "version": "7.0.0",
    },
    "settings": {
        "max_configs": 200,
        "timeout": 30,
        "ping_timeout": 3,
        "max_workers": 50
    },
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

# Hidden Base64 Sources
HIDDEN_SOURCES = [
    "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA==",
]


# -----------------------------
# Country detection keywords
# -----------------------------
COUNTRY_KEYWORDS = {
    # Germany
    "de": "DE", "ger": "DE", "germany": "DE",
    # Netherlands
    "nl": "NL", "nld": "NL", "netherlands": "NL",
    # France
    "fr": "FR", "fra": "FR", "france": "FR",
    # Russia
    "ru": "RU", "rus": "RU", "russia": "RU",
    # Iran
    "ir": "IR", "irn": "IR", "iran": "IR",
    # United States
    "us": "US", "usa": "US", "america": "US",
    # United Kingdom
    "uk": "GB", "gb": "GB", "england": "GB",
    # Canada
    "ca": "CA", "can": "CA", "canada": "CA",
}


# -----------------------------
# Load config.yaml or default
# -----------------------------
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


# -----------------------------
# Helpers
# -----------------------------
def ensure_dirs():
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)


def decode_b64(x: str) -> str:
    return base64.b64decode(x).decode("utf-8")


def normalize_b64(text: str) -> bytes:
    pad = (-len(text)) % 4
    if pad:
        text += "=" * pad
    return base64.b64decode(text)


# -----------------------------
# Extract raw configs from text
# -----------------------------
def extract_configs(text: str) -> List[Dict]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }

    result = []
    for typ, pat in patterns.items():
        matches = re.findall(pat, text)
        for m in matches:
            h = hashlib.md5(m.encode("utf-8")).hexdigest()
            result.append({"raw": m, "type": typ, "hash": h})
    return result


def dedupe(arr: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for x in arr:
        if x["hash"] not in seen:
            seen.add(x["hash"])
            out.append(x)
    return out


# -----------------------------
# REAL PING using system ping
# -----------------------------
async def real_ping(host: str, timeout=3) -> Optional[float]:
    if not host or host.lower() == "unknown":
        return None

    # DNS
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
    except:
        return None


# -----------------------------
# GEOIP using ip-api.com
# -----------------------------
async def geoip(ip: str) -> Optional[Dict]:
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
            async with session.get(url, timeout=5) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                if data.get("status") != "success":
                    return None
                return data
    except:
        return None


# -----------------------------
# Hostname country detection
# -----------------------------
def detect_country_by_hostname(host: str) -> Optional[str]:
    if not host:
        return None

    host = host.lower().strip()

    # 1) prefix detection: de-cdn.xxx
    prefix = host.split(".")[0]
    if prefix in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[prefix]

    # 2) substring detection
    for key, cc in COUNTRY_KEYWORDS.items():
        if key in host:
            return cc

    # 3) TLD detection
    tld = host.split(".")[-1]
    if tld in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[tld]

    return None


# -----------------------------
# Hybrid country detection
# -----------------------------
async def detect_country(host: str) -> Tuple[str, str]:
    """
    خروجی:
    (country_code, country_name)
    """

    # 1) Hostname detection
    cc = detect_country_by_hostname(host)
    if cc:
        return cc, cc

    # 2) GeoIP detection
    g = await geoip(host)
    if g:
        return g.get("countryCode", "US"), g.get("country", "Unknown")

    # 3) fallback
    return "US", "Unknown"


# -----------------------------
# Extract server address
# -----------------------------
def extract_server(cfg: Dict) -> str:
    raw = cfg["raw"]
    typ = cfg["type"]

    try:
        if typ == "vmess":
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            return data.get("add", "unknown")

        # vless / trojan / ss
        if "@" in raw:
            m = re.search(r"@([^:#?]+)", raw)
            if m:
                return m.group(1)
    except:
        pass

    return "unknown"


# -----------------------------
# Process Config (main logic)
# -----------------------------
async def process_config(cfg, index, country_count, project_name):
    server = extract_server(cfg)

    # Real ping
    ping_value = await real_ping(server)

    # Country detection
    cc, cname = await detect_country(server)

    # Track count of each country
    country_count[cc] = country_count.get(cc, 0) + 1
    num = country_count[cc]

    # Build remark
    ping_str = f"{int(ping_value)}ms" if ping_value else "❓ms"
    remark = f"{cname} | {num:02d} | {ping_str} | {project_name}"

    # Build final URL
    raw = cfg["raw"]
    typ = cfg["type"]

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
        from urllib.parse import quote
        if "#" in raw:
            base = raw.split("#")[0]
            final = f"{base}#{quote(remark)}"
        else:
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


# -----------------------------
# Collector logic
# -----------------------------
async def run_collector():
    cfg = load_config()
    ensure_dirs()

    # Decode hidden sources
    sources = [decode_b64(x) for x in HIDDEN_SOURCES]

    print("📥 Collecting configs...")
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
                        print(f"✖ Source failed: {url}")
            except:
                print(f"✖ Error loading: {url}")

    all_configs = dedupe(all_configs)
    print(f"✔ Total unique configs: {len(all_configs)}")

    subset = all_configs[: cfg["settings"]["max_configs"]]

    print("⚙ Processing with REAL PING + Hybrid Country Detection...")
    country_count = {}

    tasks = [
        process_config(c, i + 1, country_count, cfg["remark"]["project_name"])
        for i, c in enumerate(subset)
    ]

    results = await asyncio.gather(*tasks)

    # Save subscription outputs
    print("💾 Saving subscription files...")

    def save(name, lines):
        with open(f"output/subscriptions/{name}", "w", encoding="utf-8") as f:
            if isinstance(lines, list):
                f.write("\n".join(lines))
            else:
                f.write(lines)

    scfg = cfg["subscription_files"]

    vmess = [r["final"] for r in results if r["protocol"] == "vmess"]
    vless = [r["final"] for r in results if r["protocol"] == "vless"]
    trojan = [r["final"] for r in results if r["protocol"] == "trojan"]
    ss = [r["final"] for r in results if r["protocol"] == "ss"]
    working = [r["final"] for r in results if r["status"] == "working"]
    all_out = [r["final"] for r in results]

    save(scfg["all"], all_out)
    save(scfg["vmess"], vmess)
    save(scfg["vless"], vless)
    save(scfg["shadowsocks"], ss)
    save(scfg["trojan"], trojan)
    save(scfg["working"], working)

    # Base64 output
    b64_text = base64.b64encode("\n".join(all_out).encode()).decode()
    save(scfg["all_b64"], [b64_text])

    # Gzip + Base64
    gz = gzip.compress("\n".join(all_out).encode())
    gz_b64 = base64.b64encode(gz).decode()
    save(scfg["all_gzip_b64"], [gz_b64])

    # Generate summary
    summary = {
        "last_update": datetime.now().isoformat(),
        "total_configs": len(results),
        "working": len(working),
    }

    with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("✔ Completed.")


# -----------------------------
# MAIN
# -----------------------------
def main():
    asyncio.run(run_collector())


if __name__ == "__main__":
    main()
