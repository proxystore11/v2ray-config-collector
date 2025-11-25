#!/usr/bin/env python3
import os
import json
import base64
import requests
import re
import yaml
from datetime import datetime
import hashlib
import ipaddress

class V2RayConfigCollector:
    def __init__(self):
        self.config_data = self.load_config()
        self.collected_configs = []
        self.processed_configs = []
        
    def load_config(self):
        """بارگذاری تنظیمات از فایل YAML"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return {
                'project': {'name': 'PRX11', 'version': '1.0.0'},
                'sources': {
                    'github': [
                        'https://raw.githubusercontent.com/freev2ray/freev2ray/master/README.md',
                        'https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity.txt',
                        'https://raw.githubusercontent.com/v2ray/dist/master/v2ray-configs.txt'
                    ]
                },
                'countries': {
                    'US': '🇺🇸 آمریکا', 'DE': '🇩🇪 آلمان', 'FR': '🇫🇷 فرانسه',
                    'NL': '🇳🇱 هلند', 'TR': '🇹🇷 ترکیه', 'SG': '🇸🇬 سنگاپور',
                    'JP': '🇯🇵 ژاپن', 'KR': '🇰🇷 کره جنوبی', 'GB': '🇬🇧 انگلیس',
                    'CA': '🇨🇦 کانادa'
                },
                'settings': {'max_configs': 50, 'timeout': 30},
                'remark': {
                    'format': '{flag} {country} {config_number:02d} {project_name}',
                    'project_name': 'PRX11'
                }
            }
    
    def create_directories(self):
        """ایجاد پوشه‌های لازم"""
        directories = ['output/configs', 'output/subscriptions', 'output/logs']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        print("✅ پوشه‌های خروجی ایجاد شدند")
    
    def make_request(self, url):
        """درخواست HTTP"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ خطا در دریافت {url}: {e}")
            return None
    
    def collect_from_sources(self):
        """جمع‌آوری کانفیگ‌ها"""
        print("🔍 شروع جمع‌آوری از منابع...")
        all_configs = []
        
        for url in self.config_data['sources']['github']:
            print(f"📡 دریافت از: {url}")
            content = self.make_request(url)
            if content:
                configs = self.extract_configs(content)
                all_configs.extend(configs)
                print(f"✅ {len(configs)} کانفیگ یافت شد")
            else:
                print(f"⚠️ نتوانست از {url} دریافت کند")
        
        self.collected_configs = self.remove_duplicates(all_configs)
        print(f"📊 کل کانفیگ‌های منحصر به فرد: {len(self.collected_configs)}")
        return self.collected_configs
    
    def extract_configs(self, text):
        """استخراج کانفیگ‌ها از متن"""
        patterns = [
            r'vmess://[A-Za-z0-9+/=]+',
            r'vless://[^\s"\']+',
            r'trojan://[^\s"\']+',
            r'ss://[A-Za-z0-9+/=]+',
        ]
        configs = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                config_hash = hashlib.md5(match.encode()).hexdigest()
                config_type = 'vmess' if match.startswith('vmess://') else 'other'
                configs.append({
                    'raw_config': match,
                    'hash': config_hash,
                    'type': config_type
                })
        return configs
    
    def remove_duplicates(self, configs):
        """حذف تکراری‌ها"""
        unique_configs = []
        seen_hashes = set()
        for config in configs:
            if config['hash'] not in seen_hashes:
                unique_configs.append(config)
                seen_hashes.add(config['hash'])
        return unique_configs
    
    def process_configs(self):
        """پردازش کانفیگ‌ها"""
        print("🔄 شروع پردازش کانفیگ‌ها...")
        processed = []
        country_counters = {}
        
        for config in self.collected_configs[:self.config_data['settings']['max_configs']]:
            try:
                if config['type'] == 'vmess':
                    processed_config = self.process_vmess_config(config, country_counters)
                    if processed_config:
                        processed.append(processed_config)
                else:
                    # سایر پروتکل‌ها بدون تغییر
                    processed.append({
                        **config,
                        'final_url': config['raw_config'],
                        'country': 'Unknown',
                        'remark': 'Unprocessed'
                    })
            except Exception as e:
                print(f"⚠️ خطا در پردازش کانفیگ: {e}")
                processed.append({
                    **config,
                    'final_url': config['raw_config'],
                    'country': 'Unknown', 
                    'remark': 'Error'
                })
        
        self.processed_configs = processed
        print(f"✅ پردازش کامل: {len(processed)} کانفیگ پردازش شد")
        return processed
    
    def detect_country_from_ip(self, server_address):
        """تشخیص کشور بر اساس IP با استفاده از API رایگان"""
        try:
            # اگر آدرس IP نیست (مثلاً دامنه است)، ابتدا IP آن را پیدا می‌کنیم
            if not self.is_ip_address(server_address):
                # برای سادگی، از دامنه تشخیص می‌دهیم
                return self.detect_country_from_domain(server_address)
            
            # استفاده از API رایگان برای تشخیص کشور از IP
            response = requests.get(f'http://ip-api.com/json/{server_address}', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    return data['countryCode']
        except:
            pass
        
        # اگر API جواب نداد، از دامنه تشخیص می‌دهیم
        return self.detect_country_from_domain(server_address)
    
    def is_ip_address(self, address):
        """بررسی اینکه آیا آدرس IP است یا دامنه"""
        try:
            ipaddress.ip_address(address)
            return True
        except:
            return False
    
    def detect_country_from_domain(self, domain):
        """تشخیص کشور از دامنه"""
        domain_lower = domain.lower()
        
        # تشخیص دقیق‌تر بر اساس TLD و کلمات کلیدی
        country_tlds = {
            'US': ['.us', '.com', '.net', '.org', 'usa', 'united', 'american'],
            'DE': ['.de', 'german', 'deutschland', 'berlin', 'frankfurt'],
            'FR': ['.fr', 'france', 'paris', 'français'],
            'NL': ['.nl', 'netherlands', 'amsterdam', 'dutch'],
            'TR': ['.tr', 'turkey', 'turkish', 'istanbul'],
            'SG': ['.sg', 'singapore'],
            'JP': ['.jp', 'japan', 'tokyo', 'osaka'],
            'KR': ['.kr', 'korea', 'seoul', 'korean'],
            'GB': ['.uk', '.gb', 'london', 'british', 'england'],
            'CA': ['.ca', 'canada', 'toronto', 'vancouver']
        }
        
        for country_code, indicators in country_tlds.items():
            for indicator in indicators:
                if indicator in domain_lower:
                    return country_code
        
        # پیش‌فرض آمریکا برای دامنه‌های عمومی
        return 'US'
    
    def process_vmess_config(self, config, country_counters):
        """پردازش کانفیگ VMess"""
        config_url = config['raw_config']
        
        # حذف پیشوند vmess://
        encoded = config_url[8:]
        
        # اضافه کردن padding اگر لازم باشد
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding
        
        # دیکد base64
        decoded = base64.b64decode(encoded).decode('utf-8')
        config_data = json.loads(decoded)
        
        # تشخیص کشور (با روش جدید)
        server_address = config_data.get('add', '')
        country_code = self.detect_country_from_ip(server_address)
        
        # شمارنده برای کشور
        if country_code not in country_counters:
            country_counters[country_code] = 0
        country_counters[country_code] += 1
        config_number = country_counters[country_code]
        
        # تولید ریمارک جدید با فرمت PRX11
        new_remark = self.generate_remark(country_code, config_number)
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
            'server': config_data.get('add', ''),
            'port': config_data.get('port', ''),
            'protocol': 'vmess'
        }
    
    def generate_remark(self, country_code, config_number):
        """تولید ریمارک اختصاصی با فرمت PRX11"""
        country_info = self.config_data['countries'].get(country_code, '🇺🇸 آمریکا')
        
        if ' ' in country_info:
            flag = country_info.split(' ')[0]
            country_name = country_info.split(' ')[1]
        else:
            flag = '🇺🇸'
            country_name = country_code
        
        project_name = self.config_data.get('remark', {}).get('project_name', 'PRX11')
        
        return f"{flag} {country_name} {config_number:02d} {project_name}"
    
    def save_results(self):
        """ذخیره‌سازی نتایج با نام PRX11-FREE.txt"""
        print("💾 شروع ذخیره‌سازی نتایج...")
        
        # آماده‌سازی داده‌ها
        config_urls = [config['final_url'] for config in self.processed_configs]
        subscription_content = "\n".join(config_urls)
        
        # آمار کشورها
        country_stats = {}
        for config in self.processed_configs:
            country = config.get('country', 'Unknown')
            country_stats[country] = country_stats.get(country, 0) + 1
        
        # ذخیره فایل اشتراک با نام جدید PRX11-FREE.txt
        with open("output/subscriptions/PRX11-FREE.txt", "w", encoding="utf-8") as f:
            f.write(subscription_content)
        
        # همچنین فایل subscription_latest.txt را هم نگه می‌داریم برای سازگاری
        with open("output/subscriptions/subscription_latest.txt", "w", encoding="utf-8") as f:
            f.write(subscription_content)
        
        # ذخیره نسخه Base64
        encoded = base64.b64encode(subscription_content.encode()).decode()
        with open("output/subscriptions/subscription_base64.txt", "w") as f:
            f.write(encoded)
        
        # ذخیره اطلاعات خلاصه
        summary = {
            "last_update": datetime.now().isoformat(),
            "total_configs": len(self.processed_configs),
            "country_stats": country_stats,
            "project": "PRX11",
            "subscription_file": "PRX11-FREE.txt"
        }
        
        with open("output/configs/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ذخیره‌سازی کامل: {len(self.processed_configs)} کانفیگ")
        print(f"📁 فایل اشتراک: PRX11-FREE.txt")
        
        # نمایش آمار
        print("\n📊 آمار کشورها:")
        for country, count in sorted(country_stats.items()):
            country_name = self.config_data['countries'].get(country, country)
            print(f"   {country_name}: {count} کانفیگ")
    
    def run(self):
        """اجرای کامل پروژه"""
        print("🚀 شروع پروژه جمع‌آوری کانفیگ‌های V2Ray - PRX11")
        print("=" * 60)
        
        try:
            # ایجاد پوشه‌ها
            self.create_directories()
            
            # جمع‌آوری کانفیگ‌ها
            self.collect_from_sources()
            
            if not self.collected_configs:
                print("⚠️ هیچ کانفیگی یافت نشد. ایجاد نمونه‌های تست...")
                self.create_sample_configs()
            
            # پردازش کانفیگ‌ها
            self.process_configs()
            
            # ذخیره‌سازی نتایج
            self.save_results()
            
            print(f"\n🎉 پروژه با موفقیت کامل شد!")
            print(f"📦 تعداد کانفیگ‌های پردازش شده: {len(self.processed_configs)}")
            print("🔗 لینک‌های اشتراک:")
            print("   https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/PRX11-FREE.txt")
            print("   https://github.com/proxystore11/v2ray-config-collector/raw/main/output/subscriptions/subscription_latest.txt")
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در اجرای پروژه: {e}")
            return False
    
    def create_sample_configs(self):
        """ایجاد کانفیگ‌های نمونه در صورت عدم یافتن"""
        print("🔧 ایجاد کانفیگ‌های نمونه...")
        sample_configs = [
            {
                'raw_config': 'vmess://ewoidiI6ICIyIiwKInBzIjogIvCfmrLwn5mC8J+ZhSBEZW1vIDEiLAoiYWRkIjogInVzLWRlbW8xLmNvbSIsCiJwb3J0IjogIjgwODAiLAoiaWQiOiAiMTIzNDU2Nzg5MCIsCiJhaWQiOiAiMCIsCiJuZXQiOiAidGNwIiwKInR5cGUiOiAibm9uZSIsCiJob3N0IjogIiIsCiJwYXRoIjogIiIsCiJ0bHMiOiAiIgp9',
                'hash': 'sample1',
                'type': 'vmess'
            },
            {
                'raw_config': 'vmess://ewoidiI6ICIyIiwKInBzIjogIvCfmrLwn5mC8J+ZhSBEZW1vIDIiLAoiYWRkIjogImRlLWRlbW8yLmNvbSIsCiJwb3J0IjogIjQ0MyIsCiJpZCI6ICIwMTIzNDU2Nzg5IiwKImFpZCI6ICIwIiwKIm5ldCI6ICJ0Y3AiLAoidHlwZSI6ICJub25lIiwKImhvc3QiOiAiIiwKInBhdGgiOiAiIiwKInRscyI6ICIiCn0=',
                'hash': 'sample2', 
                'type': 'vmess'
            }
        ]
        self.collected_configs = sample_configs

def main():
    """تابع اصلی"""
    collector = V2RayConfigCollector()
    success = collector.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
