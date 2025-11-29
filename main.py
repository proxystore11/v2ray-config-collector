#!/usr/bin/env python3

import asyncio, aiohttp, base64, json, yaml, re, os, hashlib, random
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_CONFIG = {
    "project": {"name": "prx11", "version": "1"},
    "settings": {"max_configs": 2000, "timeout": 20, "max_workers": 50},
    "subscription_files": {
        "hiddify": "prx11-hiddify.txt",
        "insta": "prx11-insta-youto.txt",
        "vmess": "prx11-vmess.txt",
        "vless": "prx11-vless.txt",
        "ss": "prx11-ss.txt",
        "trojan": "prx11-trojan.txt"
    }
}

HIDDEN_SOURCES = [
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZsZXNzLnR4dA==",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3ZtZXNzLnR4dA==",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0dGVy1rbm9ja2VyL2dmd19yZXNpc3RfSFRUUFNfcHJveHkvcmVmcy9oZWFkcy9tYWluL211bHRpcGxlX2NvbmZpZy5qc29u",
    "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1NvbGlTcGlyaXQvdjJyYXktY29uZmlncy9yZWZzL2hlYWRzL21haW4vUHJvdG9jb2xzL3NzLnR4dA=="
]

INSTAGRAM_FRAGMENT = "https://raw.githubusercontent.com/hiddify/hiddify-app/refs/heads/main/test.configs/fragment"

EMOJI_POOL = ["🚀","🔥","⚡","🎯","✨","🎉","😍","😎","💎","🌐"]

def load_config():
    if not os.path.exists("config.yaml"):
        return DEFAULT_CONFIG
    with open("config.yaml","r",encoding="utf-8") as f:
        return DEFAULT_CONFIG | yaml.safe_load(f)

def ensure_dirs():
    os.makedirs("output/subscriptions",exist_ok=True)
    os.makedirs("output/configs",exist_ok=True)

def decode_b64(s): return base64.b64decode(s).decode()

def normalize_b64(d):
    missing = (-len(d)) % 4
    if missing: d+="="*missing
    return base64.b64decode(d)

def extract(text):
    p={
        "vmess":r"vmess://[A-Za-z0-9+/=]+",
        "vless":r"vless://[^\s]+",
        "trojan":r"trojan://[^\s]+",
        "ss":r"ss://[A-Za-z0-9+/=]+"
    }
    out=[]
    for t,pat in p.items():
        for m in re.findall(pat,text):
            out.append({"raw":m,"type":t,"hash":hashlib.md5(m.encode()).hexdigest()})
    return out

def dedupe(arr):
    seen=set();res=[]
    for c in arr:
        if c["hash"] not in seen:
            seen.add(c["hash"])
            res.append(c)
    return res

def remark(i,project):
    e1=random.choice(EMOJI_POOL)
    e2=random.choice(EMOJI_POOL)
    return f"{e1}join@proxystore11 | freeconfig{e2} | {project} #{i:03d}"

async def process(c,i,project):
    raw=c["raw"];t=c["type"];r=remark(i,project)
    if t=="vmess":
        try:
            p=raw[8:];d=json.loads(normalize_b64(p))
            d["ps"]=r
            np=base64.b64encode(json.dumps(d).encode()).decode().rstrip("=")
            return "vmess://"+np,t
        except:
            return raw,t
    else:
        from urllib.parse import quote
        base=raw.split("#")[0]
        return f"{base}#{quote(r)}",t

async def run():
    cfg=load_config()
    ensure_dirs()
    timeout=cfg["settings"]["timeout"]
    maxc=cfg["settings"]["max_configs"]
    sources=[decode_b64(x) for x in HIDDEN_SOURCES]

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
        allc=[]
        for url in sources:
            try:
                async with s.get(url) as r:
                    if r.status==200:
                        txt=await r.text()
                        allc+=extract(txt)
            except: pass

        allc=dedupe(allc)[:maxc]

        tasks=[process(c,i+1,cfg["project"]["name"]) for i,c in enumerate(allc)]
        res=await asyncio.gather(*tasks)

        vmess=[x[0] for x in res if x[1]=="vmess"]
        vless=[x[0] for x in res if x[1]=="vless"]
        ss=[x[0] for x in res if x[1]=="ss"]
        trojan=[x[0] for x in res if x[1]=="trojan"]

        with open("output/subscriptions/"+cfg["subscription_files"]["vmess"],"w") as f: f.write("\n".join(vmess))
        with open("output/subscriptions/"+cfg["subscription_files"]["vless"],"w") as f: f.write("\n".join(vless))
        with open("output/subscriptions/"+cfg["subscription_files"]["ss"],"w") as f: f.write("\n".join(ss))
        with open("output/subscriptions/"+cfg["subscription_files"]["trojan"],"w") as f: f.write("\n".join(trojan))

        hhead = (
            "//profile-title: base64:cHJ4MTEtZnJlZWNvbmZpZw==\n"
            "//profile-update-interval: 24\n"
            "//subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=0\n"
            "//support-url: https://t.me/proxystore11\n"
            "//profile-web-page-url: https://t.me/proxystore11\n\n"
        )

        with open("output/subscriptions/"+cfg["subscription_files"]["hiddify"],"w") as f:
            f.write(hhead)
            f.write("\n".join(vmess+vless+ss+trojan))

        async with s.get(INSTAGRAM_FRAGMENT) as r:
            frag = await r.text()

        insta_header = (
            "#profile-title: base64:8J+UpSBGcmFnbWVudCDwn5Sl\n"
            "#profile-update-interval: 24\n"
            "#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531\n"
            "#support-url: https://t.me/hiddify\n"
            "#profile-web-page-url: https://hiddify.com\n"
            "#connection-test-url: https://instagram.com\n"
            "#remote-dns-address: https://sky.rethinkdns.com/dns-query\n\n"
        )

        with open("output/subscriptions/"+cfg["subscription_files"]["insta"],"w") as f:
            f.write(insta_header)
            f.write(frag)

        now=datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M:%S")
        with open("output/configs/prx11_summary.json","w") as f:
            json.dump({"last_update":now,"total":len(res),"version":"1"},f)

        with open("output/AUTO_UPDATE.txt","w") as f:
            f.write("Auto Update: "+now+"\n")

def main(): asyncio.run(run())

if __name__=="__main__": main()
