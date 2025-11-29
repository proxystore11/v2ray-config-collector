#!/usr/bin/env python3

import asyncio
import aiohttp
import base64
import json
import yaml
import re
import os
import hashlib
import random
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_CONFIG = {
    "project": {"name": "prx11", "version": "1"},
    "settings": {
        "max_configs": 2000,
        "timeout": 20,
        "max_workers": 50,
    },
    "subscription_files": {
        "hiddify": "prx11-hiddify.txt",
        "insta": "prx11-insta-youto.txt",
        "vmess": "prx11-vmess.txt",
        "vless": "prx11-vless.txt",
        "ss": "prx11-ss.txt",
        "trojan": "prx11-trojan.txt",
    },
}

HIDDEN_SOURCES = [
    # vless
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZsZXNzLnR4dA==",
    # vmess
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZtZXNzLnR4dA==",
    # multiple_config.json
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0dGVy1rbm9ja2VyL2dmd19yZXNpc3RfSFRUUFNfcHJveHkvcmVmcy9oZWFkcy9tYWluL211bHRpcGxlX2NvbmZpZy5qc29u",
    # ss
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3NzLnR4dA==",
    # trojan
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3Ryb2phbi50eHQ=",
]

INSTAGRAM_FRAGMENT_URL = (
    "https://raw.githubusercontent.com/hiddify/hiddify-app/refs/heads/main/test.configs/fragment"
)

EMOJI_POOL = ["🚀", "🔥", "⚡", "🎯", "✨", "🎉", "😍", "😎", "💎", "🌐"]


def load_config() -> dict:
    if not os.path.exists("config.yaml"):
        return DEFAULT_CONFIG
    with open("config.yaml", "r", encoding="utf-8") as f:
        user_cfg = yaml.safe_load(f) or {}
    cfg = DEFAULT_CONFIG.copy()
    for k, v in user_cfg.items():
        if k == "subscription_files":
            cfg["subscription_files"].update(v)
        else:
            cfg[k] = v
    return cfg


def ensure_dirs() -> None:
    os.makedirs("output/subscriptions", exist_ok=True)
    os.makedirs("output/configs", exist_ok=True)


def decode_b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


def normalize_b64(d: str) -> bytes:
    missing = (-len(d)) % 4
    if missing:
        d += "=" * missing
    return base64.b64decode(d)


def extract_configs(text: str) -> list[dict]:
    patterns = {
        "vmess": r"vmess://[A-Za-z0-9+/=]+",
        "vless": r"vless://[^\s]+",
        "trojan": r"trojan://[^\s]+",
        "ss": r"ss://[A-Za-z0-9+/=]+",
    }
    out: list[dict] = []
    for t, pat in patterns.items():
        for m in re.findall(pat, text):
            out.append(
                {
                    "raw": m.strip(),
                    "type": t,
                    "hash": hashlib.md5(m.strip().encode("utf-8")).hexdigest(),
                }
            )
    return out


def dedupe(configs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    res: list[dict] = []
    for c in configs:
        h = c["hash"]
        if h not in seen:
            seen.add(h)
            res.append(c)
    return res


def make_remark() -> str:
    e1 = random.choice(EMOJI_POOL)
    e2 = random.choice(EMOJI_POOL)
    return f"{e1}join@proxystore11 | freeconfig{e2} |"


async def process_config(cfg: dict) -> tuple[str, str]:
    raw = cfg["raw"]
    t = cfg["type"]
    r = make_remark()
    if t == "vmess":
        try:
            payload = raw[len("vmess://") :]
            data = json.loads(normalize_b64(payload).decode("utf-8"))
            data["ps"] = r
            new_payload = base64.b64encode(
                json.dumps(data, ensure_ascii=False).encode("utf-8")
            ).decode("utf-8")
            new_payload = new_payload.rstrip("=")
            return "vmess://" + new_payload, t
        except Exception:
            return raw, t
    else:
        from urllib.parse import quote

        base = raw.split("#", 1)[0]
        return f"{base}#{quote(r)}", t


async def run_collector() -> None:
    cfg = load_config()
    ensure_dirs()

    timeout = cfg["settings"]["timeout"]
    max_configs = cfg["settings"]["max_configs"]
    sources = [decode_b64(x) for x in HIDDEN_SOURCES]

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session:
        all_configs: list[dict] = []

        for url in sources:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        configs = extract_configs(text)
                        all_configs.extend(configs)
            except Exception:
                continue

        all_configs = dedupe(all_configs)[:max_configs]

        tasks = [process_config(c) for c in all_configs]
        results = await asyncio.gather(*tasks)

        vmess = [u for u, t in results if t == "vmess"]
        vless = [u for u, t in results if t == "vless"]
        ss = [u for u, t in results if t == "ss"]
        trojan = [u for u, t in results if t == "trojan"]

        subs = cfg["subscription_files"]

        with open(
            os.path.join("output", "subscriptions", subs["vmess"]), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(vmess))

        with open(
            os.path.join("output", "subscriptions", subs["vless"]), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(vless))

        with open(
            os.path.join("output", "subscriptions", subs["ss"]), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(ss))

        with open(
            os.path.join("output", "subscriptions", subs["trojan"]),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("\n".join(trojan))

        hiddify_header = (
            "//profile-title: base64:cHJ4MTEtZnJlZWNvbmZpZw==\n"
            "//profile-update-interval: 24\n"
            "//subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=0\n"
            "//support-url: https://t.me/proxystore11\n"
            "//profile-web-page-url: https://t.me/proxystore11\n\n"
        )

        combined = vmess + vless + ss + trojan
        hiddify_body = combined[:100]

        with open(
            os.path.join("output", "subscriptions", subs["hiddify"]),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(hiddify_header)
            f.write("\n".join(hiddify_body))

        try:
            async with session.get(INSTAGRAM_FRAGMENT_URL) as resp:
                fragment_text = await resp.text()
        except Exception:
            fragment_text = ""

        parts = fragment_text.split("\n\n", 1)
        if len(parts) == 2:
            fragment_body = parts[1]
        else:
            fragment_body = fragment_text

        insta_header = (
            "#profile-title: base64:cHJ4MTEtaW5zdGEteW91dHViZQ==\n"
            "#profile-update-interval: 24\n"
            "#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531\n"
            "#support-url: https://t.me/proxystore11\n"
            "#profile-web-page-url: https://proxystore11.news\n"
            "#connection-test-url: https://instagram.com\n"
            "#remote-dns-address: https://sky.rethinkdns.com/dns-query\n\n"
        )

        with open(
            os.path.join("output", "subscriptions", subs["insta"]),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(insta_header)
            f.write(fragment_body.strip() + "\n")

        now_ir = datetime.now(ZoneInfo("Asia/Tehran"))
        timestamp = now_ir.strftime("%Y-%m-%d %H:%M:%S")

        summary = {
            "last_update": timestamp,
            "timezone": "Asia/Tehran",
            "total_configs": len(results),
            "version": cfg["project"]["version"],
        }

        with open(
            os.path.join("output", "configs", "prx11_summary.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        with open(
            os.path.join("output", "AUTO_UPDATE.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(f"Auto Update: {timestamp}\n")


def main() -> None:
    asyncio.run(run_collector())


if __name__ == "__main__":
    main()
