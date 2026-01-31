#!/usr/bin/env python3
"""
SOCKS5 Proxy Collector
Runs on GitHub Actions - Collects proxies from public sources
"""

import requests
import re
import time
import json
import os
from datetime import datetime

print("=" * 60)
print("  SOCKS5 Proxy Collector (GitHub)")
print("=" * 60)

# ==================== CONFIGURATION ====================

OUTPUT_FILE = "socks5_raw.txt"
OUTPUT_JSON = "socks5_sources_status.json"

# ==================== SOURCES ====================

PROXY_SOURCES = [
    # === APIs ===
    {
        "name": "ProxyScrape",
        "url": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        "type": "text"
    },
    {
        "name": "ProxyList Download",
        "url": "https://www.proxy-list.download/api/v1/get?type=socks5",
        "type": "text"
    },
    {
        "name": "OpenProxyList",
        "url": "https://openproxylist.xyz/socks5.txt",
        "type": "text"
    },
    {
        "name": "ProxyScrape v3",
        "url": "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000",
        "type": "text"
    },
    
    # === GitHub Repos ===
    {
        "name": "TheSpeedX",
        "url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "type": "text"
    },
    {
        "name": "ShiftyTR",
        "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "type": "text"
    },
    {
        "name": "monosans",
        "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "type": "text"
    },
    {
        "name": "hookzof",
        "url": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "type": "text"
    },
    {
        "name": "jetkai",
        "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        "type": "text"
    },
    {
        "name": "roosterkid",
        "url": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        "type": "text"
    },
    {
        "name": "MuRongPIG",
        "url": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
        "type": "text"
    },
    {
        "name": "prxchk",
        "url": "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
        "type": "text"
    },
    {
        "name": "STARTER8128",
        "url": "https://raw.githubusercontent.com/STARTER8128/ProxyList/refs/heads/main/SOCKS5.txt",
        "type": "text"
    },
    {
        "name": "zloi-user",
        "url": "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
        "type": "text"
    },
    {
        "name": "Anonym0usWork1221",
        "url": "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks5_proxies.txt",
        "type": "text"
    },
    {
        "name": "ErcinDedeworker",
        "url": "https://raw.githubusercontent.com/ErcinDedeworker/Proxy-List-World/main/proxy-list/data/socks5.txt",
        "type": "text"
    },
    {
        "name": "sunny9577",
        "url": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies/socks5.txt",
        "type": "text"
    },
    {
        "name": "officialputuid",
        "url": "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/socks5/socks5.txt",
        "type": "text"
    },
    {
        "name": "proxifly",
        "url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
        "type": "text"
    },
    {
        "name": "r00tee",
        "url": "https://raw.githubusercontent.com/r00tee/Proxy-List/main/Socks5.txt",
        "type": "text"
    },
    {
        "name": "Zaeem20",
        "url": "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
        "type": "text"
    },
    {
        "name": "BreakingTechFr",
        "url": "https://raw.githubusercontent.com/BreakingTechFr/Proxy_Free/main/proxies/socks5.txt",
        "type": "text"
    },
    {
        "name": "Vann-Dev",
        "url": "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/socks5.txt",
        "type": "text"
    },
    {
        "name": "yemixzy",
        "url": "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks5.txt",
        "type": "text"
    },
    {
        "name": "casals-ar",
        "url": "https://raw.githubusercontent.com/casals-ar/proxy-list/main/socks5",
        "type": "text"
    },
    {
        "name": "fahimscirex",
        "url": "https://raw.githubusercontent.com/fahimscirex/proxybd/master/proxylist/socks5.txt",
        "type": "text"
    },
    {
        "name": "mmpx12",
        "url": "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "type": "text"
    },
    {
        "name": "zevtyardt",
        "url": "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks5.txt",
        "type": "text"
    },
    {
        "name": "im-razvan",
        "url": "https://raw.githubusercontent.com/im-razvan/proxy_list/main/socks5.txt",
        "type": "text"
    },
    
    # === GeoNode API ===
    {
        "name": "GeoNode",
        "url": "https://proxylist.geonode.com/api/proxy-list?protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
        "type": "json",
        "json_path": "data"
    },
]

# ==================== FUNCTIONS ====================

def extract_proxies_from_text(text):
    """Extract ip:port patterns from text"""
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})'
    matches = re.findall(pattern, text)
    proxies = set()
    
    for ip, port in matches:
        try:
            port_int = int(port)
            if 1 <= port_int <= 65535:
                parts = ip.split('.')
                if all(0 <= int(p) <= 255 for p in parts):
                    proxies.add(f"{ip}:{port}")
        except:
            continue
    
    return proxies

def extract_proxies_from_json(data, json_path=None):
    """Extract proxies from JSON response"""
    proxies = set()
    
    try:
        if json_path:
            for key in json_path.split('.'):
                data = data[key]
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    ip = item.get('ip') or item.get('host') or item.get('address')
                    port = item.get('port')
                    
                    if ip and port:
                        proxies.add(f"{ip}:{port}")
                
                elif isinstance(item, str) and ':' in item:
                    proxies.add(item.strip())
    except:
        pass
    
    return proxies

def fetch_from_source(source):
    """Fetch proxies from a single source"""
    name = source['name']
    url = source['url']
    source_type = source.get('type', 'text')
    json_path = source.get('json_path')
    
    result = {
        'name': name,
        'url': url,
        'success': False,
        'count': 0,
        'error': None
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            if source_type == 'json':
                try:
                    data = response.json()
                    proxies = extract_proxies_from_json(data, json_path)
                except:
                    proxies = extract_proxies_from_text(response.text)
            else:
                proxies = extract_proxies_from_text(response.text)
            
            result['success'] = True
            result['count'] = len(proxies)
            result['proxies'] = proxies
        else:
            result['error'] = f"HTTP {response.status_code}"
            result['proxies'] = set()
            
    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
        result['proxies'] = set()
    except Exception as e:
        result['error'] = str(e)[:100]
        result['proxies'] = set()
    
    return result

def collect_all():
    """Collect proxies from all sources"""
    print(f"\n📥 Collecting from {len(PROXY_SOURCES)} sources...\n")
    
    all_proxies = set()
    source_results = []
    
    for i, source in enumerate(PROXY_SOURCES, 1):
        print(f"  [{i:2}/{len(PROXY_SOURCES)}] {source['name'][:30]:30}", end=" ")
        
        result = fetch_from_source(source)
        source_results.append({
            'name': result['name'],
            'url': result['url'],
            'success': result['success'],
            'count': result['count'],
            'error': result.get('error')
        })
        
        if result['success']:
            all_proxies.update(result['proxies'])
            print(f"✅ {result['count']} proxies")
        else:
            print(f"❌ {result.get('error', 'Failed')}")
        
        time.sleep(0.5)
    
    return all_proxies, source_results

def save_results(proxies, source_results):
    """Save collected proxies"""
    print(f"\n💾 Saving results...")
    
    sorted_proxies = sorted(proxies)
    
    with open(OUTPUT_FILE, 'w') as f:
        for proxy in sorted_proxies:
            f.write(f"{proxy}\n")
    print(f"   ✅ {OUTPUT_FILE}: {len(sorted_proxies)} proxies")
    
    status = {
        'collected_at': datetime.now().isoformat(),
        'total_proxies': len(sorted_proxies),
        'sources': source_results
    }
    
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(status, f, indent=2)
    print(f"   ✅ {OUTPUT_JSON}: Source statistics")

def print_summary(proxies, source_results):
    """Print collection summary"""
    print(f"\n{'='*60}")
    print(f"  COLLECTION SUMMARY")
    print(f"{'='*60}")
    
    successful = [s for s in source_results if s['success']]
    failed = [s for s in source_results if not s['success']]
    
    print(f"  Total proxies:     {len(proxies)}")
    print(f"  Sources success:   {len(successful)}/{len(source_results)}")
    print(f"  Sources failed:    {len(failed)}")
    
    if failed:
        print(f"\n  ❌ Failed sources:")
        for s in failed[:10]:
            print(f"     • {s['name']}: {s.get('error', 'Unknown')}")
    
    print(f"\n  📊 Top sources:")
    top_sources = sorted(successful, key=lambda x: x['count'], reverse=True)[:10]
    for s in top_sources:
        print(f"     • {s['name']}: {s['count']} proxies")

# ==================== MAIN ====================

def main():
    """Main function"""
    start_time = time.time()
    
    proxies, source_results = collect_all()
    
    if not proxies:
        print("\n❌ No proxies collected!")
        return
    
    save_results(proxies, source_results)
    
    print_summary(proxies, source_results)
    
    elapsed = round(time.time() - start_time, 1)
    print(f"\n✅ Done in {elapsed}s")

if __name__ == "__main__":
    main()
