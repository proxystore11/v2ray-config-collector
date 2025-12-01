import asyncio
import aiohttp
import base64
import json
import os
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from urllib.parse import unquote

OUTPUT_DIR = "output/subscriptions"
REPORT_FILE = "output/PRX11-REPORT.json"
LOGGER_FILE = "output/PRX11-LOGGER.json"
AUTO_UPDATE_FILE = "output/AUTO_UPDATE.txt"

SOURCES: Dict[str, List[str]] = {
    "vless": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vless.txt",
    ],
    "vmess": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/vmess.txt",
    ],
    "trojan": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/trojan.txt",
    ],
    "ss": [
        "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/Protocols/ss.txt",
    ],
    "frag": [
        "https://raw.githubusercontent.com/hiddify/hiddify-app/refs/heads/main/test.configs/fragment",
    ],
}

ENABLE_GEOIP = True
ENABLE_LATENCY = True
MAX_ENRICH_GEOIP = 700
MAX_ENRICH_LATENCY = 500
GEOIP_URL = "http://ip-api.com/json/{host}?fields=status,country,countryCode"

COUNTRY_PRIORITY: Dict[str, int] = {
    "DE": 9,
    "FI": 9,
    "NL": 9,
    "SE": 8,
    "CH": 8,
    "AT": 7,
    "US": 7,
    "CA": 7,
    "FR": 6,
    "GB": 6,
    "SG": 6,
    "AU": 6,
    "": 0,
}


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
    quality_score: Optional[float] = None


def parse_vless(line: str) -> ConfigEntry:
    identity, host, port = None, None, None
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
    return ConfigEntry("vless", line, identity or line, host, port)


def parse_vmess(line: str) -> ConfigEntry:
    identity, host, port = None, None, None
    try:
        raw = line.split("://", 1)[1].strip()
        pad = len(raw) % 4
        if pad:
            raw += "=" * (4 - pad)
        decoded = base64.b64decode(raw).decode("utf-8", errors="ignore")
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
    return ConfigEntry("vmess", line, identity or line, host, port)


def parse_trojan(line: str) -> ConfigEntry:
    identity, host, port = None, None, None
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
    return ConfigEntry("trojan", line, identity or line, host, port)


def parse_ss(line: str) -> ConfigEntry:
    identity, host, port = None, None, None
    try:
        body = line.split("://", 1)[1]
        tmp = body.split("#", 1)[0].split("?", 1)[0]
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
    return ConfigEntry("ss", line, identity or line, host, port)


def parse_frag(line: str) -> ConfigEntry:
    return ConfigEntry("frag", line, line)


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
    return ConfigEntry(proto, line.strip(), line.strip())


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


def dedupe_entries(entries: List[ConfigEntry]) -> List[ConfigEntry]:
    seen = set()
    out: List[ConfigEntry] = []
    for e in entries:
        key = f"{e.proto}|{e.identity}"
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def ensure_dirs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)


async def geoip_lookup(host: str, session: aiohttp.ClientSession) -> Tuple[Optional[str], Optional[str]]:
    if not host:
        return None, None
    try:
        async with session.get(GEOIP_URL.format(host=host), timeout=5) as r:
            data = await r.json(content_type=None)
            if data.get("status") == "success":
                return data.get("country"), data.get("countryCode")
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
        return round((time.monotonic() - start) * 1000, 1)
    except Exception:
        return None


async def enrich_entries(entries: List[ConfigEntry], session: aiohttp.ClientSession) -> None:
    geo_targets = entries[:MAX_ENRICH_GEOIP] if ENABLE_GEOIP else []
    lat_targets = entries[:MAX_ENRICH_LATENCY] if ENABLE_LATENCY else []

    async def do_geo(e: ConfigEntry) -> None:
        c, cc = await geoip_lookup(e.host or "", session)
        if c:
            e.country = c
        if cc:
            e.country_code = cc

    async def do_lat(e: ConfigEntry) -> None:
        ms = await measure_latency(e, session)
        if ms is not None:
            e.latency_ms = ms

    tasks: List[asyncio.Task] = []
    for e in geo_targets:
        tasks.append(asyncio.create_task(do_geo(e)))
    for e in lat_targets:
        tasks.append(asyncio.create_task(do_lat(e)))

    if tasks:
        await asyncio.gather(*tasks)


async def fetch_url(url: str, session: aiohttp.ClientSession) -> List[str]:
    try:
        async with session.get(url, timeout=25) as r:
            text = await r.text()
            return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        return []


async def fetch_all() -> Tuple[Dict[str, List[ConfigEntry]], int, int]:
    async with aiohttp.ClientSession() as session:
        tasks: List[Tuple[str, asyncio.Task]] = []
        for proto, urls in SOURCES.items():
            for u in urls:
                tasks.append((proto, asyncio.create_task(fetch_url(u, session))))

        raw_lines: Dict[str, List[str]] = {k: [] for k in SOURCES.keys()}

        for proto, task in tasks:
            try:
                lines = await task
                raw_lines[proto].extend(lines)
            except Exception:
                pass

        if "frag" in raw_lines:
            raw_lines["frag"] = [
                l for l in raw_lines["frag"]
                if not l.strip().startswith("#")
            ]

        entries: List[ConfigEntry] = []
        for proto, lines in raw_lines.items():
            for line in lines:
                e = parse_config(proto, line)
                if not e:
                    continue
                if proto != "frag" and is_fake(e):
                    continue
                entries.append(e)

        initial_count = len(entries)
        entries = dedupe_entries(entries)
        dedup_count = len(entries)

        await enrich_entries(entries, session)

        grouped: Dict[str, List[ConfigEntry]] = {k: [] for k in SOURCES.keys()}
        for e in entries:
            grouped.setdefault(e.proto, []).append(e)

        return grouped, initial_count, dedup_count


def compute_quality(e: ConfigEntry) -> None:
    country_weight = COUNTRY_PRIORITY.get(e.country_code or "", 0)
    lat = e.latency_ms if e.latency_ms is not None else 350.0
    e.quality_score = country_weight * 10 - lat * 0.3


def auto_failover_hiddify(vless_entries: List[ConfigEntry]) -> List[str]:
    scored: List[ConfigEntry] = []
    for e in vless_entries:
        compute_quality(e)
        scored.append(e)
    scored.sort(key=lambda x: (-(x.quality_score or -9999)))
    top = scored[:100]
    return [e.raw for e in top]


HIDDIFY_HEADER = """#profile-title: base64:8J+UpSBGcmFnbWVudCDwn5Sl
#profile-update-interval: 24
#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531
#support-url: https://t.me/proxystore11
#profile-web-page-url: https://proxystore11.news
#connection-test-url: https://instagram.com
#remote-dns-address: https://sky.rethinkdns.com/dns-query
"""


async def run() -> None:
    ensure_dirs()

    grouped, initial_count, dedup_count = await fetch_all()

    vless = grouped.get("vless", [])
    vmess = grouped.get("vmess", [])
    trojan = grouped.get("trojan", [])
    ss = grouped.get("ss", [])
    frag = grouped.get("frag", [])

    vless_raw = [e.raw for e in vless]
    vmess_raw = [e.raw for e in vmess]
    trojan_raw = [e.raw for e in trojan]
    ss_raw = [e.raw for e in ss]
    frag_raw = [e.raw for e in frag]

    hiddify_lines = auto_failover_hiddify(vless)
    insta_lines = frag_raw

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "prx11-vless.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(vless_raw))
    with open(os.path.join(OUTPUT_DIR, "prx11-vmess.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(vmess_raw))
    with open(os.path.join(OUTPUT_DIR, "prx11-trojan.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(trojan_raw))
    with open(os.path.join(OUTPUT_DIR, "prx11-ss.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(ss_raw))

    with open(os.path.join(OUTPUT_DIR, "prx11-hiddify.txt"), "w", encoding="utf-8") as f:
        f.write(HIDDIFY_HEADER + "\n" + "\n".join(hiddify_lines))
    with open(os.path.join(OUTPUT_DIR, "prx11-insta-youto.txt"), "w", encoding="utf-8") as f:
        f.write(HIDDIFY_HEADER + "\n" + "\n".join(insta_lines))

    all_raw = vless_raw + vmess_raw + trojan_raw + ss_raw
    all_raw = list(dict.fromkeys(all_raw))
    with open(os.path.join(OUTPUT_DIR, "prx11-all.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(all_raw))

    iran_ts = datetime.utcnow().timestamp() + 3.5 * 3600
    iran_str = datetime.fromtimestamp(iran_ts).strftime("%Y-%m-%d %H:%M:%S")
    with open(AUTO_UPDATE_FILE, "w", encoding="utf-8") as f:
        f.write(f"Auto Update: {iran_str}")

    country_stats: Dict[str, int] = {}
    latency_map: Dict[str, List[float]] = {}

    for lst in [vless, vmess, trojan, ss]:
        for e in lst:
            cc = e.country_code or "??"
            country_stats[cc] = country_stats.get(cc, 0) + 1
            if e.latency_ms is not None:
                latency_map.setdefault(cc, []).append(e.latency_ms)

    latency_summary: Dict[str, Dict[str, float]] = {}
    for cc, vals in latency_map.items():
        latency_summary[cc] = {
            "avg": round(statistics.mean(vals), 1),
            "min": round(min(vals), 1),
            "max": round(max(vals), 1),
        }

    top_fast = sorted(
        [(cc, latency_summary[cc]["avg"]) for cc in latency_summary],
        key=lambda x: x[1],
    )[:10]

    log_data = {
        "updated_at_iran": iran_str,
        "initial_configs": initial_count,
        "after_dedup": dedup_count,
        "removed_duplicates": initial_count - dedup_count,
        "country_distribution": country_stats,
        "latency_summary_ms": latency_summary,
        "top10_fastest_countries": top_fast,
    }

    with open(LOGGER_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print("Enterprise Collector completed at", iran_str)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
