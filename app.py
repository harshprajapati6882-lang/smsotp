"""
TempSMS — Real Python backend
Scrapes live free SMS sites server-side (no CORS issues)
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# HEADERS  — rotate to avoid blocks
# ─────────────────────────────────────────────
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    },
]

def get_headers():
    return random.choice(HEADERS_LIST)

def safe_get(url, timeout=12):
    """HTTP GET with retries and random headers."""
    for attempt in range(3):
        try:
            r = requests.get(url, headers=get_headers(), timeout=timeout)
            if r.status_code == 200:
                return r
            log.warning(f"[{attempt+1}] HTTP {r.status_code} for {url}")
        except Exception as e:
            log.warning(f"[{attempt+1}] Request error: {e}")
        time.sleep(1.2 * (attempt + 1))
    return None


# ─────────────────────────────────────────────
# OTP / SENDER  helpers
# ─────────────────────────────────────────────
OTP_PATTERNS = [
    r'\b([0-9]{6})\b',
    r'\b([0-9]{4})\b',
    r'\b([0-9]{8})\b',
    r'(?:code|Code|CODE)[:\s\-]+([0-9]{4,8})',
    r'(?:is|IS)[:\s]+([0-9]{4,8})\b',
    r'[:]\s*([0-9]{4,8})\b',
    r'(?:verif\w*)[^\d]*([0-9]{4,8})',
    r'\b([0-9]{5})\b',
]

SENDER_MAP = {
    'google': 'GOOGLE', 'gmail': 'GOOGLE',
    'whatsapp': 'WHATSAPP', 'wa.me': 'WHATSAPP',
    'telegram': 'TELEGRAM',
    'facebook': 'FACEBOOK', 'fb': 'FACEBOOK',
    'instagram': 'INSTAGRAM', 'insta': 'INSTAGRAM',
    'amazon': 'AMAZON',
    'twitter': 'TWITTER', 'x.com': 'TWITTER',
    'tiktok': 'TIKTOK',
    'uber': 'UBER',
    'netflix': 'NETFLIX',
    'microsoft': 'MICROSOFT',
    'apple': 'APPLE',
    'paypal': 'PAYPAL',
    'discord': 'DISCORD',
    'snapchat': 'SNAPCHAT',
    'linkedin': 'LINKEDIN',
}

def extract_otp(text):
    for pattern in OTP_PATTERNS:
        m = re.search(pattern, text)
        if m:
            code = m.group(1).replace('-', '').replace(' ', '')
            if code.isdigit() and 4 <= len(code) <= 8:
                return code
    return None

def guess_sender(text):
    low = text.lower()
    for key, val in SENDER_MAP.items():
        if key in low:
            return val
    # Try first word all-caps
    words = text.strip().split()
    if words and re.match(r'^[A-Z][A-Z0-9\-]{1,20}$', words[0]):
        return words[0].upper()
    return 'SMS'


# ─────────────────────────────────────────────
# SCRAPERS — one per source site
# ─────────────────────────────────────────────

def scrape_receive_smss(number_digits):
    """receive-smss.com — /sms/{digits}/"""
    url = f"https://receive-smss.com/sms/{number_digits}/"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    messages = []

    # Main message rows
    for row in soup.select('div.row.border-bottom, .sms-item, .message-row, table tr'):
        cells = row.find_all(['td', 'div', 'p'])
        texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
        for txt in texts:
            if len(txt) > 8 and re.search(r'\d{4,8}', txt):
                messages.append({
                    'from': guess_sender(txt),
                    'body': txt[:400],
                    'otp': extract_otp(txt),
                    'time': int(time.time()),
                })
        if len(messages) >= 15:
            break

    # Fallback: grab any block with digits
    if not messages:
        for tag in soup.find_all(['p', 'td', 'li', 'div'], string=re.compile(r'\d{4,8}')):
            txt = tag.get_text(strip=True)
            if 8 < len(txt) < 500 and not any(x in txt.lower() for x in ['advertisement', 'cookie', 'privacy']):
                messages.append({
                    'from': guess_sender(txt),
                    'body': txt[:400],
                    'otp': extract_otp(txt),
                    'time': int(time.time()),
                })
            if len(messages) >= 10:
                break
    return messages


def scrape_receivesms_co(number_digits):
    """receivesms.co — /us-phone-number/{digits}/  etc."""
    # Try different country path prefixes
    country_prefixes = ['us', 'uk', 'gb', 'de', 'fr', 'ca', 'se', 'nl', 'ru', 'in', 'au']
    for prefix in country_prefixes:
        url = f"https://www.receivesms.co/{prefix}-phone-number/{number_digits}/"
        r = safe_get(url)
        if r and r.status_code == 200:
            soup = BeautifulSoup(r.text, 'lxml')
            messages = []
            for item in soup.select('.sms-list li, .inbox-message, .message, article, .panel-body'):
                txt = item.get_text(separator=' ', strip=True)
                if len(txt) > 8 and not any(x in txt.lower() for x in ['cookie', 'advertisement']):
                    messages.append({
                        'from': guess_sender(txt),
                        'body': txt[:400],
                        'otp': extract_otp(txt),
                        'time': int(time.time()),
                    })
                if len(messages) >= 15:
                    break
            if messages:
                return messages
    return []


def scrape_quackr(number_e164):
    """quackr.io — /temporary-numbers/{country}/{digits}"""
    # Build URL from number
    num = number_e164.lstrip('+')
    # Map by prefix
    country_map = {
        '1': 'united-states', '44': 'united-kingdom',
        '91': 'india', '7': 'russia', '49': 'germany',
        '33': 'france', '46': 'sweden', '31': 'netherlands',
        '61': 'australia', '55': 'brazil',
    }
    country = 'united-states'
    for prefix, cname in sorted(country_map.items(), key=lambda x: -len(x[0])):
        if num.startswith(prefix):
            country = cname
            break
    url = f"https://quackr.io/temporary-numbers/{country}/{num}"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    messages = []
    for item in soup.select('.sms-item, .message-item, .inbox-item, li, tr'):
        txt = item.get_text(separator=' ', strip=True)
        if len(txt) > 8 and re.search(r'\d{4,8}', txt) and 'quackr' not in txt.lower():
            messages.append({
                'from': guess_sender(txt),
                'body': txt[:400],
                'otp': extract_otp(txt),
                'time': int(time.time()),
            })
        if len(messages) >= 15:
            break
    return messages


def scrape_anonymsms(number_e164):
    """anonymsms.com — /number/{e164}/"""
    num = number_e164.lstrip('+')
    url = f"https://anonymsms.com/number/{num}/"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    messages = []
    for item in soup.select('.sms, .message, .inbox-row, li, tr, .alert'):
        txt = item.get_text(separator=' ', strip=True)
        if len(txt) > 8 and re.search(r'\d{4,8}', txt):
            messages.append({
                'from': guess_sender(txt),
                'body': txt[:400],
                'otp': extract_otp(txt),
                'time': int(time.time()),
            })
        if len(messages) >= 15:
            break
    return messages


def scrape_smsonline(number_e164):
    """smsonline.cloud"""
    num = number_e164.lstrip('+')
    url = f"https://www.smsonline.cloud/phone/{num}/"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    messages = []
    for item in soup.select('.message, .sms-content, li, tr, .card-body'):
        txt = item.get_text(separator=' ', strip=True)
        if len(txt) > 8 and re.search(r'\d{4,8}', txt):
            messages.append({
                'from': guess_sender(txt),
                'body': txt[:400],
                'otp': extract_otp(txt),
                'time': int(time.time()),
            })
        if len(messages) >= 15:
            break
    return messages


# ─────────────────────────────────────────────
# NUMBER LIST SCRAPERS
# ─────────────────────────────────────────────

def fetch_numbers_receive_smss():
    """Scrape live number list from receive-smss.com"""
    url = "https://receive-smss.com/"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    numbers = []
    country_flag_map = {
        'United States': ('🇺🇸', 'us', '+1'),
        'USA': ('🇺🇸', 'us', '+1'),
        'United Kingdom': ('🇬🇧', 'uk', '+44'),
        'UK': ('🇬🇧', 'uk', '+44'),
        'India': ('🇮🇳', 'in', '+91'),
        'Russia': ('🇷🇺', 'ru', '+7'),
        'Germany': ('🇩🇪', 'de', '+49'),
        'France': ('🇫🇷', 'fr', '+33'),
        'Canada': ('🇨🇦', 'ca', '+1'),
        'Sweden': ('🇸🇪', 'se', '+46'),
        'Netherlands': ('🇳🇱', 'nl', '+31'),
        'Australia': ('🇦🇺', 'au', '+61'),
        'Brazil': ('🇧🇷', 'br', '+55'),
        'Indonesia': ('🇮🇩', 'id', '+62'),
        'Philippines': ('🇵🇭', 'ph', '+63'),
        'Poland': ('🇵🇱', 'pl', '+48'),
    }

    # Try finding number links like /sms/123456789/
    for a in soup.find_all('a', href=re.compile(r'/sms/\d+')):
        href = a['href']
        m = re.search(r'/sms/(\d+)/', href)
        if not m:
            continue
        digits = m.group(1)
        # Get country from nearby text
        parent = a.find_parent(['div', 'li', 'tr', 'td'])
        country_text = parent.get_text(strip=True) if parent else ''
        flag, code, prefix = '🌐', 'us', '+1'
        for cname, (f, c, p) in country_flag_map.items():
            if cname.lower() in country_text.lower():
                flag, code, prefix = f, c, p
                break
        # Format number
        display = f"{prefix} {digits[len(prefix.replace('+','')):]}"
        numbers.append({
            'number': f"+{digits}",
            'display': f"+{digits}",
            'country': code,
            'flag': flag,
            'label': country_text.split()[0] if country_text else 'Unknown',
            'source': 'receive-smss.com',
            'url': f"https://receive-smss.com/sms/{digits}/",
            'digits': digits,
        })
        if len(numbers) >= 30:
            break

    # Also try h5/h4 tags with phone numbers
    for tag in soup.find_all(['h5', 'h4', 'h3', 'strong', 'span'], string=re.compile(r'\+\d{7,}')):
        txt = tag.get_text(strip=True)
        m = re.search(r'\+?(\d{7,15})', txt)
        if not m:
            continue
        digits = m.group(1)
        if any(n['digits'] == digits for n in numbers):
            continue
        numbers.append({
            'number': f"+{digits}",
            'display': f"+{digits}",
            'country': 'us',
            'flag': '🌐',
            'label': 'Unknown',
            'source': 'receive-smss.com',
            'url': f"https://receive-smss.com/sms/{digits}/",
            'digits': digits,
        })
        if len(numbers) >= 40:
            break

    return numbers


def fetch_numbers_quackr():
    """Scrape live number list from quackr.io"""
    urls = [
        "https://quackr.io/temporary-numbers/united-states",
        "https://quackr.io/temporary-numbers/united-kingdom",
        "https://quackr.io/temporary-numbers/india",
    ]
    numbers = []
    meta = {
        'united-states': ('🇺🇸', 'us'),
        'united-kingdom': ('🇬🇧', 'uk'),
        'india': ('🇮🇳', 'in'),
    }
    for url in urls:
        r = safe_get(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, 'lxml')
        ckey = url.split('/')[-1]
        flag, code = meta.get(ckey, ('🌐', 'us'))
        for a in soup.find_all('a', href=re.compile(r'/temporary-numbers/.+/\d+')):
            href = a['href']
            m = re.search(r'/temporary-numbers/.+/(\d+)$', href)
            if not m:
                continue
            digits = m.group(1)
            if any(n['digits'] == digits for n in numbers):
                continue
            numbers.append({
                'number': f"+{digits}",
                'display': f"+{digits}",
                'country': code,
                'flag': flag,
                'label': ckey.replace('-', ' ').title(),
                'source': 'quackr.io',
                'url': f"https://quackr.io/temporary-numbers/{ckey}/{digits}",
                'digits': digits,
            })
            if len(numbers) >= 30:
                break
        time.sleep(0.5)
    return numbers


def fetch_numbers_receivesms_co():
    """Scrape from receivesms.co"""
    url = "https://www.receivesms.co/free-phone-numbers/"
    r = safe_get(url)
    if not r:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    numbers = []
    for a in soup.find_all('a', href=re.compile(r'phone-number/\d+')):
        href = a['href']
        m = re.search(r'phone-number/(\d+)', href)
        if not m:
            continue
        digits = m.group(1)
        if any(n['digits'] == digits for n in numbers):
            continue
        txt = a.get_text(strip=True)
        numbers.append({
            'number': f"+{digits}",
            'display': f"+{digits}",
            'country': 'us',
            'flag': '🌐',
            'label': txt or 'Number',
            'source': 'receivesms.co',
            'url': href if href.startswith('http') else f"https://www.receivesms.co{href}",
            'digits': digits,
        })
        if len(numbers) >= 20:
            break
    return numbers


# ─────────────────────────────────────────────
# CACHE  (simple in-memory, refreshes every 5 min)
# ─────────────────────────────────────────────
_cache = {
    'numbers': [],
    'numbers_ts': 0,
}
CACHE_TTL = 300  # 5 minutes


def get_cached_numbers():
    now = time.time()
    if now - _cache['numbers_ts'] > CACHE_TTL or not _cache['numbers']:
        log.info("Refreshing number list from sources...")
        nums = []
        try:
            nums += fetch_numbers_receive_smss()
        except Exception as e:
            log.error(f"receive-smss scrape error: {e}")
        try:
            nums += fetch_numbers_quackr()
        except Exception as e:
            log.error(f"quackr scrape error: {e}")
        try:
            nums += fetch_numbers_receivesms_co()
        except Exception as e:
            log.error(f"receivesms.co scrape error: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for n in nums:
            if n['digits'] not in seen:
                seen.add(n['digits'])
                unique.append(n)

        if unique:
            _cache['numbers'] = unique
            _cache['numbers_ts'] = now
            log.info(f"Fetched {len(unique)} unique numbers")
        else:
            log.warning("No numbers fetched, using fallback list")
            _cache['numbers'] = FALLBACK_NUMBERS
            _cache['numbers_ts'] = now

    return _cache['numbers']


# ─────────────────────────────────────────────
# FALLBACK numbers (hardcoded, updated manually)
# ─────────────────────────────────────────────
FALLBACK_NUMBERS = [
    {'number':'+12086957555','display':'+1 (208) 695-7555','country':'us','flag':'🇺🇸','label':'USA','source':'receive-smss.com','url':'https://receive-smss.com/sms/12086957555/','digits':'12086957555'},
    {'number':'+16475078974','display':'+1 (647) 507-8974','country':'us','flag':'🇺🇸','label':'USA','source':'receive-smss.com','url':'https://receive-smss.com/sms/16475078974/','digits':'16475078974'},
    {'number':'+17753139681','display':'+1 (775) 313-9681','country':'us','flag':'🇺🇸','label':'USA','source':'receive-smss.com','url':'https://receive-smss.com/sms/17753139681/','digits':'17753139681'},
    {'number':'+447700164114','display':'+44 7700 164114','country':'uk','flag':'🇬🇧','label':'UK','source':'receive-smss.com','url':'https://receive-smss.com/sms/447700164114/','digits':'447700164114'},
    {'number':'+447893978024','display':'+44 7893 978024','country':'uk','flag':'🇬🇧','label':'UK','source':'receive-smss.com','url':'https://receive-smss.com/sms/447893978024/','digits':'447893978024'},
    {'number':'+919876543210','display':'+91 98765 43210','country':'in','flag':'🇮🇳','label':'India','source':'receive-smss.com','url':'https://receive-smss.com/sms/919876543210/','digits':'919876543210'},
    {'number':'+917428730894','display':'+91 74287 30894','country':'in','flag':'🇮🇳','label':'India','source':'receive-smss.com','url':'https://receive-smss.com/sms/917428730894/','digits':'917428730894'},
    {'number':'+79263121838','display':'+7 926 312-1838','country':'ru','flag':'🇷🇺','label':'Russia','source':'receive-smss.com','url':'https://receive-smss.com/sms/79263121838/','digits':'79263121838'},
    {'number':'+4915207820381','display':'+49 1520 782 0381','country':'de','flag':'🇩🇪','label':'Germany','source':'receive-smss.com','url':'https://receive-smss.com/sms/4915207820381/','digits':'4915207820381'},
    {'number':'+33751897412','display':'+33 7 51 89 74 12','country':'fr','flag':'🇫🇷','label':'France','source':'receive-smss.com','url':'https://receive-smss.com/sms/33751897412/','digits':'33751897412'},
    {'number':'+16047873558','display':'+1 (604) 787-3558','country':'ca','flag':'🇨🇦','label':'Canada','source':'receive-smss.com','url':'https://receive-smss.com/sms/16047873558/','digits':'16047873558'},
    {'number':'+46726622381','display':'+46 72 662 2381','country':'se','flag':'🇸🇪','label':'Sweden','source':'receive-smss.com','url':'https://receive-smss.com/sms/46726622381/','digits':'46726622381'},
    {'number':'+31620000548','display':'+31 6 2000 0548','country':'nl','flag':'🇳🇱','label':'Netherlands','source':'receive-smss.com','url':'https://receive-smss.com/sms/31620000548/','digits':'31620000548'},
]


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/numbers')
def api_numbers():
    """Return live scraped number list."""
    country = request.args.get('country', 'all')
    try:
        nums = get_cached_numbers()
    except Exception as e:
        log.error(f"get_cached_numbers error: {e}")
        nums = FALLBACK_NUMBERS

    if country != 'all':
        nums = [n for n in nums if n.get('country') == country]

    return jsonify({'ok': True, 'numbers': nums, 'count': len(nums)})


@app.route('/api/messages/<path:number>')
def api_messages(number):
    """
    Scrape SMS inbox for a given number.
    number = e164 like +12086957555  or digits only
    source query param = receive-smss | quackr | receivesms | anonymsms | smsonline
    """
    source = request.args.get('source', 'receive-smss.com')
    digits = re.sub(r'\D', '', number)

    messages = []
    error = None

    try:
        if 'quackr' in source:
            messages = scrape_quackr(f"+{digits}")
        elif 'receivesms.co' in source or 'receivesms' in source:
            messages = scrape_receivesms_co(digits)
        elif 'anonymsms' in source:
            messages = scrape_anonymsms(f"+{digits}")
        elif 'smsonline' in source:
            messages = scrape_smsonline(f"+{digits}")
        else:
            # Default: receive-smss.com
            messages = scrape_receive_smss(digits)

        # If primary failed, try receive-smss as fallback
        if not messages and 'receive-smss' not in source:
            log.info(f"Primary scrape empty, trying receive-smss fallback for {digits}")
            messages = scrape_receive_smss(digits)

    except Exception as e:
        log.error(f"Scrape error for {number}: {e}")
        error = str(e)

    return jsonify({
        'ok': True,
        'number': f"+{digits}",
        'source': source,
        'messages': messages,
        'count': len(messages),
        'error': error,
        'timestamp': int(time.time()),
    })


@app.route('/api/status')
def api_status():
    return jsonify({'ok': True, 'status': 'running', 'ts': int(time.time())})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
