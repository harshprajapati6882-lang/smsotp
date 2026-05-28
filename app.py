"""
TempSMS — Real Python backend
Scrapes live numbers & SMS from MULTIPLE free sites:
  1. receive-smss.com
  2. receivesms.co
  3. quackr.io
  4. 7sim.net
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
import re
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────
# HEADERS
# ─────────────────────────────────────────────────────────────
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def hdrs(referer=""):
    h = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        h["Referer"] = referer
    return h

def safe_get(url, timeout=14, referer=""):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=hdrs(referer), timeout=timeout)
            log.info(f"GET {url} → {r.status_code} ({len(r.text)} bytes)")
            if r.status_code == 200:
                return r
        except Exception as e:
            log.warning(f"[{attempt+1}] {url} → {e}")
        time.sleep(1.5 * (attempt + 1))
    return None

# ─────────────────────────────────────────────────────────────
# COUNTRY LOOKUP
# ─────────────────────────────────────────────────────────────
COUNTRY_DB = {
    "united states": ("🇺🇸", "us"), "usa": ("🇺🇸", "us"),
    "united kingdom": ("🇬🇧", "uk"), "uk": ("🇬🇧", "uk"),
    "india": ("🇮🇳", "in"),
    "russia": ("🇷🇺", "ru"),
    "germany": ("🇩🇪", "de"),
    "france": ("🇫🇷", "fr"),
    "canada": ("🇨🇦", "ca"),
    "sweden": ("🇸🇪", "se"),
    "netherlands": ("🇳🇱", "nl"),
    "australia": ("🇦🇺", "au"),
    "brazil": ("🇧🇷", "br"),
    "indonesia": ("🇮🇩", "id"),
    "philippines": ("🇵🇭", "ph"),
    "poland": ("🇵🇱", "pl"),
    "ukraine": ("🇺🇦", "ua"),
    "spain": ("🇪🇸", "es"),
    "italy": ("🇮🇹", "it"),
    "portugal": ("🇵🇹", "pt"),
    "finland": ("🇫🇮", "fi"),
    "norway": ("🇳🇴", "no"),
    "denmark": ("🇩🇰", "dk"),
    "belgium": ("🇧🇪", "be"),
    "austria": ("🇦🇹", "at"),
    "switzerland": ("🇨🇭", "ch"),
    "hong kong": ("🇭🇰", "hk"),
    "china": ("🇨🇳", "cn"),
    "japan": ("🇯🇵", "jp"),
    "south korea": ("🇰🇷", "kr"),
    "vietnam": ("🇻🇳", "vn"),
    "thailand": ("🇹🇭", "th"),
    "malaysia": ("🇲🇾", "my"),
    "nigeria": ("🇳🇬", "ng"),
    "ghana": ("🇬🇭", "gh"),
    "kenya": ("🇰🇪", "ke"),
    "south africa": ("🇿🇦", "za"),
    "mexico": ("🇲🇽", "mx"),
    "colombia": ("🇨🇴", "co"),
    "argentina": ("🇦🇷", "ar"),
    "pakistan": ("🇵🇰", "pk"),
    "bangladesh": ("🇧🇩", "bd"),
    "turkey": ("🇹🇷", "tr"),
    "saudi arabia": ("🇸🇦", "sa"),
    "egypt": ("🇪🇬", "eg"),
    "croatia": ("🇭🇷", "hr"),
    "czech republic": ("🇨🇿", "cz"),
    "romania": ("🇷🇴", "ro"),
    "serbia": ("🇷🇸", "rs"),
    "israel": ("🇮🇱", "il"),
}

FLAG_IMG_MAP = {
    "/us.png": ("🇺🇸", "us", "USA"),
    "/gb.png": ("🇬🇧", "uk", "UK"),
    "/uk.png": ("🇬🇧", "uk", "UK"),
    "/in.png": ("🇮🇳", "in", "India"),
    "/ru.png": ("🇷🇺", "ru", "Russia"),
    "/de.png": ("🇩🇪", "de", "Germany"),
    "/fr.png": ("🇫🇷", "fr", "France"),
    "/ca.png": ("🇨🇦", "ca", "Canada"),
    "/se.png": ("🇸🇪", "se", "Sweden"),
    "/nl.png": ("🇳🇱", "nl", "Netherlands"),
    "/au.png": ("🇦🇺", "au", "Australia"),
    "/br.png": ("🇧🇷", "br", "Brazil"),
    "/id.png": ("🇮🇩", "id", "Indonesia"),
    "/ph.png": ("🇵🇭", "ph", "Philippines"),
    "/pl.png": ("🇵🇱", "pl", "Poland"),
    "/ua.png": ("🇺🇦", "ua", "Ukraine"),
    "/es.png": ("🇪🇸", "es", "Spain"),
    "/it.png": ("🇮🇹", "it", "Italy"),
    "/pt.png": ("🇵🇹", "pt", "Portugal"),
    "/fi.png": ("🇫🇮", "fi", "Finland"),
    "/no.png": ("🇳🇴", "no", "Norway"),
    "/dk.png": ("🇩🇰", "dk", "Denmark"),
    "/be.png": ("🇧🇪", "be", "Belgium"),
    "/at.png": ("🇦🇹", "at", "Austria"),
    "/ch.png": ("🇨🇭", "ch", "Switzerland"),
    "/hk.png": ("🇭🇰", "hk", "Hong Kong"),
    "/cn.png": ("🇨🇳", "cn", "China"),
    "/jp.png": ("🇯🇵", "jp", "Japan"),
    "/kr.png": ("🇰🇷", "kr", "South Korea"),
    "/vn.png": ("🇻🇳", "vn", "Vietnam"),
    "/th.png": ("🇹🇭", "th", "Thailand"),
    "/my.png": ("🇲🇾", "my", "Malaysia"),
    "/ng.png": ("🇳🇬", "ng", "Nigeria"),
    "/za.png": ("🇿🇦", "za", "South Africa"),
    "/mx.png": ("🇲🇽", "mx", "Mexico"),
    "/pk.png": ("🇵🇰", "pk", "Pakistan"),
    "/bd.png": ("🇧🇩", "bd", "Bangladesh"),
    "/tr.png": ("🇹🇷", "tr", "Turkey"),
    "/hr.png": ("🇭🇷", "hr", "Croatia"),
    "/cz.png": ("🇨🇿", "cz", "Czech Republic"),
    "/ro.png": ("🇷🇴", "ro", "Romania"),
    "/il.png": ("🇮🇱", "il", "Israel"),
    "/sa.png": ("🇸🇦", "sa", "Saudi Arabia"),
}

def country_from_text(text):
    low = text.lower()
    for name, (flag, code) in COUNTRY_DB.items():
        if name in low:
            return flag, code, name.title()
    return "🌐", "us", "Unknown"

def country_from_img_src(src):
    for suffix, (flag, code, label) in FLAG_IMG_MAP.items():
        if src.endswith(suffix):
            return flag, code, label
    return None


# ─────────────────────────────────────────────────────────────
# OTP + SENDER HELPERS
# ─────────────────────────────────────────────────────────────
OTP_RE = [
    r'(?:code|pin|otp|verif\w*)[^\d]{0,8}(\d{4,8})',
    r'\*{0,2}(\d{6})\*{0,2}',
    r'\b(\d{6})\b',
    r'\b(\d{4})\b',
    r'\b(\d{8})\b',
    r'\b(\d{5})\b',
]

SENDER_KW = {
    'google':'GOOGLE','gmail':'GOOGLE','whatsapp':'WHATSAPP','wa.me':'WHATSAPP',
    'telegram':'TELEGRAM','facebook':'FACEBOOK','instagram':'INSTAGRAM',
    'amazon':'AMAZON','twitter':'TWITTER','x.com':'TWITTER','tiktok':'TIKTOK',
    'uber':'UBER','netflix':'NETFLIX','microsoft':'MICROSOFT','apple':'APPLE',
    'paypal':'PAYPAL','discord':'DISCORD','snapchat':'SNAPCHAT','linkedin':'LINKEDIN',
    'dent':'DENT','kakao':'KAKAOTALK','shopee':'SHOPEE','vk':'VK','zalo':'ZALO',
}

def extract_otp(text):
    for pat in OTP_RE:
        m = re.search(pat, text, re.I)
        if m:
            code = re.sub(r'\D', '', m.group(1))
            if 4 <= len(code) <= 8:
                return code
    return None

def guess_sender(text, sender_raw=""):
    combined = (text + " " + sender_raw).lower()
    for kw, label in SENDER_KW.items():
        if kw in combined:
            return label
    if sender_raw and re.match(r'^[A-Za-z][A-Za-z0-9_\-]{1,25}$', sender_raw.strip()):
        return sender_raw.strip().upper()
    return "SMS"


# ─────────────────────────────────────────────────────────────
# ══ SOURCE 1: receive-smss.com ══
# ─────────────────────────────────────────────────────────────
def scrape_numbers_receive_smss():
    """
    Scrape the homepage HTML as raw text and extract all number links
    using regex — much more reliable than BeautifulSoup on Render.
    """
    r = safe_get("https://receive-smss.com/")
    if not r:
        return []

    html = r.text
    nums = []
    seen = set()

    # Find all: href="https://receive-smss.com/sms/DIGITS/"
    # and nearby country text and flag image src
    # Pattern: find each number block — the URL, nearby flag img src, nearby country name
    blocks = re.findall(
        r'href="(https://receive-smss\.com/sms/(\d+)/)"[^>]*>.*?'
        r'(?:src="([^"]*countries[^"]*\.png)")?.*?'
        r'(\+\d[\d\s\-]{5,})',
        html, re.S
    )

    if not blocks:
        # Simpler fallback: just find all /sms/DIGITS/ links + nearby text
        links = re.findall(r'/sms/(\d{7,15})/', html)
        # Find country+flag pairs separately
        img_srcs = re.findall(r'src="([^"]*countries[^"]*\.png)"', html)
        countries_raw = re.findall(
            r'\+\d[\d ]{5,}\s*\n\s*([\w ]+)\n',
            html
        )
        for i, digits in enumerate(dict.fromkeys(links)):  # deduplicate preserving order
            img_src = img_srcs[i] if i < len(img_srcs) else ""
            country_raw = countries_raw[i].strip() if i < len(countries_raw) else ""

            flag, code, label = "🌐", "us", "Unknown"
            if img_src:
                result = country_from_img_src(img_src)
                if result:
                    flag, code, label = result
            if label == "Unknown" and country_raw:
                flag, code, label = country_from_text(country_raw)

            if digits not in seen:
                seen.add(digits)
                nums.append({
                    "number":  f"+{digits}",
                    "display": f"+{digits}",
                    "country": code,
                    "flag":    flag,
                    "label":   label,
                    "source":  "receive-smss.com",
                    "url":     f"https://receive-smss.com/sms/{digits}/",
                    "digits":  digits,
                })
        log.info(f"receive-smss (fallback): {len(nums)} numbers")
        return nums

    for (url, digits, img_src, _phone_raw) in blocks:
        if digits in seen:
            continue
        seen.add(digits)

        # Grab a small window around this block for country name
        pos = html.find(f"/sms/{digits}/")
        window = html[max(0, pos-200):pos+500]

        flag, code, label = "🌐", "us", "Unknown"
        if img_src:
            result = country_from_img_src(img_src)
            if result:
                flag, code, label = result
        if label == "Unknown":
            flag, code, label = country_from_text(window)

        nums.append({
            "number":  f"+{digits}",
            "display": f"+{digits}",
            "country": code,
            "flag":    flag,
            "label":   label,
            "source":  "receive-smss.com",
            "url":     url,
            "digits":  digits,
        })

    log.info(f"receive-smss: {len(nums)} numbers")
    return nums


def scrape_sms_receive_smss(digits):
    """Scrape inbox of a specific number on receive-smss.com using regex on raw HTML."""
    url = f"https://receive-smss.com/sms/{digits}/"
    r = safe_get(url, referer="https://receive-smss.com/")
    if not r:
        return [], "Could not reach receive-smss.com"

    html = r.text

    if "nothing was found" in html.lower():
        return [], f"Number +{digits} no longer exists on receive-smss.com"

    msgs = []

    # Extract message blocks: the page has patterns like:
    # <strong>ACTUAL MESSAGE TEXT</strong>  then sender, then "X minutes ago"
    # Strategy: find all bold/strong text that looks like SMS
    strong_texts = re.findall(r'<strong[^>]*>(.*?)</strong>', html, re.S)
    # Also find plain text blocks between certain tags
    # Pattern: Message content appears between specific divs

    # Best approach: extract raw text lines and find SMS-like lines
    # Remove all HTML tags
    clean = re.sub(r'<[^>]+>', '\n', html)
    clean = re.sub(r'&[a-z]+;', ' ', clean)
    clean = re.sub(r'\s+', '\n', clean).strip()

    lines = [l.strip() for l in clean.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip navigation/UI lines
        if any(skip in line.lower() for skip in [
            'receive-smss', 'cookie', 'privacy', 'chrome', 'extension',
            'refresh', 'registration', 'choose', 'select', 'await',
            'how to', 'step', 'video', 'tutorial', 'click', 'install',
            'skip the', 'temp', 'update messages', 'give me another',
            'free sms', 'temporary phone', 'website', 'verify',
            '©', 'copyright', 'terms', 'contact', 'about',
        ]):
            i += 1
            continue

        # Line must have digits 4-8 long to be an SMS
        if not re.search(r'\b\d{4,8}\b', line):
            i += 1
            continue

        # Line must be reasonable SMS length
        if len(line) < 6 or len(line) > 400:
            i += 1
            continue

        # Try to find sender + time in next few lines
        sender_raw = ""
        time_raw = ""
        for j in range(i + 1, min(i + 6, len(lines))):
            nxt = lines[j]
            if re.match(r'^\d{7,15}$', nxt):
                sender_raw = nxt
            elif re.match(r'^[A-Za-z][A-Za-z0-9_\-]{1,25}$', nxt) and not sender_raw:
                sender_raw = nxt
            elif re.search(r'\d+\s*(minute|hour|second|day)s?\s*ago', nxt, re.I):
                time_raw = nxt
                break

        # Deduplicate
        if not any(m['body'] == line for m in msgs):
            msgs.append({
                "from":      guess_sender(line, sender_raw),
                "body":      line,
                "otp":       extract_otp(line),
                "sender":    sender_raw,
                "time_text": time_raw or "just now",
                "time":      int(time.time()),
            })

        i += 1
        if len(msgs) >= 20:
            break

    log.info(f"receive-smss inbox +{digits}: {len(msgs)} messages")
    return msgs, None


# ─────────────────────────────────────────────────────────────
# ══ SOURCE 2: receivesms.co ══
# ─────────────────────────────────────────────────────────────
def scrape_numbers_receivesms_co():
    r = safe_get("https://www.receivesms.co/free-phone-numbers/")
    if not r:
        return []

    html = r.text
    nums = []
    seen = set()

    # Pattern: /XX-phone-number/DIGITS/
    matches = re.findall(
        r'href="https?://www\.receivesms\.co/([a-z]+)-phone-number/(\d+)/"',
        html
    )

    for (country_code, digits) in matches:
        if digits in seen:
            continue
        seen.add(digits)

        # Map country code to flag
        flag, code, label = "🌐", country_code, country_code.upper()
        # Try from our map using the img pattern
        cc_to_info = {
            "us": ("🇺🇸", "us", "USA"),
            "gb": ("🇬🇧", "uk", "UK"),
            "uk": ("🇬🇧", "uk", "UK"),
            "in": ("🇮🇳", "in", "India"),
            "ru": ("🇷🇺", "ru", "Russia"),
            "de": ("🇩🇪", "de", "Germany"),
            "fr": ("🇫🇷", "fr", "France"),
            "ca": ("🇨🇦", "ca", "Canada"),
            "se": ("🇸🇪", "se", "Sweden"),
            "nl": ("🇳🇱", "nl", "Netherlands"),
            "au": ("🇦🇺", "au", "Australia"),
            "br": ("🇧🇷", "br", "Brazil"),
            "es": ("🇪🇸", "es", "Spain"),
            "dk": ("🇩🇰", "dk", "Denmark"),
            "fi": ("🇫🇮", "fi", "Finland"),
            "no": ("🇳🇴", "no", "Norway"),
            "pl": ("🇵🇱", "pl", "Poland"),
            "be": ("🇧🇪", "be", "Belgium"),
        }
        if country_code in cc_to_info:
            flag, code, label = cc_to_info[country_code]

        nums.append({
            "number":  f"+{digits}",
            "display": f"+{digits}",
            "country": code,
            "flag":    flag,
            "label":   label,
            "source":  "receivesms.co",
            "url":     f"https://www.receivesms.co/{country_code}-phone-number/{digits}/",
            "digits":  digits,
        })

    log.info(f"receivesms.co: {len(nums)} numbers")
    return nums


def scrape_sms_receivesms_co(digits, country_code="us"):
    url = f"https://www.receivesms.co/{country_code}-phone-number/{digits}/"
    r = safe_get(url, referer="https://www.receivesms.co/")
    if not r:
        # Try gb prefix for UK
        if country_code == "uk":
            url = f"https://www.receivesms.co/gb-phone-number/{digits}/"
            r = safe_get(url)
        if not r:
            return [], "Could not reach receivesms.co"

    html = r.text
    clean = re.sub(r'<[^>]+>', '\n', html)
    clean = re.sub(r'&[a-z]+;', ' ', clean)
    lines = [l.strip() for l in clean.split('\n') if l.strip() and len(l.strip()) > 5]

    msgs = []
    skip_kw = ['receivesms', 'cookie', 'privacy', 'menu', 'navigation',
               'footer', 'copyright', 'free phone', 'all rights']

    for line in lines:
        if any(s in line.lower() for s in skip_kw):
            continue
        if re.search(r'\b\d{4,8}\b', line) and 6 < len(line) < 400:
            if not any(m['body'] == line for m in msgs):
                msgs.append({
                    "from":      guess_sender(line),
                    "body":      line,
                    "otp":       extract_otp(line),
                    "time_text": "recent",
                    "time":      int(time.time()),
                })
        if len(msgs) >= 15:
            break

    log.info(f"receivesms.co inbox +{digits}: {len(msgs)} messages")
    return msgs, None


# ─────────────────────────────────────────────────────────────
# ══ SOURCE 3: quackr.io ══
# ─────────────────────────────────────────────────────────────
QUACKR_COUNTRIES = [
    ("united-states", "🇺🇸", "us", "USA"),
    ("united-kingdom", "🇬🇧", "uk", "UK"),
    ("india",          "🇮🇳", "in", "India"),
    ("germany",        "🇩🇪", "de", "Germany"),
    ("france",         "🇫🇷", "fr", "France"),
    ("canada",         "🇨🇦", "ca", "Canada"),
    ("sweden",         "🇸🇪", "se", "Sweden"),
    ("netherlands",    "🇳🇱", "nl", "Netherlands"),
    ("australia",      "🇦🇺", "au", "Australia"),
    ("brazil",         "🇧🇷", "br", "Brazil"),
]

def scrape_numbers_quackr():
    nums = []
    seen = set()

    for (cslug, flag, code, label) in QUACKR_COUNTRIES:
        url = f"https://quackr.io/temporary-numbers/{cslug}"
        r = safe_get(url, referer="https://quackr.io/")
        if not r:
            continue

        html = r.text
        # Find links like /temporary-numbers/united-states/12345678901
        matches = re.findall(
            rf'/temporary-numbers/{cslug}/(\d{{7,15}})',
            html
        )
        for digits in dict.fromkeys(matches):
            if digits in seen:
                continue
            seen.add(digits)
            nums.append({
                "number":  f"+{digits}",
                "display": f"+{digits}",
                "country": code,
                "flag":    flag,
                "label":   label,
                "source":  "quackr.io",
                "url":     f"https://quackr.io/temporary-numbers/{cslug}/{digits}",
                "digits":  digits,
            })
        time.sleep(0.4)  # polite delay

    log.info(f"quackr.io: {len(nums)} numbers")
    return nums


def scrape_sms_quackr(digits, country_slug="united-states"):
    url = f"https://quackr.io/temporary-numbers/{country_slug}/{digits}"
    r = safe_get(url, referer=f"https://quackr.io/temporary-numbers/{country_slug}")
    if not r:
        return [], "Could not reach quackr.io"

    html = r.text
    clean = re.sub(r'<[^>]+>', '\n', html)
    clean = re.sub(r'&[a-z#0-9]+;', ' ', clean)
    lines = [l.strip() for l in clean.split('\n') if l.strip() and len(l.strip()) > 5]

    msgs = []
    skip_kw = ['quackr', 'cookie', 'privacy', 'footer', 'nav', 'menu',
               'temporary number', 'virtual number', 'copyright']

    for line in lines:
        if any(s in line.lower() for s in skip_kw):
            continue
        if re.search(r'\b\d{4,8}\b', line) and 6 < len(line) < 400:
            if not any(m['body'] == line for m in msgs):
                msgs.append({
                    "from":      guess_sender(line),
                    "body":      line,
                    "otp":       extract_otp(line),
                    "time_text": "recent",
                    "time":      int(time.time()),
                })
        if len(msgs) >= 15:
            break

    log.info(f"quackr inbox +{digits}: {len(msgs)} messages")
    return msgs, None


# ─────────────────────────────────────────────────────────────
# ══ SOURCE 4: 7sim.net ══
# ─────────────────────────────────────────────────────────────
def scrape_numbers_7sim():
    r = safe_get("https://7sim.net/")
    if not r:
        return []

    html = r.text
    nums = []
    seen = set()

    # 7sim lists numbers as links or in a table
    matches = re.findall(r'href="[^"]*?(\+\d{7,15})[^"]*?"', html)
    if not matches:
        matches = re.findall(r'\+(\d{7,15})', html)

    for raw in matches:
        digits = re.sub(r'\D', '', raw)
        if digits in seen or len(digits) < 7:
            continue
        seen.add(digits)

        # Guess country from digit prefix
        flag, code, label = guess_country_from_digits(digits)

        nums.append({
            "number":  f"+{digits}",
            "display": f"+{digits}",
            "country": code,
            "flag":    flag,
            "label":   label,
            "source":  "7sim.net",
            "url":     f"https://7sim.net/",
            "digits":  digits,
        })
        if len(nums) >= 20:
            break

    log.info(f"7sim.net: {len(nums)} numbers")
    return nums


def guess_country_from_digits(digits):
    PREFIX_MAP = [
        ("1",   "🇺🇸", "us", "USA"),
        ("44",  "🇬🇧", "uk", "UK"),
        ("91",  "🇮🇳", "in", "India"),
        ("7",   "🇷🇺", "ru", "Russia"),
        ("49",  "🇩🇪", "de", "Germany"),
        ("33",  "🇫🇷", "fr", "France"),
        ("46",  "🇸🇪", "se", "Sweden"),
        ("31",  "🇳🇱", "nl", "Netherlands"),
        ("61",  "🇦🇺", "au", "Australia"),
        ("55",  "🇧🇷", "br", "Brazil"),
        ("34",  "🇪🇸", "es", "Spain"),
        ("45",  "🇩🇰", "dk", "Denmark"),
        ("48",  "🇵🇱", "pl", "Poland"),
        ("385", "🇭🇷", "hr", "Croatia"),
        ("234", "🇳🇬", "ng", "Nigeria"),
        ("62",  "🇮🇩", "id", "Indonesia"),
        ("63",  "🇵🇭", "ph", "Philippines"),
        ("66",  "🇹🇭", "th", "Thailand"),
        ("84",  "🇻🇳", "vn", "Vietnam"),
    ]
    for prefix, flag, code, label in sorted(PREFIX_MAP, key=lambda x: -len(x[0])):
        if digits.startswith(prefix):
            return flag, code, label
    return "🌐", "us", "Unknown"


# ─────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────
_cache = {"numbers": [], "ts": 0}
CACHE_TTL = 300  # 5 minutes

def get_all_numbers():
    now = time.time()
    if now - _cache["ts"] > CACHE_TTL or not _cache["numbers"]:
        log.info("=== Refreshing all number sources ===")
        all_nums = []
        seen_digits = set()

        sources = [
            ("receive-smss.com", scrape_numbers_receive_smss),
            ("receivesms.co",    scrape_numbers_receivesms_co),
            ("quackr.io",        scrape_numbers_quackr),
        ]

        for src_name, fn in sources:
            try:
                nums = fn()
                added = 0
                for n in nums:
                    if n["digits"] not in seen_digits:
                        seen_digits.add(n["digits"])
                        all_nums.append(n)
                        added += 1
                log.info(f"  {src_name}: +{added} unique numbers")
            except Exception as e:
                log.error(f"  {src_name} error: {e}")

        if all_nums:
            _cache["numbers"] = all_nums
            _cache["ts"] = now
            log.info(f"=== Total: {len(all_nums)} unique numbers cached ===")
        else:
            log.warning("All scrapers returned 0 — cache unchanged")

    return _cache["numbers"]


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/numbers")
def api_numbers():
    country = request.args.get("country", "all")
    source  = request.args.get("source", "all")
    try:
        nums = get_all_numbers()
    except Exception as e:
        log.error(f"api_numbers: {e}")
        nums = []

    if country != "all":
        nums = [n for n in nums if n.get("country") == country]
    if source != "all":
        nums = [n for n in nums if source in n.get("source", "")]

    return jsonify({"ok": True, "numbers": nums, "count": len(nums)})


@app.route("/api/messages/<path:number>")
def api_messages(number):
    digits  = re.sub(r"\D", "", number)
    source  = request.args.get("source", "receive-smss.com")
    country = request.args.get("country", "us")

    if not digits:
        return jsonify({"ok": False, "error": "Invalid number", "messages": []})

    msgs, error = [], None
    try:
        if "quackr" in source:
            # Find the country slug
            slug_map = {
                "us":"united-states","uk":"united-kingdom","in":"india",
                "de":"germany","fr":"france","ca":"canada","se":"sweden",
                "nl":"netherlands","au":"australia","br":"brazil",
            }
            slug = slug_map.get(country, "united-states")
            msgs, error = scrape_sms_quackr(digits, slug)
        elif "receivesms.co" in source:
            msgs, error = scrape_sms_receivesms_co(digits, country)
        else:
            # Default: receive-smss.com
            msgs, error = scrape_sms_receive_smss(digits)

        # If primary returned nothing, fallback to receive-smss
        if not msgs and "receive-smss" not in source:
            log.info(f"Primary empty, trying receive-smss fallback for {digits}")
            msgs, error = scrape_sms_receive_smss(digits)

    except Exception as e:
        log.error(f"api_messages {digits}: {e}")
        error = str(e)

    return jsonify({
        "ok":        True,
        "number":    f"+{digits}",
        "source":    source,
        "messages":  msgs,
        "count":     len(msgs),
        "error":     error,
        "timestamp": int(time.time()),
        "url":       f"https://receive-smss.com/sms/{digits}/",
    })


@app.route("/api/status")
def api_status():
    return jsonify({
        "ok":             True,
        "status":         "running",
        "cached_numbers": len(_cache["numbers"]),
        "cache_age_sec":  int(time.time() - _cache["ts"]) if _cache["ts"] else -1,
        "ts":             int(time.time()),
    })


@app.route("/api/refresh")
def api_refresh():
    """Force refresh the cache."""
    _cache["ts"] = 0
    try:
        nums = get_all_numbers()
        return jsonify({"ok": True, "count": len(nums)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
