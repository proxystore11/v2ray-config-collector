#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRX11 – Async Collector
نسخه جدید با:
- پینگ TCP واقعی (بدون نیاز به ping سیستم)
- تشخیص کشور Hybrid (GeoIP + Hostname)
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
    "project": {"name": "PRX11", "version": "7.0.0"},
    "settings": {
        "max_configs": 200,
        "timeout": 30,       # timeout برای دریافت سورس‌ها
        "ping_timeout": 3,   # timeout برای TCP ping
        "max_workers": 50,
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

# Hidden Base64 Sources (مثل قبل)
HIDDEN_SOURCES = [
    "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA==",
]

# منبع واضح VMess که ارسال کردی
EXTRA_SOURCES = [
    "https://raw.githubusercontent.com/coldwater-10/V2rayCollector/main/vmess_iran.txt",
]

# برای fallback تشخیص کشور از روی hostname
COUNTRY_KEYWORDS = {
    "de": "DE", "ger": "DE", "germany": "DE",
    "nl": "NL", "nld": "NL", "netherlands": "NL",
    "fr": "FR", "fra": "FR", "france": "FR",
    "ru": "RU", "rus": "RU", "russia": "RU",
    "ir": "IR", "irn": "IR", "iran": "IR",
    "us": "US", "usa": "US", "america": "US",
    "uk": "GB", "gb": "GB", "england": "GB",
    "ca": "CA", "can": "CA", "canada": "CA",
}


# -----------------------------
# Load config.yaml or defaults
# -----------------------------
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


def ensure_dirs() -> None:
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)


def decode_b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


def normalize_b64_payload(payload: str) -> bytes:
    payload = payload.strip()
    missing = (-len(payload)) % 4
    if missing:
        payload += "=" * missing
    return base64.b64decode(payload)


# -----------------------------
# Extract raw configs from text
# -----------------------------
def extract_configs(text: str) -> List[Dict[str, str]]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }
    out: List[Dict[str, str]] = []
    for typ, pat in patterns.items():
        for match in re.findall(pat, text):
            h = hashlib.md5(match.encode("utf-8")).hexdigest()
            out.append({"raw": match, "type": typ, "hash": h})
    return out


def dedupe(configs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out: List[Dict[str, str]] = []
    for c in configs:
        if c["hash"] not in seen:
            seen.add(c["hash"])
            out.append(c)
    return out


# -----------------------------
# TCP Ping (بهترین گزینه در GitHub Actions)
# -----------------------------
async def tcp_ping(host: str, port: Optional[int], timeout: int) -> Optional[float]:
    if not host or host.lower() == "unknown" or not port:
        return None

    try:
        # اگر دامنه بود، تبدیل به IP
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            host = socket.gethostbyname(host)
    except Exception:
        return None

    try:
        start = asyncio.get_event_loop().time()
        conn_coro = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn_coro, timeout=timeout)
        end = asyncio.get_event_loop().time()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return (end - start) * 1000.0
    except Exception:
        return None


# -----------------------------
# GEOIP via ip-api.com
# -----------------------------
async def geoip_lookup(host_or_ip: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
    if not host_or_ip:
        return None

    ip = host_or_ip
    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host_or_ip):
            ip = socket.gethostbyname(host_or_ip)
    except Exception:
        return None

    url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if data.get("status") != "success":
                return None
            return data
    except Exception:
        return None


def detect_country_from_hostname(host: str) -> Optional[str]:
    if not host:
        return None
    host = host.lower().strip()

    # 1) de-cdn.ultima.foundation -> prefix = de
    prefix = host.split(".")[0]
    if prefix in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[prefix]

    # 2) اگر اسم کشور در hostname بود
    for key, cc in COUNTRY_KEYWORDS.items():
        if key in host:
            return cc

    # 3) TLD
    tld = host.split(".")[-1]
    if tld in COUNTRY_KEYWORDS:
        return COUNTRY_KEYWORDS[tld]

    return None


async def detect_country(host: str, session: aiohttp.ClientSession) -> Tuple[str, str]:
    """
    اول GeoIP از ip-api.com
    اگر نشد → Hostname
    در نهایت fallback روی US
    """
    geo = await geoip_lookup(host, session)
    if geo:
        return geo.get("countryCode", "US"), geo.get("country", "Unknown")

    cc = detect_country_from_hostname(host)
    if cc:
        return cc, cc

    return "US", "Unknown"


# -----------------------------
# Extract host & port from config
# -----------------------------
def extract_server_and_port(cfg: Dict[str, str]) -> Tuple[str, Optional[int]]:
    raw = cfg["raw"]
    typ = cfg["type"]

    try:
        if typ == "vmess":
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64_payload(payload).decode("utf-8"))
            host = str(data.get("add", "unknown"))
            port = data.get("port")
            try:
                port = int(port)
            except Exception:
                port = 443
            return host, port

        # برای vless / trojan / ss
        m = re.search(r"@([^:#?]+)(?::(\d+))?", raw)
        if m:
            host = m.group(1)
            port_str = m.group(2)
            port = int(port_str) if port_str else 443
            return host, port

    except Exception:
        pass

    return "unknown", None


# -----------------------------
# Process a single config
# -----------------------------
async def process_config(
    cfg: Dict[str, str],
    index: int,
    country_counter: Dict[str, int],
    project_name: str,
    ping_timeout: int,
    session: aiohttp.ClientSession,
) -> Dict[str, Any]:
    host, port = extract_server_and_port(cfg)

    # TCP ping + Country detection به صورت موازی
    ping_task = asyncio.create_task(tcp_ping(host, port, ping_timeout))
    country_task = asyncio.create_task(detect_country(host, session))

    ping_value = await ping_task
    cc, cname = await country_task

    country_counter[cc] = country_counter.get(cc, 0) + 1
    num = country_counter[cc]

    ping_label = f"{int(ping_value)}ms" if ping_value is not None else "❓ms"
    remark = f"{cname} | {num:02d} | {ping_label} | {project_name}"

    raw = cfg["raw"]
    typ = cfg["type"]

    # بازنویسی VMess با ps جدید
    if typ == "vmess":
        try:
            payload = raw[len("vmess://"):]
            data = json.loads(normalize_b64_payload(payload).decode("utf-8"))
            data["ps"] = remark
            new_payload = base64.b64encode(
                json.dumps(data, ensure_ascii=False).encode("utf-8")
            ).decode("utf-8")
            new_payload = new_payload.rstrip("=")
            final_url = "vmess://" + new_payload
        except Exception:
            final_url = raw
    else:
        # VLESS / TROJAN / SS – فقط Tag بعد از # را عوض می‌کنیم
        from urllib.parse import quote
        if "#" in raw:
            base = raw.split("#", 1)[0]
            final_url = f"{base}#{quote(remark)}"
        else:
            final_url = f"{raw}#{quote(remark)}"

    status = "working" if ping_value is not None and ping_value < 1000 else "unknown"

    return {
        "final": final_url,
        "protocol": typ,
        "country": cc,
        "remark": remark,
        "ping": ping_value,
        "status": status,
    }


# -----------------------------
# Collector main logic
# -----------------------------
async def run_collector() -> None:
    cfg = load_config()
    ensure_dirs()

    timeout = int(cfg["settings"]["timeout"])
    ping_timeout = int(cfg["settings"]["ping_timeout"])
    max_configs = int(cfg["settings"]["max_configs"])

    sources = [decode_b64(s) for s in HIDDEN_SOURCES] + EXTRA_SOURCES

    all_configs: List[Dict[str, str]] = []
    print("📥 Collecting configs from sources...")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        # جمع‌آوری از همه سورس‌ها
        for url in sources:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        cfgs = extract_configs(text)
                        all_configs.extend(cfgs)
                        print(f"✔ Source OK: {url} ({len(cfgs)} configs)")
                    else:
                        print(f"✖ Source failed: {url} (HTTP {resp.status})")
            except Exception as e:
                print(f"✖ Error loading {url}: {e}")

        all_configs = dedupe(all_configs)
        print(f"✔ Total unique configs: {len(all_configs)}")

        subset = all_configs[:max_configs]
        print("⚙ Processing configs (TCP ping + GeoIP)...")

        country_counter: Dict[str, int] = {}
        tasks = [
            process_config(
                c,
                i + 1,
                country_counter,
                cfg["remark"]["project_name"],
                ping_timeout,
                session,
            )
            for i, c in enumerate(subset)
        ]
        results = await asyncio.gather(*tasks)

    # -----------------------------
    # Save subscription outputs
    # -----------------------------
    print("💾 Saving subscription files...")

    subs_cfg = cfg["subscription_files"]

    def save(name: str, content: str) -> None:
        path = os.path.join("output", "subscriptions", name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    all_urls = [r["final"] for r in results]
    vmess_urls = [r["final"] for r in results if r["protocol"] == "vmess"]
    vless_urls = [r["final"] for r in results if r["protocol"] == "vless"]
    trojan_urls = [r["final"] for r in results if r["protocol"] == "trojan"]
    ss_urls = [r["final"] for r in results if r["protocol"] == "ss"]
    working_urls = [r["final"] for r in results if r["status"] == "working"]

    save(subs_cfg["all"], "\n".join(all_urls))
    save(subs_cfg["vmess"], "\n".join(vmess_urls))
    save(subs_cfg["vless"], "\n".join(vless_urls))
    save(subs_cfg["shadowsocks"], "\n".join(ss_urls))
    save(subs_cfg["trojan"], "\n".join(trojan_urls))
    save(subs_cfg["working"], "\n".join(working_urls))

    # Base64
    b64_text = base64.b64encode("\n".join(all_urls).encode("utf-8")).decode("utf-8")
    save(subs_cfg["all_b64"], b64_text)

    # Gzip + Base64
    gz_bytes = gzip.compress("\n".join(all_urls).encode("utf-8"))
    gz_b64 = base64.b64encode(gz_bytes).decode("utf-8")
    save(subs_cfg["all_gzip_b64"], gz_b64)

    # Summary
    summary = {
        "last_update": datetime.now().isoformat(),
        "total_configs": len(results),
        "working": len(working_urls),
    }
    with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("✔ Done.")


# -----------------------------
# MAIN
# -----------------------------
def main() -> None:
    asyncio.run(run_collector())


if __name__ == "__main__":
    main()
