#!/usr/bin/env python3
"""
SOCKS5 Proxy Tester
Runs LOCALLY - Tests proxies from your network (Iran)
Outputs: working proxies + Telegram format
"""

import socket
import requests
import time
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import quote

print("=" * 60)
print("  SOCKS5 Proxy Tester (Local)")
print("  Run this WITHOUT VPN for accurate Iran testing!")
print("=" * 60)

# ==================== CONFIGURATION ====================

# Input file (from GitHub)
INPUT_FILE = "socks5_raw.txt"
INPUT_URL = None  # Set this to your GitHub raw URL if you want to fetch directly
# Example: INPUT_URL = "https://raw.githubusercontent.com/yourusername/yourrepo/main/socks5_raw.txt"

# Output files
OUTPUT_WORKING = "socks5_working.txt"           # ip:port format
OUTPUT_TELEGRAM = "socks5_telegram.txt"         # Telegram URL format
OUTPUT_JSON = "socks5_tested_results.json"      # Full details

# Testing settings
TEST_TIMEOUT = 10         # Seconds for each test
MAX_WORKERS = 50          # Parallel tests (reduce if your internet is slow)
TEST_URL = "http://httpbin.org/ip"  # URL to test through proxy

# Telegram proxy URL format
TELEGRAM_SOCKS5_FORMAT = "https://t.me/socks?server={ip}&port={port}"
TELEGRAM_SOCKS5_AUTH_FORMAT = "https://t.me/socks?server={ip}&port={port}&user={user}&pass={password}"

# Your real IP (auto-detected)
MY_REAL_IP = None

# ==================== FUNCTIONS ====================

def get_my_real_ip():
    """Get your real IP address"""
    global MY_REAL_IP
    
    print("\n🔍 Detecting your real IP...")
    
    ip_services = [
        "https://api.ipify.org?format=json",
        "https://ipinfo.io/json",
        "https://api.ip.sb/ip",
        "http://ip-api.com/json"
    ]
    
    for service in ip_services:
        try:
            response = requests.get(service, timeout=10)
            if response.status_code == 200:
                if 'json' in service:
                    try:
                        data = response.json()
                        MY_REAL_IP = data.get('ip') or data.get('query') or data.get('origin')
                    except:
                        MY_REAL_IP = response.text.strip()
                else:
                    MY_REAL_IP = response.text.strip()
                
                if MY_REAL_IP:
                    print(f"   ✅ Your IP: {MY_REAL_IP}")
                    return MY_REAL_IP
        except:
            continue
    
    print("   ⚠️  Could not detect IP (anonymity check disabled)")
    return None

def load_proxies():
    """Load proxies from file or URL"""
    proxies = []
    
    # Try URL first if configured
    if INPUT_URL:
        print(f"\n📥 Fetching proxies from URL...")
        try:
            response = requests.get(INPUT_URL, timeout=30)
            if response.status_code == 200:
                for line in response.text.strip().split('\n'):
                    line = line.strip()
                    if line and ':' in line and not line.startswith('#'):
                        proxies.append(line)
                print(f"   ✅ Loaded {len(proxies)} proxies from URL")
                return proxies
        except Exception as e:
            print(f"   ⚠️  URL fetch failed: {e}")
    
    # Try local file
    if os.path.exists(INPUT_FILE):
        print(f"\n📂 Loading proxies from {INPUT_FILE}...")
        with open(INPUT_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    proxies.append(line)
        print(f"   ✅ Loaded {len(proxies)} proxies from file")
        return proxies
    
    print(f"\n❌ No proxy source found!")
    print(f"   • Create {INPUT_FILE} with proxies (one per line)")
    print(f"   • Or set INPUT_URL in the script")
    return []

def test_socks5_proxy(proxy):
    """
    Test a SOCKS5 proxy
    Returns: dict with results or None if failed
    """
    try:
        parts = proxy.split(':')
        if len(parts) == 2:
            ip, port = parts
            user, password = None, None
        elif len(parts) == 4:
            ip, port, user, password = parts
        else:
            return None
        
        port = int(port)
    except:
        return None
    
    result = {
        'proxy': proxy,
        'ip': ip,
        'port': port,
        'user': user,
        'password': password,
        'working': False,
        'latency': None,
        'anonymous': None,
        'exit_ip': None,
        'error': None,
        'tested_at': datetime.now().isoformat()
    }
    
    start_time = time.time()
    
    try:
        # Build proxy URL
        if user and password:
            proxy_url = f"socks5h://{user}:{password}@{ip}:{port}"
        else:
            proxy_url = f"socks5h://{ip}:{port}"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Test HTTP request through proxy
        response = requests.get(
            TEST_URL,
            proxies=proxies,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code == 200:
            result['working'] = True
            result['latency'] = round((time.time() - start_time) * 1000)  # ms
            
            # Get exit IP
            try:
                data = response.json()
                result['exit_ip'] = data.get('origin', '').split(',')[0].strip()
                
                # Check anonymity
                if MY_REAL_IP and result['exit_ip']:
                    result['anonymous'] = MY_REAL_IP not in result['exit_ip']
            except:
                pass
            
            return result
        else:
            result['error'] = f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
    except requests.exceptions.ProxyError as e:
        result['error'] = "Proxy error"
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error"
    except Exception as e:
        result['error'] = str(e)[:50]
    
    return None

def test_all_proxies(proxies):
    """Test all proxies in parallel"""
    print(f"\n🧪 Testing {len(proxies)} proxies...")
    print(f"   Workers: {MAX_WORKERS}, Timeout: {TEST_TIMEOUT}s")
    print(f"   This may take a while...\n")
    
    working = []
    tested = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_proxy = {
            executor.submit(test_socks5_proxy, proxy): proxy 
            for proxy in proxies
        }
        
        for future in as_completed(future_to_proxy):
            tested += 1
            
            # Progress update
            if tested % 50 == 0 or tested == len(proxies):
                elapsed = round(time.time() - start_time)
                rate = tested / elapsed if elapsed > 0 else 0
                remaining = round((len(proxies) - tested) / rate) if rate > 0 else 0
                print(f"   Progress: {tested}/{len(proxies)} tested, {len(working)} working, ~{remaining}s remaining")
            
            result = future.result()
            if result and result['working']:
                working.append(result)
                anon = "🔒" if result.get('anonymous') else "⚠️"
                print(f"   {anon} ✅ {result['proxy']} - {result['latency']}ms")
    
    elapsed = round(time.time() - start_time, 1)
    print(f"\n📊 Testing complete in {elapsed}s")
    print(f"   Working: {len(working)}/{len(proxies)} ({round(100*len(working)/len(proxies), 1)}%)")
    
    return working

def generate_telegram_url(proxy_result):
    """Generate Telegram proxy URL"""
    ip = proxy_result['ip']
    port = proxy_result['port']
    user = proxy_result.get('user')
    password = proxy_result.get('password')
    
    if user and password:
        return TELEGRAM_SOCKS5_AUTH_FORMAT.format(
            ip=ip,
            port=port,
            user=quote(user),
            password=quote(password)
        )
    else:
        return TELEGRAM_SOCKS5_FORMAT.format(ip=ip, port=port)

def save_results(working):
    """Save results to files"""
    print(f"\n💾 Saving results...")
    
    if not working:
        print("   ⚠️  No working proxies to save!")
        return
    
    # Sort by latency
    working.sort(key=lambda x: x.get('latency', 9999))
    
    # === File 1: Normal format (ip:port) ===
    with open(OUTPUT_WORKING, 'w', encoding='utf-8') as f:
        f.write(f"# SOCKS5 Working Proxies\n")
        f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total: {len(working)} proxies\n")
        f.write(f"# Format: ip:port\n\n")
        
        for p in working:
            if p.get('user') and p.get('password'):
                f.write(f"{p['ip']}:{p['port']}:{p['user']}:{p['password']}\n")
            else:
                f.write(f"{p['ip']}:{p['port']}\n")
    
    print(f"   ✅ {OUTPUT_WORKING}: {len(working)} proxies")
    
    # === File 2: Telegram format ===
    with open(OUTPUT_TELEGRAM, 'w', encoding='utf-8') as f:
        f.write(f"# Telegram SOCKS5 Proxy Links\n")
        f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total: {len(working)} proxies\n")
        f.write(f"# Click any link to add proxy to Telegram\n\n")
        
        for p in working:
            telegram_url = generate_telegram_url(p)
            latency = p.get('latency', '?')
            anon = "Anonymous" if p.get('anonymous') else "Transparent"
            f.write(f"# {p['ip']}:{p['port']} - {latency}ms - {anon}\n")
            f.write(f"{telegram_url}\n\n")
    
    print(f"   ✅ {OUTPUT_TELEGRAM}: {len(working)} Telegram links")
    
    # === File 3: JSON with full details ===
    output_data = {
        'updated_at': datetime.now().isoformat(),
        'total_working': len(working),
        'your_ip': MY_REAL_IP,
        'proxies': working
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ {OUTPUT_JSON}: Full details")

def print_summary(working):
    """Print summary"""
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    
    if not working:
        print("  ❌ No working proxies found!")
        return
    
    # Statistics
    latencies = [p['latency'] for p in working if p.get('latency')]
    anonymous = [p for p in working if p.get('anonymous') == True]
    
    print(f"  Total working:     {len(working)}")
    print(f"  Anonymous:         {len(anonymous)}")
    
    if latencies:
        print(f"  Average latency:   {sum(latencies)//len(latencies)}ms")
        print(f"  Fastest:           {min(latencies)}ms")
        print(f"  Slowest:           {max(latencies)}ms")
    
    # Speed categories
    fast = [p for p in working if p.get('latency', 9999) < 1000]
    medium = [p for p in working if 1000 <= p.get('latency', 9999) < 3000]
    slow = [p for p in working if p.get('latency', 9999) >= 3000]
    
    print(f"\n  Speed breakdown:")
    print(f"    🚀 Fast (<1s):    {len(fast)}")
    print(f"    ⚡ Medium (1-3s): {len(medium)}")
    print(f"    🐌 Slow (>3s):    {len(slow)}")
    
    # Top 5 fastest
    print(f"\n  🏆 Top 5 Fastest:")
    for i, p in enumerate(working[:5], 1):
        anon = "🔒" if p.get('anonymous') else "⚠️"
        print(f"    {i}. {anon} {p['ip']}:{p['port']} - {p.get('latency', '?')}ms")
    
    # Sample Telegram links
    print(f"\n  📱 Sample Telegram Links:")
    for p in working[:3]:
        telegram_url = generate_telegram_url(p)
        print(f"    {telegram_url}")

def show_usage():
    """Show usage instructions"""
    print(f"""
📖 USAGE:
=========

1. First, get the proxy list:
   
   Option A: Download from GitHub
   $ curl -o {INPUT_FILE} https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/socks5_raw.txt
   
   Option B: Set INPUT_URL in this script
   
   Option C: Create {INPUT_FILE} manually with proxies (one per line)

2. Run this script WITHOUT VPN:
   $ python {os.path.basename(__file__)}

3. Results will be saved to:
   • {OUTPUT_WORKING}   - Normal format (ip:port)
   • {OUTPUT_TELEGRAM}  - Telegram links
   • {OUTPUT_JSON}      - Full details (JSON)

⚠️  IMPORTANT: Run without VPN for accurate Iran testing!
""")

# ==================== MAIN ====================

def main():
    """Main function"""
    
    # Check for help
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_usage()
        return
    
    # Step 1: Detect real IP
    get_my_real_ip()
    
    # Step 2: Load proxies
    proxies = load_proxies()
    
    if not proxies:
        show_usage()
        return
    
    # Step 3: Test proxies
    working = test_all_proxies(proxies)
    
    # Step 4: Save results
    save_results(working)
    
    # Step 5: Print summary
    print_summary(working)
    
    print(f"\n✅ Done!")
    print(f"\n💡 TIP: Open {OUTPUT_TELEGRAM} and click any link to add proxy to Telegram!")

if __name__ == "__main__":
    main()
