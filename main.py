#!/usr/bin/env python3
# 🛡️ PRX11 V2Ray Config Collector - TCP Ping Version
# ✨ پینگ TCP | تشخیص کشور از آدرس

import os
import json
import base64
import requests
import re
import yaml
from datetime import datetime
import hashlib
import socket
import time
import concurrent.futures

class PRX11TCPCollector:
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
            "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2VsaXYyLWh1Yi9FTGlWMi1SQVkvcmVmcy9oZWFkcy9tYWluL0NoYW5uZWwtRUxpVjItUmF5LnR4dA=="
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
            'project': {'name': 'PRX11', 'version': '4.3.0'},
            'settings': {
                'max_configs': 100,
                'timeout': 30,
                'ping_timeout': 5,
                'max_workers': 10
            },
            'remark': {
                'format': '{flag} | {country} | {config_number:02d} | {ping}ms | {project_name}',
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
    
    def tcp_ping(self, host, port):
        """پینگ TCP برای بررسی وضعیت سرور"""
        if not host or host in ['unknown', 'Unknown']:
            return None
        
        try:
            # تبدیل host به IP (اختیاری)
            try:
                ip = socket.gethostbyname(host)
            except:
                ip = host
            
            start_time = time.time()
            
            # ایجاد socket و اتصال TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config_data['settings']['ping_timeout'])
            
            result = sock.connect_ex((ip, int(port)))
            end_time = time.time()
            
            sock.close()
            
            if result == 0:
                ping_time = round((end_time - start_time) * 1000, 2)  # به میلی‌ثانیه
                return ping_time
            else:
                return None
                
        except Exception as e:
            return None
    
    def extract_server_info(self, config):
        """استخراج اطلاعات سرور و پورت از کانفیگ"""
        try:
            if config['type'] == 'vmess':
                # دیکد کردن VMess
                encoded = config['raw_config'][8:]  # حذف vmess://
                missing_padding = len(encoded) % 4
                if missing_padding:
                    encoded += '=' * (4 - missing_padding)
                
                try:
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    config_data = json.loads(decoded)
                    server = config_data.get('add', 'unknown')
                    port = config_data.get('port', '443')
                    return server, port
                except:
                    return 'unknown', '443'
                
            elif config['type'] == 'vless':
                # استخراج از VLess
                match = re.search(r'@([^:#?]+):(\d+)', config['raw_config'])
                if match:
                    server = match.group(1)
                    port = match.group(2)
                    return server, port
                else:
                    return 'unknown', '443'
                
            elif config['type'] == 'trojan':
                # استخراج از Trojan
                match = re.search(r'@([^:#?]+):(\d+)', config['raw_config'])
                if match:
                    server = match.group(1)
                    port = match.group(2)
                    return server, port
                else:
                    return 'unknown', '443'
                
            elif config['type'] == 'ss':
                # برای Shadowsocks نیاز به decode پیچیده‌تر دارد
                return 'unknown', '443'
                
            else:
                return 'unknown', '443'
                
        except Exception as e:
            return 'unknown', '443'
    
    def process_configs_with_tcp_ping(self):
        """پردازش کانفیگ‌ها با پینگ TCP"""
        print("\n🔄 شروع پردازش کانفیگ‌ها با پینگ TCP...")
        print("=" * 50)
        
        processed = []
        country_counters = {}
        protocol_stats = {}
        
        max_configs = self.config_data['settings']['max_configs']
        max_workers = self.config_data['settings']['max_workers']
        
        # استخراج اطلاعات سرورها برای پینگ گروهی
        servers_to_ping = []
        for i, config in enumerate(self.collected_configs[:max_configs]):
            server, port = self.extract_server_info(config)
            if server and server not in ['unknown', 'Unknown']:
                servers_to_ping.append((i, server, port))
        
        print(f"🌐 پینگ TCP برای {len(servers_to_ping)} سرور...")
        
        # پینگ TCP همزمان
        ping_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_server = {
                executor.submit(self.tcp_ping, server, port): (idx, server, port) 
                for idx, server, port in servers_to_ping
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_server):
                idx, server, port = future_to_server[future]
                try:
                    ping_value = future.result()
                    ping_results[idx] = ping_value
                    completed += 1
                    
                    if ping_value:
                        print(f"✅ {server}:{port} - {ping_value}ms")
                    else:
                        print(f"❌ {server}:{port} - timeout")
                    
                    if completed % 10 == 0:
                        print(f"📡 پینگ شده: {completed}/{len(servers_to_ping)}")
                        
                except Exception as e:
                    print(f"⚠️ خطا در پینگ TCP {server}:{port}: {e}")
                    ping_results[idx] = None
        
        # پردازش نهایی کانفیگ‌ها
        for i, config in enumerate(self.collected_configs[:max_configs]):
            try:
                # آمار پروتکل
                proto = config['type']
                protocol_stats[proto] = protocol_stats.get(proto, 0) + 1
                
                # استخراج اطلاعات سرور برای تشخیص کشور
                server, port = self.extract_server_info(config)
                country_code = self.detect_country_from_server(server, config)
                
                if config['type'] == 'vmess':
                    processed_config = self.process_vmess_config(config, country_counters, i+1, ping_results.get(i), country_code)
                elif config['type'] == 'vless':
                    processed_config = self.process_vless_config(config, country_counters, i+1, ping_results.get(i), country_code)
                elif config['type'] == 'trojan':
                    processed_config = self.process_trojan_config(config, country_counters, i+1, ping_results.get(i), country_code)
                elif config['type'] == 'ss':
                    processed_config = self.process_ss_config(config, country_counters, i+1, ping_results.get(i), country_code)
                else:
                    processed_config = self.process_unknown_config(config, country_counters, i+1, ping_results.get(i), country_code)
                
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
    
    def detect_country_from_server(self, server_address, config):
        """تشخیص کشور از آدرس سرور و اطلاعات کانفیگ"""
        if not server_address or server_address in ['unknown', 'Unknown']:
            # اگر سرور unknown است، از اطلاعات کانفیگ استفاده کن
            return self.detect_country_from_config(config)
        
        countries_config = self.config_data.get('countries', {})
        
        # اولویت ۱: تشخیص از TLD دامنه
        tld_match = re.search(r'\.([a-z]{2,3})$', server_address.lower())
        if tld_match:
            tld = tld_match.group(1)
            tld_to_country = {
                'us': 'US', 'com': 'US', 'net': 'US', 'org': 'US',
                'ir': 'IR', 'de': 'DE', 'fr': 'FR', 'nl': 'NL',
                'tr': 'TR', 'sg': 'SG', 'jp': 'JP', 'kr': 'KR',
                'uk': 'GB', 'ca': 'CA', 'hk': 'HK', 'cn': 'CN',
                'ru': 'RU', 'br': 'BR', 'in': 'IN'
            }
            if tld in tld_to_country:
                return tld_to_country[tld]
        
        # اولویت ۲: تشخیص از کلمات کلیدی در دامنه
        server_lower = server_address.lower()
        keyword_mapping = {
            'US': ['usa', 'us-', 'united', 'american', 'nyc', 'la', 'texas', 'miami'],
            'IR': ['ir-', 'iran', 'tehran', 'persian', 'persia'],
            'DE': ['de-', 'german', 'deutsch', 'frankfurt', 'berlin'],
            'FR': ['fr-', 'france', 'paris'],
            'NL': ['nl-', 'netherlands', 'amsterdam'],
            'TR': ['tr-', 'turkey', 'istanbul'],
            'SG': ['sg-', 'singapore'],
            'JP': ['jp-', 'japan', 'tokyo'],
            'KR': ['kr-', 'korea', 'seoul'],
            'HK': ['hk-', 'hongkong'],
            'RU': ['ru-', 'russia', 'moscow'],
            'BR': ['br-', 'brazil', 'sao paulo'],
            'IN': ['in-', 'india', 'mumbai']
        }
        
        for country, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in server_lower:
                    return country
        
        # اگر از سرور تشخیص داده نشد، از کانفیگ استفاده کن
        return self.detect_country_from_config(config)
    
    def detect_country_from_config(self, config):
        """تشخیص کشور از اطلاعات کانفیگ"""
        try:
            if config['type'] == 'vmess':
                # دیکد کردن VMess و بررسی remark
                encoded = config['raw_config'][8:]
                missing_padding = len(encoded) % 4
                if missing_padding:
                    encoded += '=' * (4 - missing_padding)
                
                decoded = base64.b64decode(encoded).decode('utf-8')
                config_data = json.loads(decoded)
                remark = config_data.get('ps', '').lower()
                
                # تشخیص از remark
                if 'us' in remark or 'usa' in remark or 'america' in remark:
                    return 'US'
                elif 'ir' in remark or 'iran' in remark:
                    return 'IR'
                elif 'de' in remark or 'german' in remark:
                    return 'DE'
                elif 'fr' in remark or 'france' in remark:
                    return 'FR'
                elif 'tr' in remark or 'turkey' in remark:
                    return 'TR'
                elif 'sg' in remark or 'singapore' in remark:
                    return 'SG'
                elif 'jp' in remark or 'japan' in remark:
                    return 'JP'
                elif 'kr' in remark or 'korea' in remark:
                    return 'KR'
                elif 'ru' in remark or 'russia' in remark:
                    return 'RU'
                elif 'br' in remark or 'brazil' in remark:
                    return 'BR'
                elif 'in' in remark or 'india' in remark:
                    return 'IN'
                    
        except:
            pass
        
        return 'US'  # پیش‌فرض
    
    def process_vmess_config(self, config, country_counters, config_number, ping_value, country_code):
        """پردازش کانفیگ VMess با پینگ TCP"""
        try:
            config_url = config['raw_config']
            encoded = config_url[8:]
            
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
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            country_config_number = country_counters[country_code]
            
            new_remark = self.generate_beautiful_remark(country_code, country_config_number, ping_value)
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
                'ping': ping_value,
                'status': 'working' if ping_value and ping_value < 2000 else 'unknown'
            }
            
        except Exception as e:
            print(f"⚠️ خطا در پردازش VMess: {e}")
            return self.create_fallback_config(config, config_number, 'vmess')
    
    def process_vless_config(self, config, country_counters, config_number, ping_value, country_code):
        """پردازش کانفیگ VLess با پینگ TCP"""
        try:
            config_url = config['raw_config']
            
            server_match = re.search(r'@([^:#?]+)', config_url)
            if server_match:
                server_address = server_match.group(1)
            else:
                server_address = 'unknown'
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], ping_value)
            
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
                'config_number': config_number,
                'ping': ping_value,
                'status': 'working' if ping_value and ping_value < 2000 else 'unknown'
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش VLess: {e}")
            return self.create_fallback_config(config, config_number, 'vless')
    
    def process_trojan_config(self, config, country_counters, config_number, ping_value, country_code):
        """پردازش کانفیگ Trojan با پینگ TCP"""
        try:
            config_url = config['raw_config']
            
            server_match = re.search(r'@([^:#?]+)', config_url)
            if server_match:
                server_address = server_match.group(1)
            else:
                server_address = 'unknown'
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], ping_value)
            
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
                'config_number': config_number,
                'ping': ping_value,
                'status': 'working' if ping_value and ping_value < 2000 else 'unknown'
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش Trojan: {e}")
            return self.create_fallback_config(config, config_number, 'trojan')
    
    def process_ss_config(self, config, country_counters, config_number, ping_value, country_code):
        """پردازش کانفیگ Shadowsocks با پینگ TCP"""
        try:
            config_url = config['raw_config']
            
            if country_code not in country_counters:
                country_counters[country_code] = 0
            country_counters[country_code] += 1
            
            new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], ping_value)
            
            return {
                **config,
                'final_url': config_url,
                'country': country_code,
                'remark': new_remark,
                'protocol': 'shadowsocks',
                'config_number': config_number,
                'ping': ping_value,
                'status': 'working' if ping_value and ping_value < 2000 else 'unknown'
            }
                
        except Exception as e:
            print(f"⚠️ خطا در پردازش Shadowsocks: {e}")
            return self.create_fallback_config(config, config_number, 'shadowsocks')
    
    def process_unknown_config(self, config, country_counters, config_number, ping_value, country_code):
        """پردازش کانفیگ‌های ناشناخته با پینگ TCP"""
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        
        new_remark = self.generate_beautiful_remark(country_code, country_counters[country_code], ping_value)
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': new_remark,
            'protocol': 'unknown',
            'config_number': config_number,
            'ping': ping_value,
            'status': 'unknown'
        }
    
    def create_fallback_config(self, config, config_number, protocol):
        """ایجاد کانفیگ fallback در صورت خطا"""
        country_code = 'US'
        new_remark = self.generate_beautiful_remark(country_code, config_number, None)
        
        return {
            **config,
            'final_url': config['raw_config'],
            'country': country_code,
            'remark': f"{new_remark} (Fallback)",
            'protocol': protocol,
            'config_number': config_number,
            'ping': None,
            'status': 'error'
        }
    
    def generate_beautiful_remark(self, country_code, config_number, ping_value):
        """تولید ریمارک زیبا با اطلاعات پینگ"""
        countries_config = self.config_data.get('countries', {})
        country_info = countries_config.get(country_code, '🇺🇸 | آمریکا')
        
        if ' | ' in country_info:
            flag, country_name = country_info.split(' | ', 1)
        else:
            flag, country_name = '🇺🇸', country_info
        
        project_name = self.config_data.get('remark', {}).get('project_name', 'PRX11')
        
        if ping_value:
            return f"{flag} | {country_name} | {config_number:02d} | {ping_value}ms | {project_name}"
        else:
            return f"{flag} | {country_name} | {config_number:02d} | ❓ms | {project_name}"
    
    def save_subscription_files(self):
        """ذخیره‌سازی لینک‌های ساب جداگانه"""
        print("\n💾 ایجاد لینک‌های ساب جداگانه...")
        print("=" * 40)
        
        if not self.processed_configs:
            print("❌ هیچ کانفیگی برای ذخیره‌سازی وجود ندارد")
            return False
        
        # جدا کردن بر اساس پروتکل و وضعیت
        vmess_configs = [c for c in self.processed_configs if c['protocol'] == 'vmess']
        vless_configs = [c for c in self.processed_configs if c['protocol'] == 'vless']
        ss_configs = [c for c in self.processed_configs if c['protocol'] == 'shadowsocks']
        trojan_configs = [c for c in self.processed_configs if c['protocol'] == 'trojan']
        working_configs = [c for c in self.processed_configs if c.get('status') == 'working']
        
        print(f"📊 آمار کانفیگ‌ها:")
        print(f"   VMess: {len(vmess_configs)}")
        print(f"   VLess: {len(vless_configs)}") 
        print(f"   Shadowsocks: {len(ss_configs)}")
        print(f"   Trojan: {len(trojan_configs)}")
        print(f"   کارکرده: {len(working_configs)}")
        
        # ایجاد محتوای فایل‌ها
        all_content = "\n".join([c['final_url'] for c in self.processed_configs])
        vmess_content = "\n".join([c['final_url'] for c in vmess_configs])
        vless_content = "\n".join([c['final_url'] for c in vless_configs])
        ss_content = "\n".join([c['final_url'] for c in ss_configs])
        trojan_content = "\n".join([c['final_url'] for c in trojan_configs])
        working_content = "\n".join([c['final_url'] for c in working_configs])
        
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
        
        # آمار کشورها، پروتکل‌ها و پینگ
        country_stats = {}
        protocol_stats = {}
        ping_stats = {'working': 0, 'unknown': 0, 'error': 0}
        
        for config in self.processed_configs:
            country = config.get('country', 'Unknown')
            protocol = config.get('protocol', 'unknown')
            status = config.get('status', 'unknown')
            
            country_stats[country] = country_stats.get(country, 0) + 1
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
            ping_stats[status] = ping_stats.get(status, 0) + 1
        
        # گزارش خلاصه
        summary = {
            "last_update": datetime.now().isoformat(),
            "total_configs": len(self.processed_configs),
            "country_stats": country_stats,
            "protocol_stats": protocol_stats,
            "ping_stats": ping_stats,
            "subscription_files": self.config_data['subscription_files'],
            "sources_count": len(self.hidden_sources),
            "ping_method": "TCP Socket"
        }
        
        try:
            with open("output/configs/PRX11_SUMMARY.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print("✅ گزارش خلاصه ذخیره شد")
        except Exception as e:
            print(f"❌ خطا در ذخیره گزارش: {e}")
        
        # نمایش آمار نهایی
        self.display_final_stats(country_stats, protocol_stats, ping_stats)
    
    def display_final_stats(self, country_stats, protocol_stats, ping_stats):
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
        
        print("\n📡 آمار پینگ TCP:")
        print("-" * 25)
        print(f"   ✅ کارکرده: {ping_stats.get('working', 0)} کانفیگ")
        print(f"   ❓ ناشناخته: {ping_stats.get('unknown', 0)} کانفیگ")
        print(f"   ❌ خطا: {ping_stats.get('error', 0)} کانفیگ")
        
        print("\n📁 لینک‌های ساب ایجاد شده:")
        print("-" * 30)
        for key, filename in self.config_data['subscription_files'].items():
            print(f"   📄 {filename}")
        
        print("\n" + "✅" * 20)
        print("🚀 پروژه PRX11 با موفقیت تکمیل شد!")
        print("📡 پینگ TCP: فعال")
        print("🌍 تشخیص کشور: از آدرس و کانفیگ")
        print("🔒 منابع تغذیه: مخفی (Base64)")
        print("✅" * 20)
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🎯" * 25)
        print("🛡️  PRX11 V2Ray Config Collector - TCP Ping Version")
        print("✨ پینگ TCP | تشخیص کشور از آدرس")
        print("🎯" * 25)
        
        try:
            # ایجاد پوشه‌ها
            self.create_directories()
            
            # جمع‌آوری کانفیگ‌ها از منابع مخفی
            self.collect_from_hidden_sources()
            
            if not self.collected_configs:
                print("❌ هیچ کانفیگی از منابع مخفی یافت نشد!")
                return False
            
            # پردازش کانفیگ‌ها با پینگ TCP
            self.process_configs_with_tcp_ping()
            
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
    collector = PRX11TCPCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
