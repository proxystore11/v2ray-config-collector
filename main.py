#!/usr/bin/env python3
# 🛡️ PRX11 V2Ray Config Collector - Simple & Reliable Version
# ✨ فیلترسازی بدون پینگ | عملکرد مطمئن

import os
import json
import base64
import requests
import re
import yaml
from datetime import datetime
import hashlib

class PRX11SimpleCollector:
    def __init__(self):
        self.config_data = self.load_config()
        self.collected_configs = []
        self.processed_configs = []
        
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
            'project': {'name': 'PRX11', 'version': '4.0.0'},
            'sources': {
                'vmess': [
                    'https://raw.githubusercontent.com/freev2ray/freev2ray/master/README.md',
                    'https://raw.githubusercontent.com/eliv2-hub/ELiV2-RAY/refs/heads/main/Channel-ELiV2-Ray.txt',
                    'https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/vmess_iran.txt'
                ],
                'vless': [
                    'https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/vless.html',
                    'https://raw.githubusercontent.com/Farid-Karimi/Config-Collector/main/mixed_iran.txt'
                ],
                'shadowsocks': [
                    'https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/ss.html',
                    'https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/mixarshia_ss'
                ],
                'trojan': [
                    'https://raw.githubusercontent.com/v2ray/dist/master/v2ray-configs.txt'
                ]
            },
            'settings': {
                'max_configs': 100,
                'timeout': 30
            },
            'remark': {
                'format': '{flag} | {country} | {config_number:02d} | {project_name}',
                'project_name': 'PRX11'
            },
            'subscription_files': {
                'all': 'PRX11-ALL.txt',
                'vmess': 'PRX11-VMESS.txt',
                'vless': 'PRX11-VLESS.txt',
                'shadowsocks': 'PRX11-SS.txt',
                'trojan': 'PRX11-TROJAN.txt'
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            print(f"🌐 دریافت {config_type} از: {url}")
            response = requests.get(
                url, 
                headers=headers, 
                timeout=self.config_data['settings']['timeout']
            )
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"❌ خطا در دریافت {config_type}: {e}")
            return None
    
    def collect_from_all_sources(self):
        """جمع‌آوری کانفیگ‌ها از تمام منابع"""
        print("\n🎯 شروع جمع‌آوری از منابع...")
        print("=" * 50)
        
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
        """استخراج کانفیگ‌ها از متن"""
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
                    'protocol': config_type
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
        """پردازش کانفیگ‌ها"""
        print("\n🔄 شروع پردازش کانفیگ‌ها...")
        print("=" * 40)
        
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
                    'remark': '❌ خطا در پردازش',
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
            country_code = self.detect_country_simple(server_address)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            country_config_number = country_counters[country_code]
            
            # تولید ریمارک زیبا
            new_remark = self.generate_beautiful_remark(country_code, country_config_number)
            config_data['ps'] = new_remark
            
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
            # بازگشت به نسخه اصلی در صورت خطا
            return {
                **config,
                'final_url': config['raw_config'],
                'country': 'Unknown',
                'remark': 'VMess - Unchanged',
                'protocol': 'vmess',
                'config_number': config_number
            }
    
    def process_vless_config(self, config, country_counters, config_number):
        """پردازش کانفیگ VLess"""
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
    
    def detect_country_simple(self, server_address):
        """تشخیص ساده کشور از دامنه"""
        if not server_address or server_address == 'Unknown':
            return 'US'
        
        server_lower = server_address.lower()
        
        # تشخیص از TLD
        tld_mapping = {
            'us': 'US', 'com': 'US', 'net': 'US', 'org': 'US',
            'de': 'DE', 'fr': 'FR', 'nl': 'NL', 'tr': 'TR',
            'sg': 'SG', 'jp': 'JP', 'kr': 'KR', 'uk': 'GB',
            'ca': 'CA', 'hk': 'HK', 'ir': 'IR', 'cn': 'CN',
            'ru': 'RU', 'br': 'BR', 'in': 'IN'
        }
        
        for tld, country in tld_mapping.items():
            if server_lower.endswith('.' + tld):
                return country
        
        # تشخیص از کلمات کلیدی
        keyword_mapping = {
            'US': ['usa', 'us-', 'united', 'american', 'nyc', 'la'],
            'DE': ['de-', 'german', 'deutsch', 'frankfurt'],
            'FR': ['fr-', 'france', 'paris'],
            'NL': ['nl-', 'netherlands', 'amsterdam'],
            'TR': ['tr-', 'turkey', 'istanbul'],
            'SG': ['sg-', 'singapore'],
            'JP': ['jp-', 'japan', 'tokyo'],
            'KR': ['kr-', 'korea', 'seoul'],
            'HK': ['hk-', 'hongkong'],
            'IR': ['ir-', 'iran', 'tehran']
        }
        
        for country, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in server_lower:
                    return country
        
        return 'US'
    
    def generate_beautiful_remark(self, country_code, config_number):
        """تولید ریمارک زیبا"""
        countries = {
            'US': '🇺🇸 | آمریکا', 'DE': '🇩🇪 | آلمان', 'FR': '🇫🇷 | فرانسه',
            'NL': '🇳🇱 | هلند', 'TR': '🇹🇷 | ترکیه', 'SG': '🇸🇬 | سنگاپور',
            'JP': '🇯🇵 | ژاپن', 'KR': '🇰🇷 | کره', 'GB': '🇬🇧 | انگلیس',
            'CA': '🇨🇦 | کانادا', 'HK': '🇭🇰 | هنگ‌کنگ', 'IR': '🇮🇷 | ایران',
            'CN': '🇨🇳 | چین', 'RU': '🇷🇺 | روسیه', 'BR': '🇧🇷 | برزیل',
            'IN': '🇮🇳 | هند'
        }
        
        country_info = countries.get(country_code, '🇺🇸 | آمریکا')
        
        if ' | ' in country_info:
            flag, country_name = country_info.split(' | ', 1)
        else:
            flag, country_name = '🇺🇸', country_code
        
        project_name = self.config_data.get('remark', {}).get('project_name', 'PRX11')
        
        return f"{flag} | {country_name} | {config_number:02d} | {project_name}"
    
    def save_subscription_files(self):
        """ذخیره‌سازی لینک‌های ساب جداگانه"""
        print("\n💾 ایجاد لینک‌های ساب جداگانه...")
        print("=" * 40)
        
        if not self.processed_configs:
            print("❌ هیچ کانفیگی برای ذخیره‌سازی وجود ندارد")
            return False
        
        # جدا کردن بر اساس پروتکل
        vmess_configs = [c for c in self.processed_configs if c['protocol'] == 'vmess']
        vless_configs = [c for c in self.processed_configs if c['protocol'] == 'vless']
        ss_configs = [c for c in self.processed_configs if c['protocol'] == 'shadowsocks']
        trojan_configs = [c for c in self.processed_configs if c['protocol'] == 'trojan']
        
        print(f"📊 آمار کانفیگ‌ها:")
        print(f"   VMess: {len(vmess_configs)}")
        print(f"   VLess: {len(vless_configs)}") 
        print(f"   Shadowsocks: {len(ss_configs)}")
        print(f"   Trojan: {len(trojan_configs)}")
        
        # ایجاد محتوای فایل‌ها
        all_content = "\n".join([c['final_url'] for c in self.processed_configs])
        vmess_content = "\n".join([c['final_url'] for c in vmess_configs])
        vless_content = "\n".join([c['final_url'] for c in vless_configs])
        ss_content = "\n".join([c['final_url'] for c in ss_configs])
        trojan_content = "\n".join([c['final_url'] for c in trojan_configs])
        
        # ذخیره فایل‌ها
        subscription_files = self.config_data['subscription_files']
        
        files_to_save = [
            (subscription_files['all'], all_content, "همه کانفیگ‌ها"),
            (subscription_files['vmess'], vmess_content, "فقط VMess"),
            (subscription_files['vless'], vless_content, "فقط VLess"),
            (subscription_files['shadowsocks'], ss_content, "فقط Shadowsocks"),
            (subscription_files['trojan'], trojan_content, "فقط Trojan")
        ]
        
        success_count = 0
        for filename, content, description in files_to_save:
            try:
                with open(f"output/subscriptions/{filename}", "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ {description}: {filename} ({len(content.splitlines())} کانفیگ)")
                success_count += 1
            except Exception as e:
                print(f"❌ خطا در ذخیره {filename}: {e}")
        
        return success_count > 0
    
    def save_reports(self):
        """ذخیره‌سازی گزارش‌ها"""
        print("\n📊 ایجاد گزارش‌های آماری...")
        
        # آمار کشورها و پروتکل‌ها
        country_stats = {}
        protocol_stats = {}
        
        for config in self.processed_configs:
            country = config.get('country', 'Unknown')
            protocol = config.get('protocol', 'unknown')
            
            country_stats[country] = country_stats.get(country, 0) + 1
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
        
        # گزارش خلاصه
        summary = {
            "last_update": datetime.now().isoformat(),
            "total_configs": len(self.processed_configs),
            "country_stats": country_stats,
            "protocol_stats": protocol_stats,
            "subscription_files": self.config_data['subscription_files']
        }
        
        try:
            with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print("✅ گزارش خلاصه ذخیره شد")
        except Exception as e:
            print(f"❌ خطا در ذخیره گزارش: {e}")
        
        # نمایش آمار نهایی
        self.display_final_stats(country_stats, protocol_stats)
    
    def display_final_stats(self, country_stats, protocol_stats):
        """نمایش آمار نهایی"""
        print("\n" + "🎯" * 20)
        print("📊 آمار نهایی پروژه PRX11")
        print("📈" * 20)
        
        print(f"\n🔢 کل کانفیگ‌ها: {len(self.processed_configs)}")
        
        print("\n🌍 آمار کشورها:")
        print("-" * 30)
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            countries = {
                'US': '🇺🇸 | آمریکا', 'DE': '🇩🇪 | آلمان', 'FR': '🇫🇷 | فرانسه',
                'NL': '🇳🇱 | هلند', 'TR': '🇹🇷 | ترکیه', 'SG': '🇸🇬 | سنگاپور',
                'JP': '🇯🇵 | ژاپن', 'KR': '🇰🇷 | کره', 'GB': '🇬🇧 | انگلیس',
                'HK': '🇭🇰 | هنگ‌کنگ', 'IR': '🇮🇷 | ایران'
            }
            country_name = countries.get(country, country)
            print(f"   {country_name:<20} : {count:>3} کانفیگ")
        
        print("\n🛡️ آمار پروتکل‌ها:")
        print("-" * 25)
        for protocol, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {protocol.upper():<15} : {count:>3} کانفیگ")
        
        print("\n📁 لینک‌های ساب ایجاد شده:")
        print("-" * 30)
        for key, filename in self.config_data['subscription_files'].items():
            print(f"   📄 {filename}")
        
        print("\n" + "✅" * 20)
        print("🚀 پروژه PRX11 با موفقیت تکمیل شد!")
        print("✅" * 20)
    
    def create_sample_configs(self):
        """ایجاد کانفیگ‌های نمونه برای تست"""
        print("🔧 ایجاد کانفیگ‌های نمونه برای تست...")
        
        sample_configs = [
            {
                'raw_config': 'vmess://ewoidiI6ICIyIiwKInBzIjogIkRlbW8gVk1lc3MgMSIsCiJhZGQiOiAidXMtc2VydmVyMS5jb20iLAoicG9ydCI6ICI4MDgwIiwKImlkIjogIjEyMzQ1Njc4OTAiLAoiYWlkIjogIjAiLAoibmV0IjogInRjcCIsCiJ0eXBlIjogIm5vbmUiLAoiaG9zdCI6ICIiLAoicGF0aCI6ICIiLAoidGxzIjogIiIKfQ==',
                'hash': 'sample_vmess_1',
                'type': 'vmess',
                'protocol': 'vmess'
            },
            {
                'raw_config': 'vless://12345678-1234-1234-1234-123456789012@us-server2.com:443?type=tcp&security=tls#Demo%20VLess%201',
                'hash': 'sample_vless_1', 
                'type': 'vless',
                'protocol': 'vless'
            },
            {
                'raw_config': 'ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@sg-server1.com:8388#Demo%20SS%201',
                'hash': 'sample_ss_1',
                'type': 'ss',
                'protocol': 'shadowsocks'
            }
        ]
        
        self.collected_configs = sample_configs
        print("✅ کانفیگ‌های نمونه ایجاد شدند")
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🎯" * 25)
        print("🛡️  PRX11 V2Ray Config Collector - Simple Version")
        print("✨ فیلترسازی مطمئن | بدون پینگ")
        print("🎯" * 25)
        
        try:
            # ایجاد پوشه‌ها
            self.create_directories()
            
            # جمع‌آوری کانفیگ‌ها
            self.collect_from_all_sources()
            
            if not self.collected_configs:
                print("⚠️ هیچ کانفیگی یافت نشد! ایجاد نمونه‌های تست...")
                self.create_sample_configs()
            
            # پردازش کانفیگ‌ها
            self.process_configs()
            
            if not self.processed_configs:
                print("❌ هیچ کانفیگی پردازش نشد!")
                return False
            
            # ذخیره‌سازی لینک‌های ساب
            success = self.save_subscription_files()
            if not success:
                print("❌ خطا در ذخیره‌سازی فایل‌ها!")
                return False
            
            # ذخیره‌سازی گزارش‌ها
            self.save_reports()
            
            # نمایش لینک‌ها
            print(f"\n🔗 لینک‌های اشتراک PRX11:")
            base_url = "https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/"
            for key, filename in self.config_data['subscription_files'].items():
                print(f"   📄 {base_url}{filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در اجرای پروژه: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """تابع اصلی"""
    collector = PRX11SimpleCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
