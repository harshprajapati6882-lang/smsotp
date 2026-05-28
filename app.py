"""
TempSMS — Real Python backend
Scrapes live numbers & SMS from receive-smss.com server-side
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

# ─── ROTATING HEADERS ───
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    },
]

COUNTRY_MAP = {
    "united states": ("🇺🇸", "us"),
    "united kingdom": ("🇬🇧", "uk"),
    "india":          ("🇮🇳", "in"),
    "russia":         ("🇷🇺", "ru"),
    "germany":        ("🇩🇪", "de"),
    "france":         ("🇫🇷", "fr"),
    "canada":         ("🇨🇦", "ca"),
    "sweden":         ("🇸🇪", "se"),
    "netherlands":    ("🇳🇱", "nl"),
    "australia":      ("🇦🇺", "au"),
    "brazil":         ("🇧🇷", "br"),
    "indonesia":      ("🇮🇩", "id"),
    "philippines":    ("🇵🇭", "ph"),
    "poland":         ("🇵🇱", "pl"),
    "ukraine":        ("🇺🇦", "ua"),
    "czech republic": ("🇨🇿", "cz"),
    "romania":        ("🇷🇴", "ro"),
    "spain":          ("🇪🇸", "es"),
    "italy":          ("🇮🇹", "it"),
    "portugal":       ("🇵🇹", "pt"),
    "finland":        ("🇫🇮", "fi"),
    "norway":         ("🇳🇴", "no"),
    "denmark":        ("🇩🇰", "dk"),
    "belgium":        ("🇧🇪", "be"),
    "austria":        ("🇦🇹", "at"),
    "switzerland":    ("🇨🇭", "ch"),
    "hong kong":      ("🇭🇰", "hk"),
    "china":          ("🇨🇳", "cn"),
    "japan":          ("🇯🇵", "jp"),
    "south korea":    ("🇰🇷", "kr"),
    "vietnam":        ("🇻🇳", "vn"),
    "thailand":       ("🇹🇭", "th"),
    "malaysia":       ("🇲🇾", "my"),
    "nigeria":        ("🇳🇬", "ng"),
    "ghana":          ("🇬🇭", "gh"),
    "kenya":          ("🇰🇪", "ke"),
    "south africa":   ("🇿🇦", "za"),
    "mexico":         ("🇲🇽", "mx"),
    "colombia":       ("🇨🇴", "co"),
    "argentina":      ("🇦🇷", "ar"),
    "pakistan":       ("🇵🇰", "pk"),
    "bangladesh":     ("🇧🇩", "bd"),
    "turkey":         ("🇹🇷", "tr"),
    "israel":         ("🇮🇱", "il"),
    "saudi arabia":   ("🇸🇦", "sa"),
    "egypt":          ("🇪🇬", "eg"),
}

def get_headers():
    return random.choice(HEADERS_LIST)

def safe_get(url, timeout=14):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=get_headers(), timeout=timeout)
            if r.status_code == 200:
                return r
            log.warning(f"[{attempt+1}] HTTP {r.status_code} → {url}")
        except Exception as e:
            log.warning(f"[{attempt+1}] Error: {e}")
        time.sleep(1.5 * (attempt + 1))
    return None


# ─── OTP HELPERS ───
OTP_PATTERNS = [
    r'(?:code|Code|CODE|pin|PIN|otp|OTP)[^\d]{0,5}(\d{4,8})',
    r'(\d{6})',
    r'(\d{4})',
    r'(\d{8})',
    r'(\d{5})',
    r'[-:\s](\d{4,8})\b',
]

SENDER_MAP = {
    'google': 'GOOGLE', 'gmail': 'GOOGLE',
    'whatsapp': 'WHATSAPP', 'wa.me': 'WHATSAPP',
    'telegram': 'TELEGRAM',
    'facebook': 'FACEBOOK', 'fb.com': 'FACEBOOK',
    'instagram': 'INSTAGRAM',
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
    'dent': 'DENT',
    'kakao': 'KAKAOTALK',
    'shopee': 'SHOPEE',
    'vk': 'VK',
    'zalo': 'ZALO',
    'listia': 'LISTIA',
    'steem': 'STEEM',
    'nvidia': 'NVIDIA',
    'muslim': 'MUSLIMMATRIMONY',
}

def extract_otp(text):
    for pattern in OTP_PATTERNS:
        m = re.search(pattern, text)
        if m:
            code = re.sub(r'\D', '', m.group(1))
            if 4 <= len(code) <= 8:
                return code
    return None

def guess_sender(text, sender_raw=""):
    combined = (text + " " + sender_raw).lower()
    for key, val in SENDER_MAP.items():
        if key in combined:
            return val
    if sender_raw and re.match(r'^[A-Za-z][A-Za-z0-9\-_]{1,20}$', sender_raw.strip()):
        return sender_raw.strip().upper()
    return 'SMS'


# ─── SCRAPE NUMBER LIST FROM receive-smss.com ───
def fetch_numbers_live():
    """Scrape the current live numbers listed on receive-smss.com homepage."""
    url = "https://receive-smss.com/"
    r = safe_get(url)
    if not r:
        log.error("Could not fetch receive-smss.com homepage")
        return []

    soup = BeautifulSoup(r.text, 'lxml')
    numbers = []
    seen = set()

    # Find all links matching /sms/DIGITS/
    for a in soup.find_all('a', href=re.compile(r'https://receive-smss\.com/sms/\d+/')):
        href = a['href'].strip()
        m = re.search(r'/sms/(\d+)/', href)
        if not m:
            continue
        digits = m.group(1)
        if digits in seen:
            continue
        seen.add(digits)

        # Find country from nearby text in parent element
        parent = a.find_parent(['div', 'li', 'article', 'section'])
        country_text = parent.get_text(separator=' ', strip=True).lower() if parent else ''

        flag, code = '🌐', 'us'
        label = 'Unknown'
        for cname, (f, c) in COUNTRY_MAP.items():
            if cname in country_text:
                flag, code, label = f, c, cname.title()
                break

        # Also check alt text of flag image
        img = a.find('img') or (parent.find('img') if parent else None)
        if img and label == 'Unknown':
            alt = (img.get('alt', '') + ' ' + img.get('src', '')).lower()
            for cname, (f, c) in COUNTRY_MAP.items():
                if cname in alt or c in alt:
                    flag, code, label = f, c, cname.title()
                    break

        numbers.append({
            'number':  f"+{digits}",
            'display': f"+{digits}",
            'country': code,
            'flag':    flag,
            'label':   label,
            'source':  'receive-smss.com',
            'url':     href,
            'digits':  digits,
        })

    log.info(f"Fetched {len(numbers)} numbers from receive-smss.com")
    return numbers


# ─── SCRAPE SMS INBOX FROM receive-smss.com ───
def fetch_messages_live(digits):
    """
    Scrape the actual SMS inbox page for a specific number.
    Parses the real HTML structure of receive-smss.com/sms/{digits}/
    """
    url = f"https://receive-smss.com/sms/{digits}/"
    r = safe_get(url)
    if not r:
        return [], "Could not reach receive-smss.com"

    soup = BeautifulSoup(r.text, 'lxml')

    # Check if number page exists
    body_text = soup.get_text()
    if "nothing was found" in body_text.lower() or "404" in body_text[:200]:
        return [], f"Number +{digits} not found on receive-smss.com"

    messages = []

    # ── Strategy 1: Look for Message/Sender/Time triplets ──
    # The site renders messages as sections with "Message", "Sender", "Time" labels
    all_text_blocks = soup.find_all(string=re.compile(r'.{5,}'))

    # Find all label-value pairs
    raw_messages = []
    current = {}

    for tag in soup.find_all(['p', 'div', 'td', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'li']):
        txt = tag.get_text(strip=True)
        if not txt:
            continue
        low = txt.lower()
        if low == 'message':
            if current.get('body'):
                raw_messages.append(dict(current))
            current = {}
        elif low == 'sender':
            pass
        elif low == 'time':
            pass
        elif current is not None and 'body' not in current and len(txt) > 3:
            # This could be the message body after a "Message" label
            if re.search(r'\d{4,8}|verif|code|otp|pin', txt, re.I):
                current['body'] = txt
        elif 'body' in current and 'sender' not in current and len(txt) > 1:
            current['sender'] = txt
        elif 'body' in current and 'sender' in current and 'time' not in current:
            current['time_text'] = txt

    if current.get('body'):
        raw_messages.append(current)

    # ── Strategy 2: Direct regex scan of full page text ──
    # Find message blocks by looking for sequences: body text → sender → time
    full_text = soup.get_text(separator='\n')
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for lines that are actual SMS content (contain digits or keywords)
        if (
            len(line) > 5 and len(line) < 500
            and re.search(r'\d{4,8}', line)
            and not any(x in line.lower() for x in [
                'receive', 'temporary', 'number', 'cookie', 'privacy',
                'chrome', 'extension', 'refresh', 'select', 'signup',
                'install', 'click', 'navigate', 'receive-smss', 'skip'
            ])
        ):
            # Try to find sender in next few lines
            sender_raw = ''
            time_raw = ''
            for j in range(i+1, min(i+5, len(lines))):
                nxt = lines[j]
                if re.match(r'^\d{7,15}$', nxt) or re.match(r'^[A-Za-z][A-Za-z0-9\-_]{1,20}$', nxt):
                    sender_raw = nxt
                elif 'ago' in nxt.lower() or 'minute' in nxt.lower() or 'hour' in nxt.lower() or 'second' in nxt.lower():
                    time_raw = nxt
                    break

            # Avoid duplicates
            if not any(m['body'] == line for m in messages):
                otp = extract_otp(line)
                messages.append({
                    'from':      guess_sender(line, sender_raw),
                    'body':      line,
                    'otp':       otp,
                    'sender':    sender_raw,
                    'time_text': time_raw,
                    'time':      int(time.time()),
                })
        i += 1
        if len(messages) >= 20:
            break

    # ── Strategy 3: BeautifulSoup targeted selectors ──
    if not messages:
        selectors = [
            'div.border', 'div.card', 'div.message', '.sms',
            'table tr', 'ul li', '.inbox-item',
        ]
        for sel in selectors:
            items = soup.select(sel)
            for item in items:
                txt = item.get_text(separator=' ', strip=True)
                if (
                    len(txt) > 8 and len(txt) < 500
                    and re.search(r'\d{4,8}', txt)
                    and not any(x in txt.lower() for x in ['receive-smss', 'cookie', 'privacy'])
                ):
                    messages.append({
                        'from':  guess_sender(txt),
                        'body':  txt[:400],
                        'otp':   extract_otp(txt),
                        'time':  int(time.time()),
                    })
                if len(messages) >= 20:
                    break
            if messages:
                break

    log.info(f"Scraped {len(messages)} messages for +{digits}")
    return messages, None


# ─── CACHE ───
_cache = {'numbers': [], 'ts': 0}
CACHE_TTL = 300  # 5 minutes

def get_numbers_cached():
    now = time.time()
    if now - _cache['ts'] > CACHE_TTL or not _cache['numbers']:
        log.info("Refreshing number list...")
        nums = []
        try:
            nums = fetch_numbers_live()
        except Exception as e:
            log.error(f"Fetch numbers error: {e}")
        if nums:
            _cache['numbers'] = nums
            _cache['ts'] = now
        else:
            log.warning("Fetch returned 0 numbers, cache unchanged")
    return _cache['numbers']


# ─── ROUTES ───
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/numbers')
def api_numbers():
    country = request.args.get('country', 'all')
    try:
        nums = get_numbers_cached()
    except Exception as e:
        log.error(f"api_numbers error: {e}")
        nums = []

    if country != 'all':
        nums = [n for n in nums if n.get('country') == country]

    return jsonify({'ok': True, 'numbers': nums, 'count': len(nums)})


@app.route('/api/messages/<path:number>')
def api_messages(number):
    digits = re.sub(r'\D', '', number)
    if not digits:
        return jsonify({'ok': False, 'error': 'Invalid number', 'messages': []})

    messages, error = [], None
    try:
        messages, error = fetch_messages_live(digits)
    except Exception as e:
        log.error(f"api_messages error for {digits}: {e}")
        error = str(e)

    return jsonify({
        'ok':        True,
        'number':    f"+{digits}",
        'source':    'receive-smss.com',
        'messages':  messages,
        'count':     len(messages),
        'error':     error,
        'timestamp': int(time.time()),
        'url':       f"https://receive-smss.com/sms/{digits}/",
    })


@app.route('/api/status')
def api_status():
    return jsonify({'ok': True, 'status': 'running', 'cached_numbers': len(_cache['numbers']), 'ts': int(time.time())})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
