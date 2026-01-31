#!/usr/bin/env python3
"""
SOCKS5 Proxy Scanner & Tester
Collects proxies from public sources and tests them
"""

import socket
import struct
import requests
import time
import re
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse

print("=" * 60)
print("  SOCKS5 Proxy Scanner & Tester")
print("=" * 60)

# ==================== CONFIGURATION ====================

# Testing settings
TEST_TIMEOUT = 5          # Seconds for each test
MAX_WORKERS = 100          # Parallel tests
TEST_URL = "http://httpbin.org/ip"  # URL to test proxy
CHECK_ANONYMITY = True     # Check if proxy hides your IP

# Output files
OUTPUT_WORKING = "socks5_working.txt"
OUTPUT_FAST = "socks5_fast.txt"          # < 2 second response
OUTPUT_JSON = "socks5_results.json"
OUTPUT_WITH_COUNTRY = "socks5_by_country.txt"

# Your real IP (for anonymity check) - will be auto-detected
MY_REAL_IP = None

# ==================== SOURCES ====================

PROXY_SOURCES = [
    # APIs
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://openproxylist.xyz/socks5.txt",
    
    # GitHub repos
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
    "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/STARTER8128/ProxyList/refs/heads/main/SOCKS5.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
    "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks5_proxies.txt",
    "https://raw.githubusercontent.com/ErcinDedeworker/Proxy-List/main/socks5.txt",
]

# ==================== COLLECTION ====================

def get_my_real_ip():
    """Get your real IP address (run without VPN)"""
    global MY_REAL_IP
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        MY_REAL_IP = response.json().get("ip")
        print(f"📍 Your real IP: {MY_REAL_IP}")
        return MY_REAL_IP
    except Exception as e:
        print(f"⚠️  Could not detect real IP: {e}")
        return None

def extract_proxies_from_text(text):
    """Extract ip:port patterns from text"""
    # Pattern: IP:PORT
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})'
    matches = re.findall(pattern, text)
    proxies = []
    for ip, port in matches:
        try:
            port_int = int(port)
            if 1 <= port_int <= 65535:
                # Validate IP
                parts = ip.split('.')
                if all(0 <= int(p) <= 255 for p in parts):
                    proxies.append(f"{ip}:{port}")
        except:
            continue
    return proxies

def collect_from_sources():
    """Collect proxies from all sources"""
    print("\n📥 Collecting proxies from sources...")
    all_proxies = set()
    
    for i, url in enumerate(PROXY_SOURCES, 1):
        try:
            print(f"  [{i}/{len(PROXY_SOURCES)}] {url[:60]}...")
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                
                # Try JSON format
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                ip = item.get('ip') or item.get('host')
                                port = item.get('port')
                                if ip and port:
                                    all_proxies.add(f"{ip}:{port}")
                            elif isinstance(item, str) and ':' in item:
                                all_proxies.add(item.strip())
                    elif isinstance(data, dict) and 'data' in data:
                        for item in data['data']:
                            ip = item.get('ip') or item.get('host')
                            port = item.get('port')
                            if ip and port:
                                all_proxies.add(f"{ip}:{port}")
                except:
                    # Plain text format
                    proxies = extract_proxies_from_text(content)
                    all_proxies.update(proxies)
                
                print(f"      ✓ Found {len(extract_proxies_from_text(content))} proxies")
            
            time.sleep(0.5)  # Be nice to servers
            
        except Exception as e:
            print(f"      ✗ Error: {e}")
            continue
    
    print(f"\n📊 Total collected: {len(all_proxies)} unique proxies")
    return list(all_proxies)

# ==================== TESTING ====================

def test_socks5_connection(proxy):
    """
    Test if a proxy is a working SOCKS5 proxy
    Returns: dict with results or None if failed
    """
    try:
        ip, port = proxy.split(':')
        port = int(port)
    except:
        return None
    
    result = {
        'proxy': proxy,
        'ip': ip,
        'port': port,
        'working': False,
        'latency': None,
        'anonymous': None,
        'country': None,
        'tested_at': datetime.now().isoformat()
    }
    
    start_time = time.time()
    
    try:
        # Step 1: TCP connection test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TEST_TIMEOUT)
        sock.connect((ip, port))
        
        # Step 2: SOCKS5 handshake
        # Send greeting: VER=5, NMETHODS=1, METHOD=0 (no auth)
        sock.sendall(b'\x05\x01\x00')
        
        # Receive response
        response = sock.recv(2)
        if len(response) < 2:
            sock.close()
            return None
        
        # Check if SOCKS5 and no auth required (or auth available)
        if response[0] != 0x05:  # Not SOCKS5
            sock.close()
            return None
        
        if response[1] == 0xFF:  # No acceptable methods
            sock.close()
            return None
        
        sock.close()
        
        # Step 3: HTTP request through proxy
        proxies = {
            'http': f'socks5://{proxy}',
            'https': f'socks5://{proxy}'
        }
        
        try:
            http_response = requests.get(
                TEST_URL, 
                proxies=proxies, 
                timeout=TEST_TIMEOUT
            )
            
            if http_response.status_code == 200:
                result['working'] = True
                result['latency'] = round((time.time() - start_time) * 1000)  # ms
                
                # Check anonymity
                if CHECK_ANONYMITY and MY_REAL_IP:
                    try:
                        returned_ip = http_response.json().get('origin', '')
                        result['anonymous'] = MY_REAL_IP not in returned_ip
                        result['exit_ip'] = returned_ip
                    except:
                        pass
                
        except:
            # SOCKS5 handshake worked but HTTP failed
            # Still mark as partially working
            result['working'] = True
            result['latency'] = round((time.time() - start_time) * 1000)
        
        return result
        
    except socket.timeout:
        return None
    except ConnectionRefusedError:
        return None
    except Exception as e:
        return None

def test_socks5_with_pysocks(proxy):
    """
    Alternative test using PySocks library (more reliable)
    Requires: pip install pysocks requests[socks]
    """
    try:
        ip, port = proxy.split(':')
        port = int(port)
    except:
        return None
    
    result = {
        'proxy': proxy,
        'ip': ip,
        'port': port,
        'working': False,
        'latency': None,
        'anonymous': None,
        'exit_ip': None,
        'tested_at': datetime.now().isoformat()
    }
    
    start_time = time.time()
    
    try:
        proxies = {
            'http': f'socks5h://{ip}:{port}',
            'https': f'socks5h://{ip}:{port}'
        }
        
        response = requests.get(
            TEST_URL,
            proxies=proxies,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code == 200:
            result['working'] = True
            result['latency'] = round((time.time() - start_time) * 1000)
            
            try:
                data = response.json()
                result['exit_ip'] = data.get('origin', '')
                
                if CHECK_ANONYMITY and MY_REAL_IP:
                    result['anonymous'] = MY_REAL_IP not in result['exit_ip']
            except:
                pass
            
            return result
        
    except Exception as e:
        pass
    
    return None

def test_all_proxies(proxies):
    """Test all proxies in parallel"""
    print(f"\n🧪 Testing {len(proxies)} proxies (this may take a while)...")
    print(f"   Workers: {MAX_WORKERS}, Timeout: {TEST_TIMEOUT}s")
    
    working = []
    tested = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_proxy = {
            executor.submit(test_socks5_with_pysocks, proxy): proxy 
            for proxy in proxies
        }
        
        # Process results as they complete
        for future in as_completed(future_to_proxy):
            tested += 1
            
            if tested % 100 == 0:
                print(f"   Tested {tested}/{len(proxies)}... ({len(working)} working)")
            
            result = future.result()
            if result and result['working']:
                working.append(result)
                print(f"   ✅ {result['proxy']} ({result['latency']}ms)")
    
    print(f"\n📊 Testing complete: {len(working)}/{len(proxies)} working")
    return working

# ==================== OUTPUT ====================

def get_country_from_ip(ip):
    """Get country code from IP (using free API)"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3)
        if response.status_code == 200:
            return response.json().get('countryCode', 'XX')
    except:
        pass
    return 'XX'

def enrich_with_country(working_proxies):
    """Add country information to proxies"""
    print("\n🌍 Getting country information...")
    
    for i, proxy in enumerate(working_proxies):
        if i % 10 == 0:
            print(f"   Processing {i}/{len(working_proxies)}...")
        
        ip = proxy['exit_ip'] if proxy.get('exit_ip') else proxy['ip']
        proxy['country'] = get_country_from_ip(ip.split(',')[0].strip())
        time.sleep(0.1)  # Rate limiting
    
    return working_proxies

def save_results(working_proxies):
    """Save results to files"""
    print("\n💾 Saving results...")
    
    # Sort by latency
    working_proxies.sort(key=lambda x: x.get('latency', 9999))
    
    # Plain text - all working
    with open(OUTPUT_WORKING, 'w') as f:
        for p in working_proxies:
            f.write(f"{p['proxy']}\n")
    print(f"   ✅ {OUTPUT_WORKING}: {len(working_proxies)} proxies")
    
    # Fast proxies only (< 2000ms)
    fast = [p for p in working_proxies if p.get('latency', 9999) < 2000]
    with open(OUTPUT_FAST, 'w') as f:
        for p in fast:
            f.write(f"{p['proxy']}\n")
    print(f"   ✅ {OUTPUT_FAST}: {len(fast)} proxies")
    
    # JSON with all metadata
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(working_proxies, f, indent=2)
    print(f"   ✅ {OUTPUT_JSON}: Full details")
    
    # By country
    by_country = {}
    for p in working_proxies:
        country = p.get('country', 'XX')
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(p['proxy'])
    
    with open(OUTPUT_WITH_COUNTRY, 'w') as f:
        for country, proxies in sorted(by_country.items()):
            f.write(f"\n# {country} ({len(proxies)} proxies)\n")
            for proxy in proxies:
                f.write(f"{proxy}\n")
    print(f"   ✅ {OUTPUT_WITH_COUNTRY}: Grouped by country")

def print_summary(working_proxies):
    """Print summary statistics"""
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if not working_proxies:
        print("  ❌ No working proxies found!")
        return
    
    # Stats
    latencies = [p['latency'] for p in working_proxies if p.get('latency')]
    anonymous = [p for p in working_proxies if p.get('anonymous') == True]
    
    print(f"  Total working:     {len(working_proxies)}")
    print(f"  Anonymous:         {len(anonymous)}")
    
    if latencies:
        print(f"  Avg latency:       {sum(latencies)//len(latencies)}ms")
        print(f"  Fastest:           {min(latencies)}ms")
        print(f"  Slowest:           {max(latencies)}ms")
    
    # By country
    countries = {}
    for p in working_proxies:
        c = p.get('country', 'XX')
        countries[c] = countries.get(c, 0) + 1
    
    print(f"\n  By country:")
    for country, count in sorted(countries.items(), key=lambda x: -x[1])[:10]:
        print(f"    {country}: {count}")
    
    # Top 5 fastest
    print(f"\n  🏆 Top 5 fastest:")
    for p in working_proxies[:5]:
        anon = "🔒" if p.get('anonymous') else "⚠️"
        print(f"    {anon} {p['proxy']} - {p.get('latency', '?')}ms ({p.get('country', '?')})")

# ==================== MAIN ====================

def main():
    """Main function"""
    
    # Step 0: Get your real IP
    print("\n🔍 Detecting your real IP...")
    get_my_real_ip()
    
    if MY_REAL_IP:
        print(f"   ⚠️  Make sure VPN is OFF for accurate testing!")
    
    # Step 1: Collect proxies
    proxies = collect_from_sources()
    
    if not proxies:
        print("❌ No proxies collected!")
        return
    
    # Step 2: Test proxies
    working = test_all_proxies(proxies)
    
    if not working:
        print("❌ No working proxies found!")
        return
    
    # Step 3: Enrich with country info
    working = enrich_with_country(working)
    
    # Step 4: Save results
    save_results(working)
    
    # Step 5: Print summary
    print_summary(working)
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()
