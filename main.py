#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRX11 V2Ray Config Collector - Async & Web UI Edition

ویژگی‌ها:
- جمع‌آوری کانفیگ‌ها از منابع مخفی (Base64)
- پردازش پروتکل‌های VMess / VLess / Trojan / Shadowsocks
- پینگ Async با استفاده از aiohttp
- تولید ریمارک‌های زیبا بر اساس کشور + پینگ
- تولید فایل‌های Sub (متن ساده) + نسخه‌های Base64 / Gzip+Base64
- گزارش آماری JSON
- وب‌ UI ساده برای مشاهده گزارش و دانلود Sub
"""

import asyncio
import base64
import json
import os
import re
import socket
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import yaml

# ---------------------------
# تنظیمات پیش‌فرض / Default
# ---------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "project": {
        "name": "PRX11",
        "version": "5.0.0",
        "description": "Async V2Ray collector with ping & web UI",
        "author": "PRX11 Team",
    },
    "countries": {
        "US": "🇺🇸 | آمریکا",
    },
    "settings": {
        "max_configs": 200,
        "timeout": 30,
        "ping_timeout": 10,
        "max_workers": 20,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    "remark": {
        "format": "{flag} | {country} | {config_number:02d} | {ping}ms | {project_name}",
        "project_name": "PRX11",
    },
    "subscription_files": {
        "all": "PRX11-ALL.txt",
        "vmess": "PRX11-VMESS.txt",
        "vless": "PRX11-VLESS.txt",
        "shadowsocks": "PRX11-SS.txt",
        "trojan": "PRX11-TROJAN.txt",
        "working": "PRX11-WORKING.txt",
        # encoded/ compressed versions (generated در کنار نسخه‌های اصلی)
        "all_b64": "PRX11-ALL.b64.txt",
        "all_gzip_b64": "PRX11-ALL.gz.b64.txt",
    },
}

HIDDEN_SOURCES_ENCODED: List[str] = [
    # همان مقادیر نسخه قبلی – در صورت نیاز می‌توانید اضافه/کم کنید
    "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA==",
]

PING_SERVICES = [
    "https://api.codebazan.ir/ping/",
    "https://api.codebazan.ir/ping/",  # backup
]
IPINFO_SERVICE = "https://api.codebazan.ir/ipinfo/"


# ---------------------------
# انواع داده
# ---------------------------

@dataclass
class RawConfig:
    raw_config: str
    hash: str
    type: str  # vmess, vless, trojan, ss, unknown


@dataclass
class ProcessedConfig:
    final_url: str
    protocol: str
    country: str
    remark: str
    server: str
    port: str
    config_number: int
    ping: Optional[float]
    status: str
    raw_config: RawConfig = field(repr=False)


# ---------------------------
# Utility functions
# ---------------------------

def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dict b into a (recursively) و خروجی جدید برگردان."""
    result = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_project_config(path: str = "config.yaml") -> Dict[str, Any]:
    """بارگذاری config.yaml و ادغام با DEFAULT_CONFIG."""
    if not os.path.exists(path):
        print(f"⚠️ config.yaml یافت نشد، استفاده از تنظیمات پیش‌فرض")
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # پشتیبانی از چند سند YAML (در صورت استفاده از '---' یا '...')
        docs = list(yaml.safe_load_all(content))
        if not docs:
            print("⚠️ config.yaml خالی است، استفاده از پیش‌فرض")
            return DEFAULT_CONFIG.copy()

        # اگر چند داکیومنت باشد، همه را روی هم merge می‌کنیم
        cfg: Dict[str, Any] = {}
        for d in docs:
            if isinstance(d, dict):
                cfg = deep_merge(cfg, d)

        merged = deep_merge(DEFAULT_CONFIG, cfg)
        return merged
    except Exception as e:
        print(f"⚠️ خطا در خواندن config.yaml: {e}")
        return DEFAULT_CONFIG.copy()


def ensure_directories() -> None:
    """ایجاد پوشه‌های مورد نیاز."""
    dirs = ["output/configs", "output/subscriptions", "output/logs"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def normalize_b64(payload: str) -> bytes:
    """استانداردسازی Base64 (اضافه کردن padding در صورت نیاز)."""
    payload = payload.strip()
    missing = (-len(payload)) % 4
    if missing:
        payload += "=" * missing
    return base64.b64decode(payload.encode("utf-8"), validate=False)


def decode_hidden_sources() -> List[str]:
    urls: List[str] = []
    for enc in HIDDEN_SOURCES_ENCODED:
        try:
            urls.append(base64.b64decode(enc).decode("utf-8"))
        except Exception as e:
            print(f"⚠️ خطا در decode منبع مخفی: {e}")
    return urls


def extract_all_configs_from_text(text: str) -> List[RawConfig]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[A-Za-z0-9%\.\-_@?&=#:]+",
        "trojan": r"trojan://[A-Za-z0-9%\.\-_@?&=#:]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }
    result: List[RawConfig] = []

    for typ, pat in patterns.items():
        for match in re.findall(pat, text):
            h = hashlib.md5(match.encode("utf-8")).hexdigest()
            result.append(RawConfig(raw_config=match, hash=h, type=typ))

    return result


def deduplicate_configs(configs: List[RawConfig]) -> List[RawConfig]:
    seen: set = set()
    unique: List[RawConfig] = []
    for c in configs:
        if c.hash not in seen:
            unique.append(c)
            seen.add(c.hash)
    if len(configs) != len(unique):
        print(f"♻️ حذف {len(configs) - len(unique)} کانفیگ تکراری")
    return unique


# ---------------------------
# Async HTTP Layer
# ---------------------------

class HttpClient:
    def __init__(self, user_agent: str, timeout: int, max_workers: int):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_workers = max_workers
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_workers)

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("HttpClient session not initialized")
        return self._session

    async def get_text(self, url: str, *, label: str = "") -> Optional[str]:
        async with self._semaphore:
            try:
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        print(f"❌ [{label}] HTTP {resp.status} for {url}")
                        return None
                    return await resp.text()
            except Exception as e:
                print(f"⚠️ [{label}] خطا در درخواست {url}: {e}")
                return None

    async def get_json(self, url: str, *, label: str = "") -> Optional[Dict[str, Any]]:
        async with self._semaphore:
            try:
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        print(f"❌ [{label}] HTTP {resp.status} for {url}")
                        return None
                    return await resp.json()
            except Exception as e:
                print(f"⚠️ [{label}] خطا در درخواست {url}: {e}")
                return None


# ---------------------------
# منطق تشخیص کشور و Remark
# ---------------------------

class CountryResolver:
    def __init__(self, config: Dict[str, Any]):
        self.countries_cfg: Dict[str, str] = config.get("countries", {})

    def detect_country(self, hostname_or_ip: str) -> str:
        if not hostname_or_ip:
            return "US"

        h = hostname_or_ip.lower().strip()
        if h in ("unknown", "localhost"):
            return "US"

        # اگر IP باشد
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", h):
            return "US"

        # بر اساس TLD
        tld_match = re.search(r"\.([a-z]{2,3})$", h)
        if tld_match:
            tld = tld_match.group(1)
            for cc in self.countries_cfg.keys():
                if tld == cc.lower():
                    return cc

        # جستجو بر اساس نام کشور / کد
        for cc, label in self.countries_cfg.items():
            cc_lower = cc.lower()
            if cc_lower in h:
                return cc

            # "🇺🇸 | آمریکا"
            parts = [p.strip().lower() for p in label.split("|")]
            for p in parts:
                if p and p in h:
                    return cc

        return "US"

    def country_label(self, country_code: str) -> Tuple[str, str]:
        default_flag, default_name = "🇺🇸", "آمریکا"
        raw = self.countries_cfg.get(country_code, None)
        if not raw:
            return default_flag, default_name

        parts = [p.strip() for p in raw.split("|")]
        if len(parts) >= 2:
            return parts[0], parts[1]
        if len(parts) == 1:
            return "🇺🇸", parts[0]
        return default_flag, default_name


class RemarkFormatter:
    def __init__(self, config: Dict[str, Any], country_resolver: CountryResolver):
        self.cfg = config
        self.country_resolver = country_resolver
        self.project_name = config.get("remark", {}).get("project_name", "PRX11")

    def build_remark(
        self, country_code: str, country_index: int, ping_ms: Optional[float]
    ) -> str:
        flag, cname = self.country_resolver.country_label(country_code)
        ping_str = f"{int(ping_ms)}" if ping_ms is not None else "❓"
        return (
            f"{flag} | {cname} | {country_index:02d} | {ping_str}ms | {self.project_name}"
        )


# ---------------------------
# پروتکل‌ها (Strategy Pattern)
# ---------------------------

class BaseProtocolProcessor:
    def __init__(self, country_resolver: CountryResolver, remark_formatter: RemarkFormatter):
        self.country_resolver = country_resolver
        self.remark_formatter = remark_formatter

    def extract_server(self, cfg: RawConfig) -> str:
        raise NotImplementedError

    def process(
        self,
        cfg: RawConfig,
        country_counters: Dict[str, int],
        global_index: int,
        ping_value: Optional[float],
    ) -> ProcessedConfig:
        raise NotImplementedError


class VmessProcessor(BaseProtocolProcessor):
    def extract_server(self, cfg: RawConfig) -> str:
        try:
            payload = cfg.raw_config[len("vmess://") :]
            decoded = normalize_b64(payload).decode("utf-8")
            data = json.loads(decoded)
            return str(data.get("add", "unknown"))
        except Exception:
            return "unknown"

    def process(
        self,
        cfg: RawConfig,
        country_counters: Dict[str, int],
        global_index: int,
        ping_value: Optional[float],
    ) -> ProcessedConfig:
        try:
            payload = cfg.raw_config[len("vmess://") :]
            decoded = normalize_b64(payload).decode("utf-8")
            data = json.loads(decoded)

            server = str(data.get("add", "unknown"))
            port = str(data.get("port", ""))

            country_code = self.country_resolver.detect_country(server)
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], ping_value
            )
            data["ps"] = remark

            new_payload = base64.b64encode(
                json.dumps(data, ensure_ascii=False).encode("utf-8")
            ).decode("utf-8")
            new_payload = new_payload.rstrip("=")  # سبک فشرده
            final_url = f"vmess://{new_payload}"

            status = "working" if ping_value is not None and ping_value < 1000 else "unknown"

            return ProcessedConfig(
                final_url=final_url,
                protocol="vmess",
                country=country_code,
                remark=remark,
                server=server,
                port=port,
                config_number=global_index,
                ping=ping_value,
                status=status,
                raw_config=cfg,
            )
        except Exception:
            # fallback
            country_code = "US"
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], None
            )
            return ProcessedConfig(
                final_url=cfg.raw_config,
                protocol="vmess",
                country=country_code,
                remark=f"{remark} (Fallback)",
                server="unknown",
                port="",
                config_number=global_index,
                ping=None,
                status="error",
                raw_config=cfg,
            )


class UrlLikeProcessor(BaseProtocolProcessor):
    """
    برای VLess و Trojan که ساختارشان URL مانند است.
    """

    def __init__(
        self,
        protocol_name: str,
        country_resolver: CountryResolver,
        remark_formatter: RemarkFormatter,
    ):
        super().__init__(country_resolver, remark_formatter)
        self.protocol_name = protocol_name

    def extract_server(self, cfg: RawConfig) -> str:
        try:
            # proto://user@host:port?...
            m = re.search(r"@([^:#?]+)", cfg.raw_config)
            if m:
                return m.group(1)
            return "unknown"
        except Exception:
            return "unknown"

    def process(
        self,
        cfg: RawConfig,
        country_counters: Dict[str, int],
        global_index: int,
        ping_value: Optional[float],
    ) -> ProcessedConfig:
        try:
            server = self.extract_server(cfg)
            port_match = re.search(r":(\d+)", cfg.raw_config.split("@", 1)[-1])
            port = port_match.group(1) if port_match else ""

            country_code = self.country_resolver.detect_country(server)
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], ping_value
            )

            # اصلاح تگ # بدون دستکاری querystring
            if "#" in cfg.raw_config:
                base, _sep, _old_tag = cfg.raw_config.partition("#")
                final_url = f"{base}#{aiohttp.helpers.quote(remark, safe='')}"
            else:
                final_url = f"{cfg.raw_config}#{aiohttp.helpers.quote(remark, safe='')}"

            status = "working" if ping_value is not None and ping_value < 1000 else "unknown"

            return ProcessedConfig(
                final_url=final_url,
                protocol=self.protocol_name,
                country=country_code,
                remark=remark,
                server=server,
                port=port,
                config_number=global_index,
                ping=ping_value,
                status=status,
                raw_config=cfg,
            )
        except Exception:
            country_code = "US"
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], None
            )
            return ProcessedConfig(
                final_url=cfg.raw_config,
                protocol=self.protocol_name,
                country=country_code,
                remark=f"{remark} (Fallback)",
                server="unknown",
                port="",
                config_number=global_index,
                ping=None,
                status="error",
                raw_config=cfg,
            )


class ShadowsocksProcessor(BaseProtocolProcessor):
    def extract_server(self, cfg: RawConfig) -> str:
        try:
            # ss://base64 or ss://base64@host:port
            if "@" in cfg.raw_config:
                m = re.search(r"@([^:#?]+)", cfg.raw_config)
                if m:
                    return m.group(1)
            return "unknown"
        except Exception:
            return "unknown"

    def process(
        self,
        cfg: RawConfig,
        country_counters: Dict[str, int],
        global_index: int,
        ping_value: Optional[float],
    ) -> ProcessedConfig:
        try:
            server = self.extract_server(cfg)
            port_match = re.search(r":(\d+)", cfg.raw_config.split("@", 1)[-1])
            port = port_match.group(1) if port_match else ""

            country_code = self.country_resolver.detect_country(server)
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], ping_value
            )

            # در SS معمولاً تگ remark بعد از '#' می‌آید، اگر نبود اضافه می‌کنیم
            if "#" in cfg.raw_config:
                base, _sep, _old_tag = cfg.raw_config.partition("#")
                final_url = f"{base}#{aiohttp.helpers.quote(remark, safe='')}"
            else:
                final_url = f"{cfg.raw_config}#{aiohttp.helpers.quote(remark, safe='')}"

            status = "working" if ping_value is not None and ping_value < 1000 else "unknown"

            return ProcessedConfig(
                final_url=final_url,
                protocol="shadowsocks",
                country=country_code,
                remark=remark,
                server=server,
                port=port,
                config_number=global_index,
                ping=ping_value,
                status=status,
                raw_config=cfg,
            )
        except Exception:
            country_code = "US"
            country_counters[country_code] = country_counters.get(country_code, 0) + 1
            remark = self.remark_formatter.build_remark(
                country_code, country_counters[country_code], None
            )
            return ProcessedConfig(
                final_url=cfg.raw_config,
                protocol="shadowsocks",
                country=country_code,
                remark=f"{remark} (Fallback)",
                server="unknown",
                port="",
                config_number=global_index,
                ping=None,
                status="error",
                raw_config=cfg,
            )


class UnknownProcessor(BaseProtocolProcessor):
    def extract_server(self, cfg: RawConfig) -> str:
        return "unknown"

    def process(
        self,
        cfg: RawConfig,
        country_counters: Dict[str, int],
        global_index: int,
        ping_value: Optional[float],
    ) -> ProcessedConfig:
        country_code = "US"
        country_counters[country_code] = country_counters.get(country_code, 0) + 1
        remark = self.remark_formatter.build_remark(
            country_code, country_counters[country_code], ping_value
        )
        return ProcessedConfig(
            final_url=cfg.raw_config,
            protocol="unknown",
            country=country_code,
            remark=remark,
            server="unknown",
            port="",
            config_number=global_index,
            ping=ping_value,
            status="unknown",
            raw_config=cfg,
        )


# ---------------------------
# Ping & IP Info
# ---------------------------

async def ping_server_async(
    hostname: str, http: HttpClient, ping_timeout: int
) -> Optional[float]:
    if not hostname or hostname.lower() in ("unknown", "localhost"):
        return None

    # ابتدا DNS resolve
    try:
        # اگر IP بود، همان را نگه می‌داریم
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
            hostname = socket.gethostbyname(hostname)
    except Exception:
        # اگر DNS fail شود، همان hostname باقی می‌ماند
        pass

    for svc in PING_SERVICES:
        url = f"{svc}?url={hostname}"
        text = await http.get_text(url, label="ping")
        if not text:
            continue

        t = text.lower()
        m = re.search(r"(\d+\.?\d*)\s*ms", t)
        if not m:
            m = re.search(r"ping[^\d]*(\d+\.?\d*)", t)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue

    return None


async def get_ip_info_async(hostname: str, http: HttpClient) -> Optional[Dict[str, Any]]:
    if not hostname or hostname.lower() in ("unknown", "localhost"):
        return None
    try:
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
            hostname = socket.gethostbyname(hostname)
    except Exception:
        pass

    url = f"{IPINFO_SERVICE}?ip={hostname}"
    return await http.get_json(url, label="ipinfo")


# ---------------------------
# هسته اصلی Collector
# ---------------------------

class PRX11AsyncCollector:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.collected: List[RawConfig] = []
        self.processed: List[ProcessedConfig] = []

        self.country_resolver = CountryResolver(config)
        self.remark_formatter = RemarkFormatter(config, self.country_resolver)

        self.protocols = {
            "vmess": VmessProcessor(self.country_resolver, self.remark_formatter),
            "vless": UrlLikeProcessor("vless", self.country_resolver, self.remark_formatter),
            "trojan": UrlLikeProcessor("trojan", self.country_resolver, self.remark_formatter),
            "ss": ShadowsocksProcessor(self.country_resolver, self.remark_formatter),
        }
        self.unknown_processor = UnknownProcessor(self.country_resolver, self.remark_formatter)

    async def collect_from_hidden_sources(self, http: HttpClient) -> None:
        print("\n🎯 شروع جمع‌آوری از منابع مخفی...")
        decoded_urls = decode_hidden_sources()
        tasks = [http.get_text(u, label="hidden") for u in decoded_urls]
        texts = await asyncio.gather(*tasks)

        all_raw: List[RawConfig] = []
        for u, text in zip(decoded_urls, texts):
            if not text:
                print(f"❌ منبع مخفی در دسترس نیست: {u}")
                continue
            cfgs = extract_all_configs_from_text(text)
            all_raw.extend(cfgs)
            print(f"✅ منبع مخفی: {u} → {len(cfgs)} کانفیگ")

        self.collected = deduplicate_configs(all_raw)
        print(f"📊 کل کانفیگ‌های منحصر به فرد: {len(self.collected)}")

    async def process_with_ping(self, http: HttpClient) -> None:
        print("\n🔄 شروع پردازش کانفیگ‌ها (با پینگ Async)...")
        max_configs = int(self.cfg.get("settings", {}).get("max_configs", 200))
        ping_timeout = int(self.cfg.get("settings", {}).get("ping_timeout", 10))

        subset = self.collected[:max_configs]

        # مرحله ۱: استخراج server برای همه کانفیگ‌ها
        servers: List[str] = []
        for cfg in subset:
            processor = self.protocols.get(cfg.type, self.unknown_processor)
            server = processor.extract_server(cfg)
            servers.append(server)

        # مرحله ۲: پینگ موازی
        print(f"🌐 پینگ {len(servers)} سرور...")
        ping_tasks = [ping_server_async(s, http, ping_timeout) for s in servers]
        ping_results = await asyncio.gather(*ping_tasks)

        # مرحله ۳: پردازش نهایی
        country_counters: Dict[str, int] = {}
        processed: List[ProcessedConfig] = []
        protocol_stats: Dict[str, int] = {}

        for idx, cfg in enumerate(subset):
            processor = self.protocols.get(cfg.type, self.unknown_processor)
            protocol_stats[cfg.type] = protocol_stats.get(cfg.type, 0) + 1
            ping_val = ping_results[idx]

            pc = processor.process(
                cfg, country_counters=country_counters, global_index=idx + 1, ping_value=ping_val
            )
            processed.append(pc)

            if (idx + 1) % 20 == 0:
                print(f"📦 پردازش شده: {idx + 1}/{len(subset)}")

        self.processed = processed

        print("\n📊 آمار پروتکل‌ها:")
        for proto, cnt in protocol_stats.items():
            print(f"   {proto.upper():<10}: {cnt} کانفیگ")

    def _write_file(self, path: str, content: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ ذخیره شد: {path} ({len(content.splitlines())} خط)")
        except Exception as e:
            print(f"❌ خطا در ذخیره {path}: {e}")

    def save_subscription_files(self) -> None:
        print("\n💾 ایجاد لینک‌های Sub...")
        subs_cfg = self.cfg.get("subscription_files", {})

        vmess = [c.final_url for c in self.processed if c.protocol == "vmess"]
        vless = [c.final_url for c in self.processed if c.protocol == "vless"]
        trojan = [c.final_url for c in self.processed if c.protocol == "trojan"]
        ss = [c.final_url for c in self.processed if c.protocol == "shadowsocks"]
        working = [c.final_url for c in self.processed if c.status == "working"]
        all_links = [c.final_url for c in self.processed]

        def join(lst: List[str]) -> str:
            return "\n".join(lst)

        mapping = [
            (subs_cfg.get("all", "PRX11-ALL.txt"), join(all_links), "همه کانفیگ‌ها"),
            (subs_cfg.get("vmess", "PRX11-VMESS.txt"), join(vmess), "فقط VMess"),
            (subs_cfg.get("vless", "PRX11-VLESS.txt"), join(vless), "فقط VLess"),
            (subs_cfg.get("shadowsocks", "PRX11-SS.txt"), join(ss), "فقط Shadowsocks"),
            (subs_cfg.get("trojan", "PRX11-TROJAN.txt"), join(trojan), "فقط Trojan"),
            (subs_cfg.get("working", "PRX11-WORKING.txt"), join(working), "کانفیگ‌های کارکرده"),
        ]

        for filename, content, label in mapping:
            path = os.path.join("output", "subscriptions", filename)
            self._write_file(path, content)
            print(f"   {label}: {filename}")

        # نسخه فشرده/Encode شده
        import gzip

        all_text = join(all_links)
        # Base64 ساده
        b64_bytes = base64.b64encode(all_text.encode("utf-8")).decode("utf-8")
        b64_name = subs_cfg.get("all_b64", "PRX11-ALL.b64.txt")
        self._write_file(os.path.join("output", "subscriptions", b64_name), b64_bytes)

        # Gzip + Base64
        gz_bytes = gzip.compress(all_text.encode("utf-8"))
        gz_b64 = base64.b64encode(gz_bytes).decode("utf-8")
        gz_name = subs_cfg.get("all_gzip_b64", "PRX11-ALL.gz.b64.txt")
        self._write_file(os.path.join("output", "subscriptions", gz_name), gz_b64)

        print("✅ نسخه‌های Encode شده (Base64 / Gzip+Base64) نیز ایجاد شدند")

    def save_reports(self) -> None:
        print("\n📊 ایجاد گزارش آماری...")
        country_stats: Dict[str, int] = {}
        protocol_stats: Dict[str, int] = {}
        ping_stats: Dict[str, int] = {"working": 0, "unknown": 0, "error": 0}

        for c in self.processed:
            country_stats[c.country] = country_stats.get(c.country, 0) + 1
            protocol_stats[c.protocol] = protocol_stats.get(c.protocol, 0) + 1
            ping_stats[c.status] = ping_stats.get(c.status, 0) + 1

        summary = {
            "last_update": datetime.now().isoformat(),
            "project": self.cfg.get("project", {}),
            "total_configs": len(self.processed),
            "country_stats": country_stats,
            "protocol_stats": protocol_stats,
            "ping_stats": ping_stats,
            "subscription_files": self.cfg.get("subscription_files", {}),
            "sources_count": len(HIDDEN_SOURCES_ENCODED),
            "ping_services": PING_SERVICES,
        }

        path = os.path.join("output", "configs", "PRX11_SUMMARY.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"✅ گزارش ذخیره شد: {path}")
        except Exception as e:
            print(f"❌ خطا در ذخیره گزارش: {e}")

        # نمایش کلی روی کنسول
        print("\n🎯 آمار نهایی PRX11")
        print(f"🔢 کل کانفیگ‌ها: {len(self.processed)}")
        print(f"🔗 تعداد منابع مخفی: {len(HIDDEN_SOURCES_ENCODED)}")

        print("\n🌍 آمار کشورها:")
        for cc, cnt in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
            label = self.cfg.get("countries", {}).get(cc, cc)
            print(f"   {label:<20} : {cnt:>3}")

        print("\n🛡️ آمار پروتکل‌ها:")
        for proto, cnt in protocol_stats.items():
            print(f"   {proto.upper():<15} : {cnt:>3}")

        print("\n📡 آمار وضعیت پینگ:")
        for st, cnt in ping_stats.items():
            print(f"   {st:<10}: {cnt}")

    async def run_full_cycle(self) -> None:
        ensure_directories()
        settings = self.cfg.get("settings", {})
        timeout = int(settings.get("timeout", 30))
        max_workers = int(settings.get("max_workers", 20))
        user_agent = settings.get("user_agent", DEFAULT_CONFIG["settings"]["user_agent"])

        async with HttpClient(user_agent, timeout, max_workers) as http:
            await self.collect_from_hidden_sources(http)
            if not self.collected:
                print("❌ هیچ کانفیگی جمع‌آوری نشد")
                return

            await self.process_with_ping(http)
            if not self.processed:
                print("❌ هیچ کانفیگی پردازش نشد")
                return

        self.save_subscription_files()
        self.save_reports()


# ---------------------------
# وب UI ساده (aiohttp)
# ---------------------------

async def start_web_ui(collector: PRX11AsyncCollector, host: str = "0.0.0.0", port: int = 8080):
    from aiohttp import web

    async def index(request):
        # تلاش برای خواندن گزارش
        summary_path = os.path.join("output", "configs", "PRX11_SUMMARY.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        else:
            summary = {"error": "Summary not found. Run collector first."}

        html = "<html><head><meta charset='utf-8'><title>PRX11 Dashboard</title></head><body>"
        html += "<h1>PRX11 Dashboard</h1>"
        if "error" in summary:
            html += f"<p style='color:red'>{summary['error']}</p>"
        else:
            html += "<h2>Summary</h2>"
            html += f"<p>Last update: {summary.get('last_update','-')}</p>"
            html += f"<p>Total configs: {summary.get('total_configs',0)}</p>"

            html += "<h3>Protocol stats</h3><ul>"
            for k, v in summary.get("protocol_stats", {}).items():
                html += f"<li>{k}: {v}</li>"
            html += "</ul>"

            html += "<h3>Country stats</h3><ul>"
            for k, v in summary.get("country_stats", {}).items():
                html += f"<li>{k}: {v}</li>"
            html += "</ul>"

            html += "<h3>Ping stats</h3><ul>"
            for k, v in summary.get("ping_stats", {}).items():
                html += f"<li>{k}: {v}</li>"
            html += "</ul>"

            html += "<h3>Subscription files</h3><ul>"
            for key, fname in summary.get("subscription_files", {}).items():
                html += f"<li>{key}: <a href='/sub/{fname}'>{fname}</a></li>"
            html += "</ul>"

        html += "<hr><p><a href='/api/summary'>JSON Summary</a></p>"
        html += "<p><a href='/refresh'>Refresh (run collector)</a></p>"
        html += "</body></html>"
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def api_summary(request):
        summary_path = os.path.join("output", "configs", "PRX11_SUMMARY.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        else:
            summary = {"error": "Summary not found. Run collector first."}
        from aiohttp import web as _web
        return _web.json_response(summary, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    async def serve_sub(request):
        from aiohttp import web as _web
        fname = request.match_info.get("filename")
        path = os.path.join("output", "subscriptions", fname)
        if not os.path.exists(path):
            raise _web.HTTPNotFound(text="File not found")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return _web.Response(text=content, content_type="text/plain", charset="utf-8")

    async def refresh(request):
        from aiohttp import web as _web

        async def _run():
            await collector.run_full_cycle()

        # اجرای collector در background
        asyncio.create_task(_run())
        return _web.json_response({"status": "started"})

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/api/summary", api_summary)
    app.router.add_get("/sub/{filename}", serve_sub)
    app.router.add_get("/refresh", refresh)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    print(f"🌐 Web UI on http://{host}:{port}")
    await site.start()

    # منتظر بمان تا Ctrl+C
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        print("🛑 توقف Web UI ...")
    finally:
        await runner.cleanup()


# ---------------------------
# Entry point / CLI
# ---------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="PRX11 Async V2Ray Collector")
    parser.add_argument(
        "--web",
        action="store_true",
        help="اجرای وب‌ UI بعد از جمع‌آوری (dashboard)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="آدرس bind برای وب UI (پیش‌فرض: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="پورت وب UI (پیش‌فرض: 8080)"
    )
    args = parser.parse_args()

    cfg = load_project_config()
    collector = PRX11AsyncCollector(cfg)

    async def runner():
        await collector.run_full_cycle()
        if args.web:
            await start_web_ui(collector, host=args.host, port=args.port)

    asyncio.run(runner())


if __name__ == "__main__":
    main()
