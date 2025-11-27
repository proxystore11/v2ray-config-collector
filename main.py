#!/usr/bin/env python3
# 🛡️ PRX11 V2Ray Config Collector - Advanced Version v4.0
# ✨ فیلترسازی پیشرفته | پینگ اتوماتیک | لینک‌های جداگانه

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
import subprocess
import concurrent.futures
import threading

class PRX11AdvancedCollector:
    def __init__(self):
        self.config_data = self.load_config()
        self.collected_configs = []
        self.processed_configs = []
        self.working_configs = []
        self.country_cache = {}
        self.ping_results = {}
        self.lock = threading.Lock()
        
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
                'vmess': ['https://raw.githubusercontent.com/freev2ray/freev2ray/master/README.md'],
                'vless': ['https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/vless.html'],
                'shadowsocks': ['https://raw.githubusercontent.com/arshiacomplus/v2rayExtractor/refs/heads/main/ss.html'],
                'trojan': ['https://raw.githubusercontent.com/v2ray/dist/master/v2ray-configs.txt']
            },
            'settings': {
                'max_configs': 100,
                'timeout': 20,
                'ping_timeout': 5,
                'min_ping_success': 3
            },
            'remark': {
                'format': '{flag} | {country} | {config_number:02d} | {project_name} | {ping}ms',
                'project_name': 'PRX11'
            },
            'subscription_files': {
                'all': 'PRX11-ALL.txt',
                'vmess': 'PRX11-VMESS.txt',
                'vless': 'PRX11-VLESS.txt',
                'shadowsocks': 'PRX11-SS.txt',
                'trojan': 'PRX11-TROJAN.txt',
                'working': 'PRX11-WORKING.txt'
            }
        }
    
    def create_directories(self):
        """ایجاد پوشه‌های لازم"""
        directories = [
            'output/configs', 
            'output/subscriptions',
            'output/logs',
            'output/backups'
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
                    'source': 'classified',
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
    
    def ping_server(self, server_info):
        """پینگ سرور و بازگشت نتیجه"""
        server, port, config_hash = server_info
        
        try:
            # پینگ با استفاده از ping command
            if os.name == 'nt':  # Windows
                cmd = ['ping', '-n', '2', '-w', str(self.config_data['settings']['ping_timeout'] * 1000), server]
            else:  # Linux/Mac
                cmd = ['ping', '-c', '2', '-W', str(self.config_data['settings']['ping_timeout']), server]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.config_data['settings']['ping_timeout'] + 2
            )
            
            if result.returncode == 0:
                # استخراج زمان پینگ از خروجی
                ping_times = re.findall(r'time=([\d.]+)ms', result.stdout)
                if ping_times:
                    avg_ping = sum(float(t) for t in ping_times) / len(ping_times)
                    with self.lock:
                        self.ping_results[config_hash] = {
                            'success': True,
                            'ping': round(avg_ping, 1),
                            'server': server,
                            'port': port
                        }
                    return True, round(avg_ping, 1)
            
            with self.lock:
                self.ping_results[config_hash] = {
                    'success': False,
                    'ping': None,
                    'server': server,
                    'port': port
                }
            return False, None
            
        except Exception as e:
            with self.lock:
                self.ping_results[config_hash] = {
                    'success': False,
                    'ping': None,
                    'server': server,
                    'port': port,
                    'error': str(e)
                }
            return False, None
    
    def test_configs_ping(self):
        """تست پینگ تمام کانفیگ‌ها"""
        print("\n🚀 شروع تست پینگ کانفیگ‌ها...")
        print("=" * 40)
        
        servers_to_ping = []
        
        # استخراج اطلاعات سرور از کانفیگ‌ها
        for config in self.processed_configs:
            server = config.get('server', '')
            port = config.get('port', '')
            
            if server and server != 'Unknown' and not self.is_ip_address(server):
                servers_to_ping.append((server, port, config['hash']))
        
        print(f"🎯 تعداد سرورها برای پینگ: {len(servers_to_ping)}")
        
        # پینگ همزمان با ThreadPoolExecutor
        successful_pings = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.ping_server, server_info) for server_info in servers_to_ping]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    success, ping_time = future.result()
                    if success:
                        successful_pings += 1
                except Exception as e:
                    print(f"⚠️ خطا در پینگ: {e}")
        
        print(f"✅ پینگ موفق: {successful_pings}/{len(servers_to_ping)}")
        
        # بروزرسانی کانفیگ‌ها با اطلاعات پینگ
        for config in self.processed_configs:
            ping_info = self.ping_results.get(config['hash'], {})
            config['ping_success'] = ping_info.get('success', False)
            config['ping_time'] = ping_info.get('ping')
            config['working'] = ping_info.get('success', False)
        
        return successful_pings
    
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
        
        self.processed_configs = processed
        
        print(f"\n✅ پردازش کامل!")
        print(f"🎯 کانفیگ‌های پردازش شده: {len(processed)}")
        
        # نمایش آمار پروتکل‌ها
        print("\n📊 آمار پروتکل‌ها:")
        for proto, count in protocol_stats.items():
            print(f"   {proto.upper():<12}: {count} کانفیگ")
        
        return processed
    
    def is_ip_address(self, address):
        """بررسی اینکه آیا آدرس IP است"""
        try:
            ipaddress.ip_address(address)
            return True
        except:
            return False
    
    def detect_country_intelligent(self, server_address):
        """تشخیص هوشمند کشور"""
        if not server_address or server_address == 'Unknown':
            return 'US'
        
        if server_address in self.country_cache:
            return self.country_cache[server_address]
        
        country_code = 'US'
        
        try:
            # تشخیص از TLD دامنه
            if not self.is_ip_address(server_address):
                country_from_domain = self.detect_country_from_domain_tld(server_address)
                if country_from_domain != 'US':
                    self.country_cache[server_address] = country_from_domain
                    return country_from_domain
            
            # سایر روش‌های تشخیص...
            # (کد تشخیص کشور از نسخه قبلی)
            
        except Exception as e:
            print(f"⚠️ خطا در تشخیص کشور برای {server_address}: {e}")
        
        self.country_cache[server_address] = country_code
        return country_code
    
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
        
        for tld, country in tld_mapping.items():
            if domain_lower.endswith('.' + tld):
                return country
        
        return 'US'
    
    def process_vmess_config(self, config, country_counters, config_number):
        """پردازش کانفیگ VMess"""
        try:
            config_url = config['raw_config']
            encoded = config_url[8:]  # حذف vmess://
            
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += '=' * padding
            
            decoded = base64.b64decode(encoded).decode('utf-8')
            config_data = json.loads(decoded)
            
            server_address = config_data.get('add', 'Unknown')
            country_code = self.detect_country_intelligent(server_address)
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            country_config_number = country_counters[country_code]
            
            # تولید ریمارک با فرمت زیبا
            new_remark = self.generate_beautiful_remark(country_code, country_config_number, "0ms")
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
                'config_number': config_number,
                'ping_time': 0,
                'working': False
            }
            
        except Exception as e:
            print(f"⚠️ خطا در پردازش VMess: {e}")
            return None
    
    def process_vless_config(self, config, country_counters, config_number):
        """پردازش کانفیگ VLess"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], "0ms")
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'vless',
            'config_number': config_number,
            'ping_time': 0,
            'working': False
        }
    
    def process_trojan_config(self, config, country_counters, config_number):
        """پردازش کانفیگ Trojan"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], "0ms")
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'trojan',
            'config_number': config_number,
            'ping_time': 0,
            'working': False
        }
    
    def process_ss_config(self, config, country_counters, config_number):
        """پردازش کانفیگ Shadowsocks"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], "0ms")
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'shadowsocks',
            'config_number': config_number,
            'ping_time': 0,
            'working': False
        }
    
    def process_unknown_config(self, config, country_counters, config_number):
        """پردازش کانفیگ‌های ناشناخته"""
        country_code = 'US'
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], "0ms")
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'unknown',
            'config_number': config_number,
            'ping_time': 0,
            'working': False
        }
    
    def generate_beautiful_remark(self, country_code, config_number, ping_time):
        """تولید ریمارک زیبا"""
        country_info = self.config_data['countries'].get(country_code, '🇺🇸 | آمریکا')
        
        if ' | ' in country_info:
            flag, country_name = country_info.split(' | ', 1)
        else:
            flag, country_name = '🇺🇸', country_code
        
        project_name = self.config_data.get('remark', {}).get('project_name', 'PRX11')
        
        return f"{flag} | {country_name} | {config_number:02d} | {project_name} | {ping_time}"
    
    def update_remarks_with_ping(self):
        """بروزرسانی ریمارک‌ها با اطلاعات پینگ"""
        for config in self.processed_configs:
            if config.get('ping_success'):
                ping_time = config.get('ping_time', 0)
                country_code = config.get('country', 'US')
                
                if country_code not in self.country_counters:
                    self.country_counters[country_code] = 0
                self.country_counters[country_code] += 1
                
                new_remark = self.generate_beautiful_remark(
                    country_code, 
                    self.country_counters[country_code], 
                    f"{ping_time}ms"
                )
                
                if config['protocol'] == 'vmess':
                    try:
                        config_url = config['final_url']
                        encoded = config_url[8:]
                        padding = 4 - len(encoded) % 4
                        if padding != 4:
                            encoded += '=' * padding
                        
                        decoded = base64.b64decode(encoded).decode('utf-8')
                        config_data = json.loads(decoded)
                        config_data['ps'] = new_remark
                        
                        new_encoded = base64.b64encode(
                            json.dumps(config_data).encode('utf-8')
                        ).decode('utf-8').replace('=', '')
                        
                        config['final_url'] = f"vmess://{new_encoded}"
                    except:
                        pass
                
                config['remark'] = new_remark
    
    def save_filtered_subscriptions(self):
        """ذخیره‌سازی لینک‌های ساب جداگانه"""
        print("\n💾 ایجاد لینک‌های ساب جداگانه...")
        print("=" * 50)
        
        # فیلتر کردن کانفیگ‌های کارکرده
        self.working_configs = [c for c in self.processed_configs if c.get('working', False)]
        
        # جدا کردن بر اساس پروتکل
        vmess_configs = [c for c in self.processed_configs if c['protocol'] == 'vmess']
        vless_configs = [c for c in self.processed_configs if c['protocol'] == 'vless']
        ss_configs = [c for c in self.processed_configs if c['protocol'] == 'shadowsocks']
        trojan_configs = [c for c in self.processed_configs if c['protocol'] == 'trojan']
        
        # ایجاد محتوای فایل‌ها
        all_content = "\n".join([c['final_url'] for c in self.processed_configs])
        vmess_content = "\n".join([c['final_url'] for c in vmess_configs])
        vless_content = "\n".join([c['final_url'] for c in vless_configs])
        ss_content = "\n".join([c['final_url'] for c in ss_configs])
        trojan_content = "\n".join([c['final_url'] for c in trojan_configs])
        working_content = "\n".join([c['final_url'] for c in self.working_configs])
        
        # ذخیره فایل‌ها
        subscription_files = self.config_data['subscription_files']
        
        files_to_save = [
            (subscription_files['all'], all_content, "همه کانفیگ‌ها"),
            (subscription_files['vmess'], vmess_content, "فقط VMess"),
            (subscription_files['vless'], vless_content, "فقط VLess"),
            (subscription_files['shadowsocks'], ss_content, "فقط Shadowsocks"),
            (subscription_files['trojan'], trojan_content, "فقط Trojan"),
            (subscription_files['working'], working_content, "کانفیگ‌های کارکرده")
        ]
        
        for filename, content, description in files_to_save:
            with open(f"output/subscriptions/{filename}", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ {description}: {filename}")
    
    def save_detailed_reports(self):
        """ذخیره‌سازی گزارش‌های دقیق"""
        print("\n📊 ایجاد گزارش‌های دقیق...")
        
        # آمار کشورها و پروتکل‌ها
        country_stats = {}
        protocol_stats = {}
        working_stats = {}
        
        for config in self.processed_configs:
            country = config.get('country', 'Unknown')
            protocol = config.get('protocol', 'unknown')
            working = config.get('working', False)
            
            country_stats[country] = country_stats.get(country, 0) + 1
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
            
            if working:
                working_stats[country] = working_stats.get(country, 0) + 1
        
        # گزارش کامل
        full_report = {
            "metadata": {
                "project": "PRX11 V2Ray Config Collector",
                "version": self.config_data['project']['version'],
                "generated_at": datetime.now().isoformat(),
                "total_configs": len(self.processed_configs),
                "working_configs": len(self.working_configs),
                "success_rate": f"{(len(self.working_configs)/len(self.processed_configs)*100):.1f}%" if self.processed_configs else "0%"
            },
            "statistics": {
                "country_stats": country_stats,
                "protocol_stats": protocol_stats,
                "working_stats": working_stats
            },
            "subscription_files": self.config_data['subscription_files'],
            "configs": self.processed_configs
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"output/configs/PRX11_FULL_REPORT_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        # گزارش خلاصه
        summary = {
            "last_update": datetime.now().isoformat(),
            "total_configs": len(self.processed_configs),
            "working_configs": len(self.working_configs),
            "success_rate": f"{(len(self.working_configs)/len(self.processed_configs)*100):.1f}%" if self.processed_configs else "0%",
            "country_stats": country_stats,
            "protocol_stats": protocol_stats,
            "subscription_files": self.config_data['subscription_files']
        }
        
        with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print("✅ گزارش‌های دقیق ذخیره شدند")
        
        # نمایش آمار نهایی
        self.display_final_stats(country_stats, protocol_stats, working_stats)
    
    def display_final_stats(self, country_stats, protocol_stats, working_stats):
        """نمایش آمار نهایی"""
        print("\n" + "🎯" * 25)
        print("📊 آمار نهایی پروژه PRX11")
        print("📈" * 25)
        
        print(f"\n🔢 کل کانفیگ‌ها: {len(self.processed_configs)}")
        print(f"✅ کانفیگ‌های کارکرده: {len(self.working_configs)}")
        print(f"📊 نرخ موفقیت: {(len(self.working_configs)/len(self.processed_configs)*100):.1f}%" if self.processed_configs else "0%")
        
        print("\n🌍 آمار کشورها (کارکرده/کل):")
        print("-" * 40)
        for country, total in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
            working = working_stats.get(country, 0)
            country_name = self.config_data['countries'].get(country, country)
            print(f"   {country_name:<20} : {working:>2}/{total:>2}")
        
        print("\n🛡️ آمار پروتکل‌ها:")
        print("-" * 25)
        for protocol, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {protocol.upper():<15} : {count:>3} کانفیگ")
        
        print("\n📁 لینک‌های ساب ایجاد شده:")
        print("-" * 30)
        for key, filename in self.config_data['subscription_files'].items():
            print(f"   📄 {filename}")
        
        print("\n" + "✅" * 25)
        print("🚀 پروژه PRX11 با موفقیت تکمیل شد!")
        print("✅" * 25)
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🎯" * 30)
        print("🛡️  PRX11 V2Ray Config Collector - v4.0")
        print("✨ فیلترسازی پیشرفته | پینگ اتوماتیک")
        print("🎯" * 30)
        
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
            
            # تست پینگ
            self.test_configs_ping()
            
            # بروزرسانی ریمارک‌ها با پینگ
            self.country_counters = {}
            self.update_remarks_with_ping()
            
            # ذخیره‌سازی لینک‌های ساب
            self.save_filtered_subscriptions()
            
            # ذخیره‌سازی گزارش‌ها
            self.save_detailed_reports()
            
            # نمایش لینک‌ها
            print(f"\n🔗 لینک‌های اشتراک PRX11:")
            base_url = "https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/"
            for key, filename in self.config_data['subscription_files'].items():
                print(f"   📄 {filename}")
                print(f"      {base_url}{filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در اجرای پروژه: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """تابع اصلی"""
    collector = PRX11AdvancedCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
