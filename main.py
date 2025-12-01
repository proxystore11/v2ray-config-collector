import asyncio
import aiohttp
import base64
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from urllib.parse import unquote, urlparse


# ======================== تنظیمات Enterprise ========================

OUTPUT_DIR = "output/subscriptions/"
REPORT_FILE = "output/PRX11-REPORT.json"
AUTO_UPDATE_FILE = "output/AUTO_UPDATE.txt"

SOURCES = {
    "vless": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vless.txt"
    ],
    "vmess": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vmess.txt"
    ],
    "trojan": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/trojan.txt"
    ],
    "ss": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/ss.txt"
    ],
    "frag": [
        "https://raw.githubusercontent.com/hiddify/hiddify-app/refs/heads/main/test.configs/fragment"
    ],
}

# GeoIP/Latency را در صورت نیاز فعال/غیرفعال کن
ENABLE_GEOIP = True
ENABLE_LATENCY = True

# حداکثر تعداد کانفیگ برای Enrich (برای جلوگیری از فشار به APIها)
MAX_ENRICH_GEOIP = 400
MAX_ENRICH_LATENCY = 250

# تنظیمات GeoIP (با سرویس رایگان ip-api.com)
GEOIP_URL = "http://ip-api.com/json/{host}?fields=status,country,countryCode"


# ======================== مدل داده کانفیگ ========================

@dataclass
class ConfigEntry:
    proto: str
    raw: str
    identity: str
    host: Optional[str] = None
    port: Optional[int] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latency_ms: Optional[float] = None


# ======================== ابزارهای کمکی ========================

def parse_host_port_from_url(url: str):
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port
        return host, port
    except Exception:
        return None, None


def parse_vless(line: str) -> ConfigEntry:
    identity = ""
    host = None
    port = None
    try:
        no_scheme = line.split("://", 1)[1]
        userinfo, rest = no_scheme.split("@", 1)
        identity = userinfo.split(":", 1)[0]
        hp = rest.split("?", 1)[0]
        if ":" in hp:
            host, p = hp.rsplit(":", 1)
            port = int(p)
        else:
            host = hp
    except Exception:
        pass
    return ConfigEntry(proto="vless", raw=line, identity=identity or line, host=host, port=port)


def parse_vmess(line: str) -> ConfigEntry:
    identity = ""
    host = None
    port = None
    try:
        b64 = line.split("://", 1)[1].strip()
        pad = len(b64) % 4
        if pad:
            b64 += "=" * (4 - pad)
        decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
        obj = json.loads(decoded)
        identity = (obj.get("id") or obj.get("uuid") or "").strip()
        host = (obj.get("host") or obj.get("add") or "").strip() or None
        p = obj.get("port")
        if isinstance(p, str):
            try:
                port = int(p)
            except Exception:
                port = None
        elif isinstance(p, int):
            port = p
    except Exception:
        pass
    return ConfigEntry(proto="vmess", raw=line, identity=identity or line, host=host, port=port)


def parse_trojan(line: str) -> ConfigEntry:
    identity = ""
    host = None
    port = None
    try:
        no_scheme = line.split("://", 1)[1]
        userinfo, rest = no_scheme.split("@", 1)
        identity = userinfo.strip()
        hp = rest.split("?", 1)[0]
        if ":" in hp:
            host, p = hp.rsplit(":", 1)
            port = int(p)
        else:
            host = hp
    except Exception:
        pass
    return ConfigEntry(proto="trojan", raw=line, identity=identity or line, host=host, port=port)


def parse_ss(line: str) -> ConfigEntry:
    identity = ""
    host = None
    port = None
    try:
        no_scheme = line.split("://", 1)[1]
        tmp = no_scheme.split("#", 1)[0].split("?", 1)[0]
        if "@" in tmp:
            userinfo, hp = tmp.split("@", 1)
            identity = unquote(userinfo)
            if ":" in hp:
                host, p = hp.rsplit(":", 1)
                port = int(p)
            else:
                host = hp
        else:
            identity = unquote(tmp)
    except Exception:
        pass
    return ConfigEntry(proto="ss", raw=line, identity=identity or line, host=host, port=port)


def parse_frag(line: str) -> ConfigEntry:
    return ConfigEntry(proto="frag", raw=line, identity=line)


def parse_config(proto: str, line: str) -> Optional[ConfigEntry]:
    l = line.strip().lower()
    if not l:
        return None
    if proto == "vless" or l.startswith("vless://"):
        return parse_vless(line.strip())
    if proto == "vmess" or l.startswith("vmess://"):
        return parse_vmess(line.strip())
    if proto == "trojan" or l.startswith("trojan://"):
        return parse_trojan(line.strip())
    if proto == "ss" or l.startswith("ss://"):
        return parse_ss(line.strip())
    if proto == "frag":
        return parse_frag(line.strip())
    return ConfigEntry(proto=proto, raw=line.strip(), identity=line.strip())


FAKE_PATTERNS = [
    r"free.*vpn",
    r"fake",
    r"test",
    r"example",
    r"temp",
    r"speedtest",
    r"xxxx",
]

def is_fake(entry: ConfigEntry) -> bool:
    txt = entry.raw.lower()
    for p in FAKE_PATTERNS:
        if re.search(p, txt):
            return True
    return False


def dedupe_entries(entries: list[ConfigEntry]) -> list[ConfigEntry]:
    seen = set()
    out: list[ConfigEntry] = []
    for e in entries:
        key = f"{e.proto}|{e.identity}"
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def sort_entries(entries: list[ConfigEntry]) -> list[ConfigEntry]:
    return sorted(
        entries,
        key=lambda e: (
            e.country_code or "ZZ",
            e.latency_ms if e.latency_ms is not None else 999999,
            e.identity,
            len(e.raw),
        ),
    )


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)


def write_file(path: str, lines: list[str], header: Optional[str] = None):
    with open(path, "w", encoding="utf-8") as f:
        if header:
            f.write(header.strip() + "\n")
        f.write("\n".join(lines))


# ======================== GeoIP و Latency ========================

async def geoip_lookup(host: str, session: aiohttp.ClientSession) -> tuple[Optional[str], Optional[str]]:
    if not host:
        return None, None
    try:
        url = GEOIP_URL.format(host=host)
        async with session.get(url, timeout=5) as r:
            data = await r.json(content_type=None)
            if data.get("status") == "success":
                country = data.get("country")
                cc = data.get("countryCode")
                return country, cc
    except Exception:
        pass
    return None, None


async def measure_latency(entry: ConfigEntry, session: aiohttp.ClientSession) -> Optional[float]:
    if not entry.host:
        return None
    port = entry.port or 443
    scheme = "https" if port == 443 else "http"
    url = f"{scheme}://{entry.host}"
    start = time.monotonic()
    try:
        async with session.get(url, timeout=3) as r:
            await r.read()
        elapsed = time.monotonic() - start
        return round(elapsed * 1000, 1)
    except Exception:
        return None


async def enrich_entries(entries: list[ConfigEntry], session: aiohttp.ClientSession):
    geo_targets = [e for e in entries if e.host][:MAX_ENRICH_GEOIP] if ENABLE_GEOIP else []
    lat_targets = [e for e in entries if e.host][:MAX_ENRICH_LATENCY] if ENABLE_LATENCY else []

    sem_geo = asyncio.Semaphore(20)
    sem_lat = asyncio.Semaphore(30)

    async def _geo_task(e: ConfigEntry):
        async with sem_geo:
            country, cc = await geoip_lookup(e.host, session)
            if country:
                e.country = country
            if cc:
                e.country_code = cc

    async def _lat_task(e: ConfigEntry):
        async with sem_lat:
            ms = await measure_latency(e, session)
            if ms is not None:
                e.latency_ms = ms

    tasks = []
    for e in geo_targets:
        tasks.append(asyncio.create_task(_geo_task(e)))
    for e in lat_targets:
        tasks.append(asyncio.create_task(_lat_task(e)))

    if tasks:
        await asyncio.gather(*tasks)


# ======================== دانلود موازی منابع ========================

async def fetch_url(url: str, session: aiohttp.ClientSession) -> list[str]:
    try:
        async with session.get(url, timeout=25) as r:
            text = await r.text()
            return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        return []


async def fetch_all_sources() -> dict[str, list[str]]:
    async with aiohttp.ClientSession() as session:
        tasks = []
        for proto, urls in SOURCES.items():
            for u in urls:
                tasks.append((proto, asyncio.create_task(fetch_url(u, session))))

        raw_results: dict[str, list[str]] = {k: [] for k in SOURCES.keys()}

        for proto, task in tasks:
            try:
                data = await task
                raw_results[proto].extend(data)
            except Exception:
                pass

        # حذف هدرهای fragment (#profile-...) → فقط direct/xdirect
        if "frag" in raw_results:
            raw_results["frag"] = [
                l for l in raw_results["frag"]
                if not l.strip().startswith("#")
            ]

        # Enrich بعد از ساخته شدن Session کلی
        all_entries: list[ConfigEntry] = []

        for proto, lines in raw_results.items():
            for line in lines:
                e = parse_config(proto, line)
                if not e:
                    continue
                if proto != "frag" and is_fake(e):
                    continue
                all_entries.append(e)

        # Dedup کلی
        all_entries = dedupe_entries(all_entries)

        # Enrich GeoIP & Latency
        await enrich_entries(all_entries, session)

        # گروه‌بندی دوباره بر اساس پروتکل
        grouped: dict[str, list[ConfigEntry]] = {k: [] for k in SOURCES.keys()}
        for e in all_entries:
            grouped.setdefault(e.proto, []).append(e)

        # Sort در هر پروتکل
        for k in grouped.keys():
            grouped[k] = sort_entries(grouped[k])

        return grouped


# ======================== هدر Hiddify ========================

HIDDIFY_HEADER = """#profile-title: base64:8J+UpSBGcmFnbWVudCDwn5Sl
#profile-update-interval: 24
#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531
#support-url: https://t.me/proxystore11
#profile-web-page-url: https://proxystore11.news
#connection-test-url: https://instagram.com
#remote-dns-address: https://sky.rethinkdns.com/dns-query
"""


# ======================== اجرای اصلی ========================

async def run():
    ensure_dirs()

    grouped = await fetch_all_sources()

    vless_entries = grouped.get("vless", [])
    vmess_entries = grouped.get("vmess", [])
    trojan_entries = grouped.get("trojan", [])
    ss_entries = grouped.get("ss", [])
    frag_entries = grouped.get("frag", [])

    vless_lines = [e.raw for e in vless_entries]
    vmess_lines = [e.raw for e in vmess_entries]
    trojan_lines = [e.raw for e in trojan_entries]
    ss_lines = [e.raw for e in ss_entries]
    frag_lines = [e.raw for e in frag_entries]

    hiddify_lines = vless_lines[:100]
    insta_lines = frag_lines

    write_file(os.path.join(OUTPUT_DIR, "prx11-vless.txt"), vless_lines)
    write_file(os.path.join(OUTPUT_DIR, "prx11-vmess.txt"), vmess_lines)
    write_file(os.path.join(OUTPUT_DIR, "prx11-trojan.txt"), trojan_lines)
    write_file(os.path.join(OUTPUT_DIR, "prx11-ss.txt"), ss_lines)
    write_file(os.path.join(OUTPUT_DIR, "prx11-hiddify.txt"), hiddify_lines, HIDDIFY_HEADER)
    write_file(os.path.join(OUTPUT_DIR, "prx11-insta-youto.txt"), insta_lines, HIDDIFY_HEADER)

    all_entries = vless_entries + vmess_entries + trojan_entries + ss_entries
    all_entries = dedupe_entries(all_entries)
    all_lines = [e.raw for e in sort_entries(all_entries)]
    write_file(os.path.join(OUTPUT_DIR, "prx11-all.txt"), all_lines)

    iran_ts = datetime.utcnow().timestamp() + 3.5 * 3600
    iran_str = datetime.fromtimestamp(iran_ts).strftime("%Y-%m-%d %H:%M:%S")
    write_file(AUTO_UPDATE_FILE, [f"Auto Update: {iran_str}"])

    report = {
        "update_time_iran": iran_str,
        "counts": {
            "vless": len(vless_entries),
            "vmess": len(vmess_entries),
            "trojan": len(trojan_entries),
            "ss": len(ss_entries),
            "fragment": len(frag_entries),
            "all": len(all_entries),
        },
        "geoip_enabled": ENABLE_GEOIP,
        "latency_enabled": ENABLE_LATENCY,
        "sample_geo": [
            {
                "proto": e.proto,
                "identity": e.identity,
                "host": e.host,
                "country": e.country,
                "country_code": e.country_code,
                "latency_ms": e.latency_ms,
            }
            for e in all_entries[:50]
        ],
        "sources": SOURCES,
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
