project:
  name: "PRX11"
  version: "4.0.0"
  description: "پروژه ساده و مطمئن جمع‌آوری کانفیگ‌های V2Ray"

sources:
  vmess:
    - "https://raw.githubusercontent.com/freev2ray/freev2ray/master/README.md"
    - "https://raw.githubusercontent.com/eliv2-hub/ELiV2-RAY/refs/heads/main/Channel-ELiV2-Ray.txt"
    - "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vmess_iran.txt"

  vless:
    - "https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/vless.html"
    - "https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/mixed_iran.txt"

  shadowsocks:
    - "https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/ss.html"
    - "https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/mixarshia_ss"

  trojan:
    - "https://raw.githubusercontent.com/v2ray/dist/master/v2ray-configs.txt"

settings:
  max_configs: 100
  timeout: 30

remark:
  format: "{flag} | {country} | {config_number:02d} | {project_name}"
  project_name: "PRX11"

subscription_files:
  all: "PRX11-ALL.txt"
  vmess: "PRX11-VMESS.txt"
  vless: "PRX11-VLESS.txt"
  shadowsocks: "PRX11-SS.txt"
  trojan: "PRX11-TROJAN.txt"
