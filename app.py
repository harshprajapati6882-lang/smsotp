"""
TempSMS — Python Flask Backend
Primary source: sms24.me  (9,000+ numbers, 51 countries, open API)
Fallback sources: receive-smss.com, receivesms.co
Always-works fallback: hardcoded number list
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

# ─── USER AGENTS ───
UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def hdrs(ref=""):
    h = {
        "User-Agent": random.choice(UA),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    if ref:
        h["Referer"] = ref
    return h

def get(url, timeout=15, ref=""):
    for i in range(3):
        try:
            r = requests.get(url, headers=hdrs(ref), timeout=timeout)
            log.info(f"GET {url} → {r.status_code} ({len(r.text)}b)")
            if r.status_code == 200:
                return r
        except Exception as e:
            log.warning(f"[{i+1}] {url}: {e}")
        time.sleep(1.5 * (i + 1))
    return None

# ─── OTP / SENDER ───
OTP_RE = [
    r'(?:code|pin|otp|verif\w*|password)[^\d]{0,10}(\d{4,8})',
    r'\[(\d{4,8})\]',
    r':\s*(\d{6})\b',
    r'\b(\d{6})\b',
    r'\b(\d{4})\b',
    r'\b(\d{8})\b',
    r'\b(\d{5})\b',
]
SENDER_KW = {
    'google':'GOOGLE','gmail':'GOOGLE','whatsapp':'WHATSAPP','telegram':'TELEGRAM',
    'facebook':'FACEBOOK','instagram':'INSTAGRAM','amazon':'AMAZON','twitter':'TWITTER',
    'x.com':'TWITTER','tiktok':'TIKTOK','uber':'UBER','netflix':'NETFLIX',
    'microsoft':'MICROSOFT','apple':'APPLE','paypal':'PAYPAL','discord':'DISCORD',
    'snapchat':'SNAPCHAT','linkedin':'LINKEDIN','signal':'SIGNAL','dent':'DENT',
    'kakao':'KAKAOTALK','shopee':'SHOPEE','vk':'VK','supercell':'SUPERCELL',
    'fetch':'FETCH','publix':'PUBLIX','dingtalk':'DINGTALK',
}

def otp(text):
    for p in OTP_RE:
        m = re.search(p, text, re.I)
        if m:
            c = re.sub(r'\D','', m.group(1))
            if 4 <= len(c) <= 8:
                return c
    return None

def sender(text, raw=""):
    t = (text+" "+raw).lower()
    for k,v in SENDER_KW.items():
        if k in t:
            return v
    if raw and re.match(r'^[A-Za-z][A-Za-z0-9_\-]{1,25}$', raw.strip()):
        return raw.strip().upper()
    return "SMS"

# ─── COUNTRY HELPERS ───
PREFIX = [
    ("1",   "🇺🇸","us","USA"),
    ("44",  "🇬🇧","uk","UK"),
    ("91",  "🇮🇳","in","India"),
    ("7",   "🇷🇺","ru","Russia"),
    ("49",  "🇩🇪","de","Germany"),
    ("33",  "🇫🇷","fr","France"),
    ("46",  "🇸🇪","se","Sweden"),
    ("31",  "🇳🇱","nl","Netherlands"),
    ("61",  "🇦🇺","au","Australia"),
    ("55",  "🇧🇷","br","Brazil"),
    ("34",  "🇪🇸","es","Spain"),
    ("45",  "🇩🇰","dk","Denmark"),
    ("48",  "🇵🇱","pl","Poland"),
    ("63",  "🇵🇭","ph","Philippines"),
    ("62",  "🇮🇩","id","Indonesia"),
    ("66",  "🇹🇭","th","Thailand"),
    ("84",  "🇻🇳","vn","Vietnam"),
    ("60",  "🇲🇾","my","Malaysia"),
    ("86",  "🇨🇳","cn","China"),
    ("81",  "🇯🇵","jp","Japan"),
    ("82",  "🇰🇷","kr","South Korea"),
    ("852", "🇭🇰","hk","Hong Kong"),
    ("234", "🇳🇬","ng","Nigeria"),
    ("27",  "🇿🇦","za","South Africa"),
    ("52",  "🇲🇽","mx","Mexico"),
    ("92",  "🇵🇰","pk","Pakistan"),
    ("880", "🇧🇩","bd","Bangladesh"),
    ("90",  "🇹🇷","tr","Turkey"),
    ("972", "🇮🇱","il","Israel"),
    ("385", "🇭🇷","hr","Croatia"),
    ("420", "🇨🇿","cz","Czech Republic"),
    ("40",  "🇷🇴","ro","Romania"),
    ("43",  "🇦🇹","at","Austria"),
    ("32",  "🇧🇪","be","Belgium"),
    ("41",  "🇨🇭","ch","Switzerland"),
    ("47",  "🇳🇴","no","Norway"),
    ("358", "🇫🇮","fi","Finland"),
    ("351", "🇵🇹","pt","Portugal"),
    ("39",  "🇮🇹","it","Italy"),
    ("380", "🇺🇦","ua","Ukraine"),
    ("54",  "🇦🇷","ar","Argentina"),
    ("57",  "🇨🇴","co","Colombia"),
]

SMS24_CC = {
    "us":"us","gb":"uk","uk":"uk","in":"in","ru":"ru","de":"de","fr":"fr",
    "ca":"ca","se":"se","nl":"nl","au":"au","br":"br","es":"es","dk":"dk",
    "pl":"pl","ph":"ph","id":"id","th":"th","vn":"vn","my":"my","cn":"cn",
    "jp":"jp","kr":"kr","hk":"hk","ng":"ng","za":"za","mx":"mx","pk":"pk",
    "bd":"bd","tr":"tr","il":"il","hr":"hr","cz":"cz","ro":"ro","at":"at",
    "be":"be","ch":"ch","no":"no","fi":"fi","pt":"pt","it":"it","ua":"ua",
    "ar":"ar","co":"co","bg":"bg","ee":"ee","ge":"ge","kz":"kz",
}

SMS24_FLAG = {
    "us":"🇺🇸","gb":"🇬🇧","in":"🇮🇳","ru":"🇷🇺","de":"🇩🇪","fr":"🇫🇷","ca":"🇨🇦",
    "se":"🇸🇪","nl":"🇳🇱","au":"🇦🇺","br":"🇧🇷","es":"🇪🇸","dk":"🇩🇰","pl":"🇵🇱",
    "ph":"🇵🇭","id":"🇮🇩","th":"🇹🇭","vn":"🇻🇳","my":"🇲🇾","cn":"🇨🇳","jp":"🇯🇵",
    "kr":"🇰🇷","hk":"🇭🇰","ng":"🇳🇬","za":"🇿🇦","mx":"🇲🇽","pk":"🇵🇰","bd":"🇧🇩",
    "tr":"🇹🇷","il":"🇮🇱","hr":"🇭🇷","cz":"🇨🇿","ro":"🇷🇴","at":"🇦🇹","be":"🇧🇪",
    "ch":"🇨🇭","no":"🇳🇴","fi":"🇫🇮","pt":"🇵🇹","it":"🇮🇹","ua":"🇺🇦","ar":"🇦🇷",
    "co":"🇨🇴","bg":"🇧🇬","ee":"🇪🇪","ge":"🇬🇪","kz":"🇰🇿","uk":"🇬🇧",
}

SMS24_LABEL = {
    "us":"USA","gb":"UK","uk":"UK","in":"India","ru":"Russia","de":"Germany",
    "fr":"France","ca":"Canada","se":"Sweden","nl":"Netherlands","au":"Australia",
    "br":"Brazil","es":"Spain","dk":"Denmark","pl":"Poland","ph":"Philippines",
    "id":"Indonesia","th":"Thailand","vn":"Vietnam","my":"Malaysia","cn":"China",
    "jp":"Japan","kr":"S.Korea","hk":"Hong Kong","ng":"Nigeria","za":"S.Africa",
    "mx":"Mexico","pk":"Pakistan","bd":"Bangladesh","tr":"Turkey","il":"Israel",
    "hr":"Croatia","cz":"Czech Rep.","ro":"Romania","at":"Austria","be":"Belgium",
    "ch":"Switzerland","no":"Norway","fi":"Finland","pt":"Portugal","it":"Italy",
    "ua":"Ukraine","ar":"Argentina","co":"Colombia","bg":"Bulgaria","ee":"Estonia",
    "ge":"Georgia","kz":"Kazakhstan",
}

def guess_country(digits):
    for pfx, flag, code, label in sorted(PREFIX, key=lambda x: -len(x[0])):
        if digits.startswith(pfx):
            return flag, code, label
    return "🌐","us","Unknown"

def make_num(digits, flag, code, label, source, url, msg_count=0):
    return {
        "number":    f"+{digits}",
        "display":   f"+{digits}",
        "country":   code,
        "flag":      flag,
        "label":     label,
        "source":    source,
        "url":       url,
        "digits":    digits,
        "msg_count": msg_count,
    }


# ═══════════════════════════════════════════════════════════
# SOURCE 1 — sms24.me  (PRIMARY — best site, very open)
# ═══════════════════════════════════════════════════════════

SMS24_COUNTRIES = [
    "us","gb","ca","au","de","fr","gb","nl","se","pl",
    "in","br","es","it","fi","dk","no","be","at","ch",
    "cn","jp","kr","hk","vn","th","id","ph","my",
    "ng","za","tr","il","hr","cz","ro","ua","ar","co",
]

def scrape_sms24_numbers():
    """Scrape sms24.me — it clearly lists numbers with msg counts on each country page."""
    nums = []
    seen = set()

    # First get homepage (has top numbers across countries)
    r = get("https://sms24.me/en", ref="https://sms24.me/")
    if r:
        # Pattern: /en/numbers/DIGITS — number + SMS count
        # e.g. +17043681472\\\n\\\n707 SMS received
        matches = re.findall(
            r'/en/numbers/(\d{7,15})',
            r.text
        )
        # Also get msg counts
        blocks = re.findall(
            r'/en/numbers/(\d{7,15}).*?(\d+)\s+SMS\s+received',
            r.text, re.S
        )
        block_map = {d: int(c) for d,c in blocks if c.isdigit()}

        for digits in dict.fromkeys(matches):
            if digits in seen:
                continue
            seen.add(digits)
            flag, code, label = guess_country(digits)
            mc = block_map.get(digits, 0)
            nums.append(make_num(
                digits, flag, code, label,
                "sms24.me",
                f"https://sms24.me/en/numbers/{digits}",
                mc
            ))

    # Then scrape top country pages for more numbers
    for cc in SMS24_COUNTRIES[:15]:  # limit to avoid timeout
        url = f"https://sms24.me/en/countries/{cc}"
        r = get(url, ref="https://sms24.me/en")
        if not r:
            continue

        matches = re.findall(r'/en/numbers/(\d{7,15})', r.text)
        blocks  = re.findall(
            r'/en/numbers/(\d{7,15}).*?(\d+)\s+SMS\s+received',
            r.text, re.S
        )
        block_map = {d: int(c) for d,c in blocks if c.isdigit()}

        our_code = SMS24_CC.get(cc, cc)
        flag     = SMS24_FLAG.get(our_code, "🌐")
        label    = SMS24_LABEL.get(our_code, cc.upper())

        for digits in dict.fromkeys(matches):
            if digits in seen:
                continue
            seen.add(digits)
            mc = block_map.get(digits, 0)
            nums.append(make_num(
                digits, flag, our_code, label,
                "sms24.me",
                f"https://sms24.me/en/numbers/{digits}",
                mc
            ))

        time.sleep(0.3)

    # Sort by msg_count descending (most active first)
    nums.sort(key=lambda x: x.get("msg_count", 0), reverse=True)
    log.info(f"sms24.me: {len(nums)} numbers")
    return nums


def scrape_sms24_inbox(digits):
    """Scrape SMS inbox from sms24.me/en/numbers/DIGITS — very clean HTML."""
    url = f"https://sms24.me/en/numbers/{digits}"
    r = get(url, ref="https://sms24.me/en")
    if not r:
        return [], "Could not reach sms24.me"

    html = r.text

    if "not found" in html.lower() or "404" in html[:500]:
        return [], f"Number +{digits} not found on sms24.me"

    msgs = []

    # sms24.me structure:
    # From: SENDER  X minutes ago
    # MESSAGE TEXT
    # Regex approach on cleaned text
    clean = re.sub(r'<[^>]+>', '\n', html)
    clean = re.sub(r'&[a-z#0-9]+;', ' ', clean)
    lines = [l.strip() for l in clean.split('\n') if l.strip()]

    SKIP = [
        'sms24.me','cookie','privacy','how to','select a','choose a',
        'free temporary','public inbox','verification code','receive sms',
        'new sms','subscribe','newsletter','footer','navigation','menu',
        'frequently asked','are temporary','can i use','why did','how often',
        'all countries','more free','united states phone','fresh active',
        'newest','showing','page','active numbers','practical recommendation',
        'sms aggregator','digital economy','global user','customer support',
        'fraud prevention','core capabilities','phone number generator',
        'inbound routing','api maturity','security and compliance',
        'reliability','analytics','pricing','data privacy','integrations',
    ]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect "From: SENDER" lines
        from_match = re.match(r'^(?:From:\s*)?([A-Za-z0-9_\+\-\.]{2,30})\s*$', line)
        time_match = re.search(r'(\d+\s*(?:minute|hour|second|day)s?\s*ago)', line, re.I)

        if any(s in line.lower() for s in SKIP):
            i += 1
            continue

        # Look for message body — lines with digits 4-8
        if (
            re.search(r'\b\d{4,8}\b', line)
            and 8 < len(line) < 500
            and not any(s in line.lower() for s in SKIP)
        ):
            # Find sender from previous line
            sender_raw = ""
            time_raw   = "just now"

            if i > 0:
                prev = lines[i-1]
                fm = re.match(r'^(?:From:\s*)?([A-Za-z0-9_\+\-\.]{2,30})\s*$', prev)
                if fm:
                    sender_raw = fm.group(1).strip()
            # Find time in next line
            if i + 1 < len(lines):
                tm = re.search(r'(\d+\s*(?:minute|hour|second|day)s?\s*ago)', lines[i+1], re.I)
                if tm:
                    time_raw = tm.group(1)

            if not any(m['body'] == line for m in msgs):
                msgs.append({
                    "from":      sender(line, sender_raw),
                    "body":      line,
                    "otp":       otp(line),
                    "sender":    sender_raw,
                    "time_text": time_raw,
                    "time":      int(time.time()),
                })

        i += 1
        if len(msgs) >= 25:
            break

    log.info(f"sms24 inbox +{digits}: {len(msgs)} msgs")
    return msgs, None


# ═══════════════════════════════════════════════════════════
# SOURCE 2 — receive-smss.com
# ═══════════════════════════════════════════════════════════

def scrape_receive_smss_numbers():
    r = get("https://receive-smss.com/")
    if not r:
        return []

    html = r.text
    nums = []
    seen = set()

    # Extract all /sms/DIGITS/ links
    digits_list = re.findall(r'/sms/(\d{7,15})/', html)

    # Extract flag img srcs (they appear in same order as numbers)
    img_srcs = re.findall(r'src="([^"]*countries[^"]*\.png)"', html)

    FLAG_IMG = {
        "/us.png":("🇺🇸","us","USA"),"/gb.png":("🇬🇧","uk","UK"),
        "/in.png":("🇮🇳","in","India"),"/ru.png":("🇷🇺","ru","Russia"),
        "/de.png":("🇩🇪","de","Germany"),"/fr.png":("🇫🇷","fr","France"),
        "/ca.png":("🇨🇦","ca","Canada"),"/se.png":("🇸🇪","se","Sweden"),
        "/nl.png":("🇳🇱","nl","Netherlands"),"/au.png":("🇦🇺","au","Australia"),
        "/br.png":("🇧🇷","br","Brazil"),"/es.png":("🇪🇸","es","Spain"),
        "/dk.png":("🇩🇰","dk","Denmark"),"/pl.png":("🇵🇱","pl","Poland"),
        "/it.png":("🇮🇹","it","Italy"),"/pt.png":("🇵🇹","pt","Portugal"),
        "/hr.png":("🇭🇷","hr","Croatia"),"/ng.png":("🇳🇬","ng","Nigeria"),
    }

    for i, digits in enumerate(dict.fromkeys(digits_list)):
        if digits in seen:
            continue
        seen.add(digits)

        flag, code, label = guess_country(digits)
        if i < len(img_srcs):
            src = img_srcs[i]
            for suffix, (f, c, l) in FLAG_IMG.items():
                if src.endswith(suffix):
                    flag, code, label = f, c, l
                    break

        nums.append(make_num(
            digits, flag, code, label,
            "receive-smss.com",
            f"https://receive-smss.com/sms/{digits}/"
        ))

    log.info(f"receive-smss: {len(nums)} numbers")
    return nums


def scrape_receive_smss_inbox(digits):
    url = f"https://receive-smss.com/sms/{digits}/"
    r = get(url, ref="https://receive-smss.com/")
    if not r:
        return [], "Could not reach receive-smss.com"

    html = r.text
    if "nothing was found" in html.lower():
        return [], f"+{digits} not found on receive-smss.com"

    clean = re.sub(r'<[^>]+>', '\n', html)
    clean = re.sub(r'&[a-z#0-9]+;', ' ', clean)
    lines = [l.strip() for l in clean.split('\n') if l.strip()]

    SKIP = ['receive-smss','cookie','privacy','chrome','extension','refresh',
            'registration','choose','select','await','how to','step','video',
            'tutorial','click','install','skip','update messages','give me',
            'free sms','temporary phone','website','verify','©','copyright',
            'terms','contact','about','platform']

    msgs = []
    for line in lines:
        if any(s in line.lower() for s in SKIP):
            continue
        if re.search(r'\b\d{4,8}\b', line) and 8 < len(line) < 400:
            if not any(m['body'] == line for m in msgs):
                msgs.append({
                    "from": sender(line),
                    "body": line,
                    "otp":  otp(line),
                    "time_text": "recent",
                    "time": int(time.time()),
                })
        if len(msgs) >= 20:
            break

    log.info(f"receive-smss inbox +{digits}: {len(msgs)} msgs")
    return msgs, None


# ═══════════════════════════════════════════════════════════
# SOURCE 3 — receivesms.co
# ═══════════════════════════════════════════════════════════

def scrape_receivesms_co_numbers():
    r = get("https://www.receivesms.co/free-phone-numbers/")
    if not r:
        return []

    html = r.text
    nums = []
    seen = set()

    matches = re.findall(
        r'href="https?://www\.receivesms\.co/([a-z]+)-phone-number/(\d+)/"',
        html
    )

    CC_MAP = {
        "us":("🇺🇸","us","USA"),"gb":("🇬🇧","uk","UK"),"uk":("🇬🇧","uk","UK"),
        "in":("🇮🇳","in","India"),"ru":("🇷🇺","ru","Russia"),"de":("🇩🇪","de","Germany"),
        "fr":("🇫🇷","fr","France"),"ca":("🇨🇦","ca","Canada"),"se":("🇸🇪","se","Sweden"),
        "nl":("🇳🇱","nl","Netherlands"),"au":("🇦🇺","au","Australia"),"br":("🇧🇷","br","Brazil"),
        "es":("🇪🇸","es","Spain"),"dk":("🇩🇰","dk","Denmark"),"fi":("🇫🇮","fi","Finland"),
        "no":("🇳🇴","no","Norway"),"pl":("🇵🇱","pl","Poland"),"be":("🇧🇪","be","Belgium"),
    }

    for (cc, digits) in matches:
        if digits in seen:
            continue
        seen.add(digits)
        flag, code, label = CC_MAP.get(cc, guess_country(digits)[:3])
        nums.append(make_num(
            digits, flag, code, label,
            "receivesms.co",
            f"https://www.receivesms.co/{cc}-phone-number/{digits}/"
        ))

    log.info(f"receivesms.co: {len(nums)} numbers")
    return nums


# ═══════════════════════════════════════════════════════════
# HARDCODED FALLBACK — always works, updated with real numbers
# ═══════════════════════════════════════════════════════════

FALLBACK = [
    # sms24.me numbers (real, verified working today)
    {"number":"+17043681472","display":"+17043681472","country":"us","flag":"🇺🇸","label":"USA",      "source":"sms24.me","url":"https://sms24.me/en/numbers/17043681472","digits":"17043681472","msg_count":707},
    {"number":"+12021462828","display":"+12021462828","country":"us","flag":"🇺🇸","label":"USA",      "source":"sms24.me","url":"https://sms24.me/en/numbers/12021462828","digits":"12021462828","msg_count":924},
    {"number":"+18583060497","display":"+18583060497","country":"us","flag":"🇺🇸","label":"USA",      "source":"sms24.me","url":"https://sms24.me/en/numbers/18583060497","digits":"18583060497","msg_count":506},
    {"number":"+12026882682","display":"+12026882682","country":"us","flag":"🇺🇸","label":"USA",      "source":"sms24.me","url":"https://sms24.me/en/numbers/12026882682","digits":"12026882682","msg_count":377},
    {"number":"+12018452399","display":"+12018452399","country":"us","flag":"🇺🇸","label":"USA",      "source":"sms24.me","url":"https://sms24.me/en/numbers/12018452399","digits":"12018452399","msg_count":148},
    {"number":"+16722020926","display":"+16722020926","country":"ca","flag":"🇨🇦","label":"Canada",   "source":"sms24.me","url":"https://sms24.me/en/numbers/16722020926","digits":"16722020926","msg_count":390},
    {"number":"+61468245023","display":"+61468245023","country":"au","flag":"🇦🇺","label":"Australia","source":"sms24.me","url":"https://sms24.me/en/numbers/61468245023","digits":"61468245023","msg_count":204},
    {"number":"+8618000005840","display":"+8618000005840","country":"cn","flag":"🇨🇳","label":"China","source":"sms24.me","url":"https://sms24.me/en/numbers/8618000005840","digits":"8618000005840","msg_count":28},
    # receive-smss.com numbers
    {"number":"+13207661354","display":"+13207661354","country":"us","flag":"🇺🇸","label":"USA",      "source":"receive-smss.com","url":"https://receive-smss.com/sms/13207661354/","digits":"13207661354","msg_count":0},
    {"number":"+19707840255","display":"+19707840255","country":"us","flag":"🇺🇸","label":"USA",      "source":"receive-smss.com","url":"https://receive-smss.com/sms/19707840255/","digits":"19707840255","msg_count":0},
    {"number":"+13324653687","display":"+13324653687","country":"us","flag":"🇺🇸","label":"USA",      "source":"receive-smss.com","url":"https://receive-smss.com/sms/13324653687/","digits":"13324653687","msg_count":0},
    {"number":"+447985618978","display":"+447985618978","country":"uk","flag":"🇬🇧","label":"UK",     "source":"receive-smss.com","url":"https://receive-smss.com/sms/447985618978/","digits":"447985618978","msg_count":0},
    {"number":"+447931082241","display":"+447931082241","country":"uk","flag":"🇬🇧","label":"UK",     "source":"receive-smss.com","url":"https://receive-smss.com/sms/447931082241/","digits":"447931082241","msg_count":0},
    {"number":"+447498579857","display":"+447498579857","country":"uk","flag":"🇬🇧","label":"UK",     "source":"receive-smss.com","url":"https://receive-smss.com/sms/447498579857/","digits":"447498579857","msg_count":0},
    {"number":"+4915210947617","display":"+4915210947617","country":"de","flag":"🇩🇪","label":"Germany","source":"receive-smss.com","url":"https://receive-smss.com/sms/4915210947617/","digits":"4915210947617","msg_count":0},
    {"number":"+4915211094215","display":"+4915211094215","country":"de","flag":"🇩🇪","label":"Germany","source":"receive-smss.com","url":"https://receive-smss.com/sms/4915211094215/","digits":"4915211094215","msg_count":0},
    {"number":"+917428730894","display":"+917428730894","country":"in","flag":"🇮🇳","label":"India",  "source":"receive-smss.com","url":"https://receive-smss.com/sms/917428730894/","digits":"917428730894","msg_count":0},
    {"number":"+917428723247","display":"+917428723247","country":"in","flag":"🇮🇳","label":"India",  "source":"receive-smss.com","url":"https://receive-smss.com/sms/917428723247/","digits":"917428723247","msg_count":0},
    {"number":"+31651889518","display":"+31651889518","country":"nl","flag":"🇳🇱","label":"Netherlands","source":"receive-smss.com","url":"https://receive-smss.com/sms/31651889518/","digits":"31651889518","msg_count":0},
    {"number":"+34699305583","display":"+34699305583","country":"es","flag":"🇪🇸","label":"Spain",   "source":"receive-smss.com","url":"https://receive-smss.com/sms/34699305583/","digits":"34699305583","msg_count":0},
    {"number":"+4571383439","display":"+4571383439","country":"dk","flag":"🇩🇰","label":"Denmark",   "source":"receive-smss.com","url":"https://receive-smss.com/sms/4571383439/","digits":"4571383439","msg_count":0},
    {"number":"+559551583801","display":"+559551583801","country":"br","flag":"🇧🇷","label":"Brazil", "source":"receive-smss.com","url":"https://receive-smss.com/sms/559551583801/","digits":"559551583801","msg_count":0},
]


# ═══════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════

_cache = {"numbers": [], "ts": 0}
CACHE_TTL = 300

def get_numbers():
    now = time.time()
    if now - _cache["ts"] > CACHE_TTL or not _cache["numbers"]:
        log.info("=== Fetching fresh numbers ===")
        all_nums = []
        seen = set()

        # Try each source
        sources = [
            ("sms24.me",          scrape_sms24_numbers),
            ("receive-smss.com",  scrape_receive_smss_numbers),
            ("receivesms.co",     scrape_receivesms_co_numbers),
        ]

        for name, fn in sources:
            try:
                nums = fn()
                added = 0
                for n in nums:
                    if n["digits"] not in seen:
                        seen.add(n["digits"])
                        all_nums.append(n)
                        added += 1
                log.info(f"  ✓ {name}: +{added} unique")
            except Exception as e:
                log.error(f"  ✗ {name}: {e}")

        # Always merge in fallback numbers
        for n in FALLBACK:
            if n["digits"] not in seen:
                seen.add(n["digits"])
                all_nums.append(n)

        # Sort: sms24 first (has msg_count), then by msg_count desc
        all_nums.sort(key=lambda x: (x["source"] != "sms24.me", -x.get("msg_count", 0)))

        _cache["numbers"] = all_nums
        _cache["ts"] = now
        log.info(f"=== Cached {len(all_nums)} numbers ===")

    return _cache["numbers"]


# ═══════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/numbers")
def api_numbers():
    country = request.args.get("country", "all")
    source  = request.args.get("source",  "all")
    try:
        nums = get_numbers()
    except Exception as e:
        log.error(f"api_numbers: {e}")
        nums = FALLBACK

    if country != "all":
        nums = [n for n in nums if n.get("country") == country]
    if source != "all":
        nums = [n for n in nums if source in n.get("source","")]

    return jsonify({"ok": True, "numbers": nums, "count": len(nums)})


@app.route("/api/messages/<path:number>")
def api_messages(number):
    digits  = re.sub(r"\D","", number)
    source  = request.args.get("source", "sms24.me")
    country = request.args.get("country", "us")

    if not digits:
        return jsonify({"ok":False,"error":"Invalid number","messages":[]})

    msgs, error = [], None
    tried = []

    try:
        # Pick scraper by source
        if "sms24" in source:
            msgs, error = scrape_sms24_inbox(digits)
            tried.append("sms24.me")
        elif "receive-smss" in source:
            msgs, error = scrape_receive_smss_inbox(digits)
            tried.append("receive-smss.com")
        else:
            msgs, error = scrape_sms24_inbox(digits)
            tried.append("sms24.me")

        # If empty, try receive-smss as fallback
        if not msgs and "receive-smss" not in tried:
            msgs, error = scrape_receive_smss_inbox(digits)
            tried.append("receive-smss.com")

    except Exception as e:
        log.error(f"api_messages {digits}: {e}")
        error = str(e)

    # Build direct URL
    if "sms24" in source:
        direct_url = f"https://sms24.me/en/numbers/{digits}"
    else:
        direct_url = f"https://receive-smss.com/sms/{digits}/"

    return jsonify({
        "ok":        True,
        "number":    f"+{digits}",
        "source":    source,
        "tried":     tried,
        "messages":  msgs,
        "count":     len(msgs),
        "error":     error,
        "url":       direct_url,
        "timestamp": int(time.time()),
    })


@app.route("/api/status")
def api_status():
    nums = _cache.get("numbers", [])
    by_src = {}
    for n in nums:
        s = n.get("source","?")
        by_src[s] = by_src.get(s, 0) + 1
    return jsonify({
        "ok": True, "status": "running",
        "cached_numbers": len(nums),
        "by_source": by_src,
        "cache_age_sec": int(time.time() - _cache["ts"]) if _cache["ts"] else -1,
        "ts": int(time.time()),
    })


@app.route("/api/refresh")
def api_refresh():
    _cache["ts"] = 0
    try:
        nums = get_numbers()
        return jsonify({"ok": True, "count": len(nums)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
