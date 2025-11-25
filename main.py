#!/usr/bin/env python3
# 🛡️ PRX11 V2Ray Config Collector - Advanced Version
# ✨ تشخیص هوشمند کشور | فرمت‌بندی زیبا | منابع طبقه‌بندی شده

import os
import json
import base64
import requests
import re
import yaml
from datetime import datetime
import hashlib
import ipaddress
import socket
import time

class PRX11ConfigCollector:
    def __init__(self):
        self.config_data = self.load_config()
        self.collected_configs = []
        self.processed_configs = []
        self.country_cache = {}
        
    def load_config(self):
        """بارگذاری تنظیمات از فایل YAML"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری config.yaml: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """تنظیمات پیش‌فرض"""
        return {
            'project': {'name': 'PRX11', 'version': '3.0.0'},
            'sources': {
                'vmess': ['https://raw.githubusercontent.com/freev2ray/freev2ray/master/README.md'],
                'vless': ['https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/vless.html'],
                'shadowsocks': ['https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/ss.html'],
                'trojan': ['https://raw.githubusercontent.com/v2ray/dist/master/v2ray-configs.txt']
            },
            'countries': {
                'US': '🇺🇸 | آمریکا', 'DE': '🇩🇪 | آلمان', 'FR': '🇫🇷 | فرانسه',
                'NL': '🇳🇱 | هلند', 'TR': '🇹🇷 | ترکیه', 'SG': '🇸🇬 | سنگاپور',
                'JP': '🇯🇵 | ژاپن', 'KR': '🇰🇷 | کره', 'GB': '🇬🇧 | انگلیس',
                'CA': '🇨🇦 | کانادا', 'HK': '🇭🇰 | هنگ‌کنگ', 'IR': '🇮🇷 | ایران'
            },
            'settings': {'max_configs': 100, 'timeout': 25},
            'remark': {
                'format': '{flag} | {country} | {config_number:02d} | {project_name}',
                'project_name': 'PRX11'
            }
        }
    
    def create_directories(self):
        """ایجاد پوشه‌های لازم"""
        directories = [
            'output/configs', 
            'output/subscriptions',
            'output/logs'
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        print("✅ پوشه‌های خروجی ایجاد شدند")
    
    def make_request(self, url, config_type="عمومی"):
        """درخواست HTTP با مدیریت خطا"""
        try:
            headers = {
                'User-Agent': self.config_data['settings']['user_agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            print(f"🌐 دریافت {config_type} از: {url}")
            response = requests.get(url, headers=headers, timeout=self.config_data['settings']['timeout'])
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"❌ خطا در دریافت {config_type}: {e}")
            return None
    
    def collect_from_all_sources(self):
        """جمع‌آوری کانفیگ‌ها از تمام منابع طبقه‌بندی شده"""
        print("\n🎯 شروع جمع‌آوری از منابع طبقه‌بندی شده...")
        print("=" * 60)
        
        all_configs = []
        
        # جمع‌آوری از منابع VMess
        if 'vmess' in self.config_data['sources']:
            for url in self.config_data['sources']['vmess']:
                content = self.make_request(url, "VMess")
                if content:
                    configs = self.extract_configs(content, 'vmess')
                    all_configs.extend(configs)
                    print(f"✅ VMess: {len(configs)} کانفیگ")
        
        # جمع‌آوری از منابع VLess
        if 'vless' in self.config_data['sources']:
            for url in self.config_data['sources']['vless']:
                content = self.make_request(url, "VLess")
                if content:
                    configs = self.extract_configs(content, 'vless')
                    all_configs.extend(configs)
                    print(f"✅ VLess: {len(configs)} کانفیگ")
        
        # جمع‌آوری از منابع Shadowsocks
        if 'shadowsocks' in self.config_data['sources']:
            for url in self.config_data['sources']['shadowsocks']:
                content = self.make_request(url, "Shadowsocks")
                if content:
                    configs = self.extract_configs(content, 'ss')
                    all_configs.extend(configs)
                    print(f"✅ Shadowsocks: {len(configs)} کانفیگ")
        
        # جمع‌آوری از منابع Trojan
        if 'trojan' in self.config_data['sources']:
            for url in self.config_data['sources']['trojan']:
                content = self.make_request(url, "Trojan")
                if content:
                    configs = self.extract_configs(content, 'trojan')
                    all_configs.extend(configs)
                    print(f"✅ Trojan: {len(configs)} کانفیگ")
        
        # حذف duplicates
        self.collected_configs = self.remove_duplicates(all_configs)
        
        print(f"\n📊 جمع‌آوری کامل!")
        print(f"🎯 کل کانفیگ‌های منحصر به فرد: {len(self.collected_configs)}")
        
        return self.collected_configs
    
    def extract_configs(self, text, config_type):
        """استخراج کانفیگ‌ها از متن بر اساس نوع"""
        patterns = {
            'vmess': [r'vmess://[A-Za-z0-9+/=]+'],
            'vless': [r'vless://[^\s"\']+'],
            'trojan': [r'trojan://[^\s"\']+'],
            'ss': [r'ss://[A-Za-z0-9+/=]+']
        }
        
        configs = []
        for pattern in patterns.get(config_type, []):
            matches = re.findall(pattern, text)
            for match in matches:
                config_hash = hashlib.md5(match.encode()).hexdigest()
                configs.append({
                    'raw_config': match,
                    'hash': config_hash,
                    'type': config_type,
                    'source': 'classified'
                })
        
        return configs
    
    def remove_duplicates(self, configs):
        """حذف کانفیگ‌های تکراری"""
        unique_configs = []
        seen_hashes = set()
        
        for config in configs:
            if config['hash'] not in seen_hashes:
                unique_configs.append(config)
                seen_hashes.add(config['hash'])
        
        removed = len(configs) - len(unique_configs)
        if removed > 0:
            print(f"♻️ حذف {removed} کانفیگ تکراری")
        
        return unique_configs
    
    def process_configs(self):
        """پردازش هوشمند کانفیگ‌ها"""
        print("\n🔄 شروع پردازش هوشمند کانفیگ‌ها...")
        print("=" * 50)
        
        processed = []
        country_counters = {}
        protocol_stats = {}
        
        max_configs = self.config_data['settings']['max_configs']
        
        for i, config in enumerate(self.collected_configs[:max_configs]):
            try:
                # آمار پروتکل
                proto = config['type']
                protocol_stats[proto] = protocol_stats.get(proto, 0) + 1
                
                if config['type'] == 'vmess':
                    processed_config = self.process_vmess_config(config, country_counters, i+1)
                elif config['type'] == 'vless':
                    processed_config = self.process_vless_config(config, country_counters, i+1)
                elif config['type'] == 'trojan':
                    processed_config = self.process_trojan_config(config, country_counters, i+1)
                elif config['type'] == 'ss':
                    processed_config = self.process_ss_config(config, country_counters, i+1)
                else:
                    processed_config = self.process_unknown_config(config, country_counters, i+1)
                
                if processed_config:
                    processed.append(processed_config)
                    
                # نمایش پیشرفت
                if (i + 1) % 20 == 0:
                    print(f"📦 پردازش شده: {i+1}/{min(len(self.collected_configs), max_configs)}")
                    
            except Exception as e:
                print(f"⚠️ خطا در پردازش کانفیگ {i+1}: {e}")
                # اضافه کردن نسخه اصلی در صورت خطا
                processed.append({
                    **config,
                    'final_url': config['raw_config'],
                    'country': 'Unknown',
                    'remark': '❌ | خطا در پردازش',
                    'protocol': config['type']
                })
        
        self.processed_configs = processed
        
        print(f"\n✅ پردازش کامل!")
        print(f"🎯 کانفیگ‌های پردازش شده: {len(processed)}")
        
        # نمایش آمار پروتکل‌ها
        print("\n📊 آمار پروتکل‌ها:")
        for proto, count in protocol_stats.items():
            print(f"   {proto.upper():<12}: {count} کانفیگ")
        
        return processed
    
    def get_ip_from_domain(self, domain):
        """دریافت IP از دامنه"""
        try:
            # حذف پورت اگر وجود دارد
            domain = domain.split(':')[0]
            ip = socket.gethostbyname(domain)
            return ip
        except:
            return None
    
    def detect_country_intelligent(self, server_address):
        """تشخیص هوشمند کشور با روش‌های مختلف"""
        if not server_address or server_address == 'Unknown':
            return 'US'
        
        # کش کردن برای عملکرد بهتر
        if server_address in self.country_cache:
            return self.country_cache[server_address]
        
        country_code = 'US'  # پیش‌فرض
        
        try:
            # روش 1: تشخیص از TLD دامنه
            if not self.is_ip_address(server_address):
                country_from_domain = self.detect_country_from_domain_tld(server_address)
                if country_from_domain != 'US':
                    self.country_cache[server_address] = country_from_domain
                    return country_from_domain
            
            # روش 2: دریافت IP از دامنه
            ip_address = server_address
            if not self.is_ip_address(server_address):
                ip_address = self.get_ip_from_domain(server_address)
                if not ip_address:
                    self.country_cache[server_address] = 'US'
                    return 'US'
            
            # روش 3: استفاده از API برای تشخیص دقیق
            if self.config_data['settings'].get('enable_ip_api', True):
                country_from_api = self.detect_country_from_ip_api(ip_address)
                if country_from_api:
                    self.country_cache[server_address] = country_from_api
                    return country_from_api
            
        except Exception as e:
            print(f"⚠️ خطا در تشخیص کشور برای {server_address}: {e}")
        
        self.country_cache[server_address] = country_code
        return country_code
    
    def is_ip_address(self, address):
        """بررسی اینکه آیا آدرس IP است"""
        try:
            ipaddress.ip_address(address)
            return True
        except:
            return False
    
    def detect_country_from_domain_tld(self, domain):
        """تشخیص کشور از TLD دامنه"""
        domain_lower = domain.lower()
        
        tld_mapping = {
            'us': 'US', 'com': 'US', 'net': 'US', 'org': 'US',
            'de': 'DE', 'fr': 'FR', 'nl': 'NL', 'tr': 'TR',
            'sg': 'SG', 'jp': 'JP', 'kr': 'KR', 'uk': 'GB',
            'ca': 'CA', 'hk': 'HK', 'ir': 'IR', 'cn': 'CN',
            'ru': 'RU', 'br': 'BR', 'in': 'IN'
        }
        
        # بررسی TLDهای معروف
        for tld, country in tld_mapping.items():
            if domain_lower.endswith('.' + tld):
                return country
        
        # بررسی کلمات کلیدی در دامنه
        keyword_mapping = {
            'US': ['usa', 'us-', 'united', 'american', 'nyc', 'la', 'chicago'],
            'DE': ['de-', 'german', 'deutsch', 'frankfurt', 'berlin'],
            'FR': ['fr-', 'france', 'paris', 'franc'],
            'NL': ['nl-', 'netherlands', 'amsterdam', 'dutch'],
            'TR': ['tr-', 'turkey', 'turk', 'istanbul'],
            'SG': ['sg-', 'singapore'],
            'JP': ['jp-', 'japan', 'tokyo', 'osaka'],
            'KR': ['kr-', 'korea', 'seoul'],
            'HK': ['hk-', 'hongkong', 'hong-kong'],
            'IR': ['ir-', 'iran', 'tehran'],
            'CN': ['cn-', 'china', 'beijing', 'shanghai'],
            'RU': ['ru-', 'russia', 'moscow'],
            'CA': ['ca-', 'canada', 'toronto', 'vancouver']
        }
        
        for country, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in domain_lower:
                    return country
        
        return 'US'
    
    def detect_country_from_ip_api(self, ip_address):
        """تشخیص کشور از API"""
        try:
            # استفاده از ip-api.com (رایگان)
            response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data.get('countryCode', 'US')
            
            # استفاده از api.ipify.org به عنوان fallback
            time.sleep(0.5)  # جلوگیری از rate limit
            response = requests.get(f'https://ipapi.co/{ip_address}/country_code/', timeout=10)
            if response.status_code == 200:
                country = response.text.strip()
                if country and len(country) == 2:
                    return country
                    
        except:
            pass
        
        return None
    
    def process_vmess_config(self, config, country_counters, config_number):
        """پردازش کانفیگ VMess"""
        try:
            config_url = config['raw_config']
            encoded = config_url[8:]  # حذف vmess://
            
            # اضافه کردن padding
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += '=' * padding
            
            decoded = base64.b64decode(encoded).decode('utf-8')
            config_data = json.loads(decoded)
            
            server_address = config_data.get('add', 'Unknown')
            country_code = self.detect_country_intelligent(server_address)
            
            # شمارنده کشور
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            country_config_number = country_counters[country_code]
            
            # تولید ریمارک زیبا
            new_remark = self.generate_beautiful_remark(country_code, country_config_number)
            config_data['ps'] = new_remark
            
            # کد کردن مجدد
            new_encoded = base64.b64encode(
                json.dumps(config_data).encode('utf-8')
            ).decode('utf-8').replace('=', '')
            
            final_url = f"vmess://{new_encoded}"
            
            return {
                **config,
                'final_url': final_url,
                'country': country_code,
                'remark': new_remark,
                'server': server_address,
                'port': config_data.get('port', ''),
                'protocol': 'vmess',
                'config_number': config_number
            }
            
        except Exception as e:
            print(f"⚠️ خطا در پردازش VMess: {e}")
            return None
    
    def process_vless_config(self, config, country_counters, config_number):
        """پردازش کانفیگ VLess (ساده شده)"""
        # برای VLess فعلاً بدون تغییر ریمارک
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'vless',
            'config_number': config_number
        }
    
    def process_trojan_config(self, config, country_counters, config_number):
        """پردازش کانفیگ Trojan"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'trojan',
            'config_number': config_number
        }
    
    def process_ss_config(self, config, country_counters, config_number):
        """پردازش کانفیگ Shadowsocks"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'shadowsocks',
            'config_number': config_number
        }
    
    def process_unknown_config(self, config, country_counters, config_number):
        """پردازش کانفیگ‌های ناشناخته"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'unknown',
            'config_number': config_number
        }
    
    def generate_beautiful_remark(self, country_code, config_number):
        """تولید ریمارک زیبا با ایموجی و فرمت‌بندی"""
        country_info = self.config_data['countries'].get(country_code, '🇺🇸 | آمریکا')
        
        if ' | ' in country_info:
            flag, country_name = country_info.split(' | ', 1)
        else:
            flag, country_name = '🇺🇸', country_code
        
        project_name = self.config_data.get('remark', {}).get('project_name', 'PRX11')
        
        return f"{flag} | {country_name} | {config_number:02d} | {project_name}"
    
    def save_results(self):
        """ذخیره‌سازی نتایج با فرمت‌بندی زیبا"""
        print("\n💾 شروع ذخیره‌سازی نتایج...")
        print("=" * 50)
        
        if not self.processed_configs:
            print("❌ هیچ کانفیگی برای ذخیره‌سازی وجود ندارد")
            return
        
        # آماده‌سازی داده‌ها
        config_urls = [config['final_url'] for config in self.processed_configs]
        subscription_content = "\n".join(config_urls)
        
        # آمار کشورها و پروتکل‌ها
        country_stats = {}
        protocol_stats = {}
        
        for config in self.processed_configs:
            country = config.get('country', 'Unknown')
            protocol = config.get('protocol', 'unknown')
            
            country_stats[country] = country_stats.get(country, 0) + 1
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
        
        # 📁 ذخیره فایل اشتراک اصلی
        with open("output/subscriptions/PRX11-FREE.txt", "w", encoding="utf-8") as f:
            f.write(subscription_content)
        
        # 📊 ذخیره اطلاعات کامل
        full_data = {
            "metadata": {
                "project": "PRX11 V2Ray Config Collector",
                "version": self.config_data['project']['version'],
                "generated_at": datetime.now().isoformat(),
                "total_configs": len(self.processed_configs),
                "country_stats": country_stats,
                "protocol_stats": protocol_stats
            },
            "configs": self.processed_configs
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"output/configs/PRX11_FULL_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        
        # 💎 ذخیره اطلاعات خلاصه
        summary = {
            "last_update": datetime.now().isoformat(),
            "total_configs": len(self.processed_configs),
            "country_stats": country_stats,
            "protocol_stats": protocol_stats,
            "project": "PRX11",
            "subscription_file": "PRX11-FREE.txt"
        }
        
        with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print("✅ ذخیره‌سازی کامل!")
        print(f"📁 فایل اشتراک: PRX11-FREE.txt")
        print(f"🎯 تعداد کانفیگ‌ها: {len(self.processed_configs)}")
        
        # نمایش آمار زیبا
        self.display_beautiful_stats(country_stats, protocol_stats)
    
    def display_beautiful_stats(self, country_stats, protocol_stats):
        """نمایش آمار زیبا"""
        print("\n" + "📊" * 20)
        print("🎯 آمار نهایی پروژه PRX11")
        print("📈" * 20)
        
        print("\n🌍 آمار کشورها:")
        print("-" * 30)
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
            country_name = self.config_data['countries'].get(country, country)
            print(f"   {country_name:<20} : {count:>3} کانفیگ")
        
        print("\n🛡️ آمار پروتکل‌ها:")
        print("-" * 25)
        for protocol, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {protocol.upper():<15} : {count:>3} کانفیگ")
        
        print("\n" + "✅" * 20)
        print(f"🚀 پروژه PRX11 با موفقیت تکمیل شد!")
        print("✅" * 20)
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🎯" * 25)
        print("🛡️  PRX11 V2Ray Config Collector - v3.0")
        print("✨ تشخیص هوشمند کشور | فرمت‌بندی زیبا")
        print("🎯" * 25)
        
        try:
            # ایجاد پوشه‌ها
            self.create_directories()
            
            # جمع‌آوری کانفیگ‌ها
            self.collect_from_all_sources()
            
            if not self.collected_configs:
                print("❌ هیچ کانفیگی یافت نشد!")
                return False
            
            # پردازش کانفیگ‌ها
            self.process_configs()
            
            # ذخیره‌سازی نتایج
            self.save_results()
            
            print(f"\n🔗 لینک اشتراک PRX11:")
            print("   https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-FREE.txt")
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در اجرای پروژه: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """تابع اصلی"""
    collector = PRX11ConfigCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
