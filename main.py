#!/usr/bin/env python3
# 🛡️ PRX11 V2Ray Config Collector - Enhanced Version
# ✨ پارسر پیشرفته VLess | عملکرد بهینه

import os
import json
import base64
import requests
import re
import yaml
from datetime import datetime
import hashlib
from urllib.parse import urlparse, parse_qs, unquote

class PRX11EnhancedCollector:
    def __init__(self):
        self.config_data = self.load_config()
        self.collected_configs = []
        self.processed_configs = []
        self.hidden_sources = self.decode_sources()
        
    def load_config(self):
        """بارگذاری تنظیمات از فایل YAML"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری config.yaml: {e}")
            return self.get_default_config()
    
    def decode_sources(self):
        """دیکد کردن منابع مخفی"""
        encoded_sources = [
            "aHR0cHM6Ly90d2lsaWdodC13b29kLTkyMjQubXVqa2R0Z2oud29ya2Vycy5kZXYvYXBpL2NvbmZpZ3M=",
            "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTElWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxJVjItUmF5LnR4dA=="
        ]
        
        sources = []
        for encoded in encoded_sources:
            try:
                decoded = base64.b64decode(encoded).decode('utf-8')
                sources.append(decoded)
            except Exception as e:
                print(f"⚠️ خطا در دیکد منبع: {e}")
        
        return sources
    
    def get_default_config(self):
        """تنظیمات پیش‌فرض"""
        return {
            'project': {'name': 'PRX11', 'version': '4.0.0'},
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
            
            print(f"🌐 دریافت {config_type} از منبع مخفی")
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
    
    def collect_from_hidden_sources(self):
        """جمع‌آوری کانفیگ‌ها از منابع مخفی"""
        print("\n🎯 شروع جمع‌آوری از منابع مخفی...")
        print("=" * 50)
        
        all_configs = []
        
        for url in self.hidden_sources:
            content = self.make_request(url, "مخفی")
            if content:
                configs = self.extract_all_configs(content)
                all_configs.extend(configs)
                print(f"✅ منبع مخفی: {len(configs)} کانفیگ")
        
        # حذف duplicates
        self.collected_configs = self.remove_duplicates(all_configs)
        
        print(f"\n📊 جمع‌آوری کامل!")
        print(f"🎯 کل کانفیگ‌های منحصر به فرد: {len(self.collected_configs)}")
        
        return self.collected_configs
    
    def extract_all_configs(self, text):
        """استخراج همه انواع کانفیگ‌ها از متن"""
        patterns = {
            'vmess': r'vmess://[A-Za-z0-9+/=]+',
            'vless': r'vless://[A-Za-z0-9%\.\-_@?&=#:]+',
            'trojan': r'trojan://[A-Za-z0-9%\.\-_@?&=#:]+',
            'ss': r'ss://[A-Za-z0-9+/=]+'
        }
        
        configs = []
        for config_type, pattern in patterns.items():
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
                    processed_config = self.process_vless_config_enhanced(config, country_counters, i+1)
                elif config['type'] == 'trojan':
                    processed_config = self.process_trojan_config_enhanced(config, country_counters, i+1)
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
                processed.append(self.create_fallback_config(config, i+1, config['type']))
        
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
            
            # اصلاح padding
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += '=' * (4 - missing_padding)
            
            try:
                decoded = base64.b64decode(encoded).decode('utf-8')
                config_data = json.loads(decoded)
            except:
                decoded = base64.b64decode(encoded + '=' * (4 - len(encoded) % 4)).decode('utf-8')
                config_data = json.loads(decoded)
            
            server_address = config_data.get('add', 'Unknown')
            country_code = self.detect_country_advanced(server_address)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            country_config_number = country_counters[country_code]
            
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
            return self.create_fallback_config(config, config_number, 'vmess')
    
    def process_vless_config_enhanced(self, config, country_counters, config_number):
        """پردازش کانفیگ VLess - نسخه پیشرفته"""
        try:
            config_url = config['raw_config']
            
            # پارس کردن URL با روش پیشرفته
            parsed = self.parse_vless_url_enhanced(config_url)
            
            if parsed and parsed.get('server'):
                server_address = parsed['server']
                country_code = self.detect_country_advanced(server_address)
                
                if country_code not in country_counters:
                    country_counters[country_code] = 0
                country_counters[country_code] += 1
                
                new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
                
                # ساخت URL جدید با ریمارک به روز شده
                final_url = self.rebuild_vless_url_enhanced(config_url, new_remark)
                
                return {
                    **config,
                    'final_url': final_url,
                    'country': country_code,
                    'remark': new_remark,
                    'server': server_address,
                    'port': parsed.get('port', '443'),
                    'protocol': 'vless',
                    'config_number': config_number
                }
            else:
                # اگر پارس کردن شکست خورد، از روش ساده استفاده کن
                return self.process_vless_simple(config, country_counters, config_number)
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش VLess: {e}")
            return self.process_vless_simple(config, country_counters, config_number)
    
    def parse_vless_url_enhanced(self, url):
        """پارس کردن URL VLess - نسخه پیشرفته"""
        try:
            # حذف vless://
            url_content = url[8:]
            
            # جدا کردن بخش اصلی و fragment (ریمارک)
            if '#' in url_content:
                main_part, fragment = url_content.split('#', 1)
                remark = unquote(fragment)
            else:
                main_part, remark = url_content, ""
            
            # جدا کردن UUID و سرور
            if '@' in main_part:
                uuid_part, server_part = main_part.split('@', 1)
            else:
                return None
            
            # جدا کردن سرور و پورت
            server_parts = server_part.split(':')
            if len(server_parts) >= 2:
                server_address = server_parts[0]
                port_part = server_parts[1]
                
                # جدا کردن پورت از پارامترها
                if '?' in port_part:
                    port, params = port_part.split('?', 1)
                else:
                    port, params = port_part, ""
            else:
                return None
            
            return {
                'server': server_address,
                'port': port,
                'uuid': uuid_part,
                'params': params,
                'remark': remark,
                'type': 'vless'
            }
        except Exception as e:
            print(f"⚠️ خطا در پارس VLess: {e}")
            return None
    
    def rebuild_vless_url_enhanced(self, original_url, new_remark):
        """بازسازی URL VLess با ریمارک جدید - نسخه پیشرفته"""
        try:
            parsed = self.parse_vless_url_enhanced(original_url)
            if not parsed:
                return original_url
            
            # ساخت URL جدید
            encoded_remark = requests.utils.quote(new_remark)
            final_url = f"vless://{parsed['uuid']}@{parsed['server']}:{parsed['port']}"
            
            if parsed['params']:
                final_url += f"?{parsed['params']}"
            
            final_url += f"#{encoded_remark}"
            
            return final_url
        except:
            return original_url
    
    def process_vless_simple(self, config, country_counters, config_number):
        """پردازش ساده VLess در صورت شکست روش پیشرفته"""
        try:
            config_url = config['raw_config']
            
            # استخراج سرور با regex
            server_match = re.search(r'@([^:#?]+)', config_url)
            if server_match:
                server_address = server_match.group(1)
            else:
                server_address = 'unknown'
            
            country_code = self.detect_country_advanced(server_address)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
            
            # اضافه کردن ریمارک به URL
            if '#' in config_url:
                base_url = config_url.split('#')[0]
                final_url = f"{base_url}#{requests.utils.quote(new_remark)}"
            else:
                final_url = f"{config_url}#{requests.utils.quote(new_remark)}"
            
            return {
                **config,
                'final_url': final_url,
                'country': country_code,
                'remark': new_remark,
                'server': server_address,
                'protocol': 'vless',
                'config_number': config_number
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش ساده VLess: {e}")
            return self.create_fallback_config(config, config_number, 'vless')
    
    def process_trojan_config_enhanced(self, config, country_counters, config_number):
        """پردازش کانفیگ Trojan - نسخه پیشرفته"""
        try:
            config_url = config['raw_config']
            
            # استخراج سرور با regex
            server_match = re.search(r'@([^:#?]+)', config_url)
            if server_match:
                server_address = server_match.group(1)
            else:
                server_address = 'unknown'
            
            country_code = self.detect_country_advanced(server_address)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
            
            # اضافه کردن ریمارک به URL
            if '#' in config_url:
                base_url = config_url.split('#')[0]
                final_url = f"{base_url}#{requests.utils.quote(new_remark)}"
            else:
                final_url = f"{config_url}#{requests.utils.quote(new_remark)}"
            
            return {
                **config,
                'final_url': final_url,
                'country': country_code,
                'remark': new_remark,
                'server': server_address,
                'protocol': 'trojan',
                'config_number': config_number
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش Trojan: {e}")
            return self.create_fallback_config(config, config_number, 'trojan')
    
    def process_ss_config(self, config, country_counters, config_number):
        """پردازش کانفیگ Shadowsocks"""
        try:
            config_url = config['raw_config']
            
            # برای SS، کشور را بر اساس الگو تشخیص می‌دهیم
            country_code = self.detect_country_from_ss(config_url)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code])
            
            return {
                **config,
                'final_url': config_url,
                'country': country_code,
                'remark': new_remark,
                'protocol': 'shadowsocks',
                'config_number': config_number
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش Shadowsocks: {e}")
            return self.create_fallback_config(config, config_number, 'shadowsocks')
    
    def detect_country_from_ss(self, ss_url):
        """تشخیص کشور از URL Shadowsocks"""
        try:
            # استخراج سرور با regex
            server_match = re.search(r'@([^:#?]+)', ss_url)
            if server_match:
                server_address = server_match.group(1)
                return self.detect_country_advanced(server_address)
            return 'US'
        except:
            return 'US'
    
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
    
    def create_fallback_config(self, config, config_number, protocol):
        """ایجاد کانفیگ fallback در صورت خطا"""
        country_code = 'US'
        new_remark = self.generate_beautiful_remark(country_code, config_number)
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': f"{new_remark} (Fallback)",
            'protocol': protocol,
            'config_number': config_number,
            'status': 'error'
        }
    
    def detect_country_advanced(self, server_address):
        """تشخیص پیشرفته کشور"""
        if not server_address or server_address == 'Unknown' or server_address == 'unknown':
            return 'US'
        
        countries_config = self.config_data.get('countries', {})
        
        # اولویت 1: جستجو در TLD
        tld_match = re.search(r'\.([a-z]{2,3})$', server_address.lower())
        if tld_match:
            tld = tld_match.group(1)
            for country_code in countries_config.keys():
                if tld == country_code.lower():
                    return country_code
        
        # اولویت 2: کلمات کلیدی در دامنه
        server_lower = server_address.lower()
        for country_code, country_name in countries_config.items():
            country_keywords = [
                country_code.lower(),
                country_name.split('|')[1].strip().lower() if '|' in country_name else country_name.lower()
            ]
            
            for keyword in country_keywords:
                if keyword in server_lower:
                    return country_code
        
        return 'US'
    
    def generate_beautiful_remark(self, country_code, config_number):
        """تولید ریمارک زیبا"""
        countries_config = self.config_data.get('countries', {})
        country_info = countries_config.get(country_code, '🇺🇸 | آمریکا')
        
        if ' | ' in country_info:
            flag, country_name = country_info.split(' | ', 1)
        else:
            flag, country_name = '🇺🇸', country_info
        
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
            "subscription_files": self.config_data['subscription_files'],
            "sources_count": len(self.hidden_sources)
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
        print(f"🔗 تعداد منابع: {len(self.hidden_sources)}")
        
        print("\n🌍 آمار کشورها:")
        print("-" * 30)
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            countries_config = self.config_data.get('countries', {})
            country_name = countries_config.get(country, country)
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
        print("🔒 منابع تغذیه: مخفی (Base64)")
        print("✅" * 20)
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🎯" * 25)
        print("🛡️  PRX11 V2Ray Config Collector - Enhanced Version")
        print("✨ پارسر پیشرفته VLess | عملکرد بهینه")
        print("🎯" * 25)
        
        try:
            # ایجاد پوشه‌ها
            self.create_directories()
            
            # جمع‌آوری کانفیگ‌ها از منابع مخفی
            self.collect_from_hidden_sources()
            
            if not self.collected_configs:
                print("❌ هیچ کانفیگی از منابع مخفی یافت نشد!")
                return False
            
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
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در اجرای پروژه: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """تابع اصلی"""
    collector = PRX11EnhancedCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
