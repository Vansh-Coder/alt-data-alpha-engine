import os
import re
import requests
import pandas as pd
import praw
import yfinance as yf

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from sec_cik_mapper import StockMapper

# ─── Config ────────────────────────────────────────────────────────────────────
load_dotenv()
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

NASDAQ_USER_AGENT    = os.getenv("NASDAQ_USER_AGENT")
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT")
SEC_USER_AGENT       = os.getenv("SEC_USER_AGENT")

MAX_NEWS_PER_TICKER = 20
MAX_REDDIT_WORDS = 75
MAX_SEC_WORDS    = 75
CUTOFF_DAYS      = 7  # keep last 7 days only

# ticker -> CIK mapper
mapper       = StockMapper()
all_mappings = mapper.ticker_to_cik

# default NASDAQ-100 tickers
DEFAULT_NASDAQ_100_TICKERS = [
    'AAPL', 'ABNB', 'ADBE', 'ADI', 'ADP', 'ADSK', 'AEP', 'AMAT', 'AMD',
    'AMGN', 'AMZN', 'APP', 'ARM', 'ASML', 'AVGO', 'AXON', 'AZN', 'BIIB',
    'BKNG', 'BKR', 'CCEP', 'CDNS', 'CDW', 'CEG', 'CHTR', 'CMCSA', 'COST',
    'CPRT', 'CRWD', 'CSCO', 'CSGP', 'CSX', 'CTAS', 'CTSH', 'DASH', 'DDOG',
    'DXCM', 'EA', 'EXC', 'FANG', 'FAST', 'FTNT', 'GEHC', 'GFS', 'GILD',
    'GOOG', 'GOOGL', 'HON', 'IDXX', 'INTC', 'INTU', 'ISRG', 'KDP', 'KHC',
    'KLAC', 'LIN', 'LRCX', 'LULU', 'MAR', 'MCHP', 'MDLZ', 'MELI', 'META',
    'MNST', 'MRVL', 'MSFT', 'MSTR', 'MU', 'NFLX', 'NVDA', 'NXPI', 'ODFL',
    'ON', 'ORLY', 'PANW', 'PAYX', 'PCAR', 'PDD', 'PEP', 'PLTR', 'PYPL',
    'QCOM', 'REGN', 'ROP', 'ROST', 'SBUX', 'SHOP', 'SNPS', 'TEAM', 'TMUS',
    'TSLA', 'TTD', 'TTWO', 'TXN', 'VRSK', 'VRTX', 'WBD', 'WDAY', 'XEL', 'ZS'
]

# ─── HTML / EDGAR helpers ──────────────────────────────────────────────────────
def extract_html_document(document_text):
    """Extracts the <TEXT>…</TEXT> block for 8-K filings."""
    if not document_text:
        return ""
    blocks = re.split(r'<DOCUMENT>', document_text, flags=re.IGNORECASE)
    for blk in blocks:
        if re.search(r'<TYPE>\s*8-K', blk, re.IGNORECASE) and re.search(r'<FILENAME>.*\.htm', blk, re.IGNORECASE):
            m = re.search(r'<TEXT>(.*?)</TEXT>', blk, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(1)
    return None


def extract_key_items_full_text(document_text):
    """Extracts truncated text for key Item X.XX sections."""
    important = {'1.01','2.02','4.02','5.02','5.07','8.01'}
    soup        = BeautifulSoup(document_text, "html.parser")
    txt         = re.sub(r'\s+',' ', soup.get_text(separator=' '))
    # drop after signature
    sig_match   = re.search(r'(SIGNATURE|Pursuant to the requirements of the Securities Exchange Act)', txt, re.IGNORECASE)
    if sig_match:
        txt = txt[:sig_match.start()].strip()
    pattern     = re.compile(r'(Item[\s\xa0]*([1-9]\.\d{2}))', re.IGNORECASE)
    matches     = list(pattern.finditer(txt))
    parts       = []
    for i, m in enumerate(matches):
        code = m.group(2)
        if code not in important:
            continue
        start = m.end()
        end   = matches[i+1].start() if i+1 < len(matches) else len(txt)
        section = txt[start:end].strip().split()[:MAX_SEC_WORDS]
        parts.append(f"({m.group(1)}) " + " ".join(section))
    return "\n\n".join(parts)

# ─── Data‐fetching functions ──────────────────────────────────────────────────

def fetch_yahoo_news(ticker: str) -> pd.DataFrame:
    try:
        raw = yf.Ticker(ticker).get_news(count=MAX_NEWS_PER_TICKER, tab="all") or []
    except Exception as e:
        print(f"yfinance news failed {ticker}: {e}")
        return pd.DataFrame()
    recs = []
    for item in raw:
        c      = item.get("content", {})
        prov   = c.get("provider", {})
        url    = (c.get("clickThroughUrl") or {}).get("url", "") or (c.get("canonicalUrl") or {}).get("url","")
        recs.append({
            "timestamp": c.get("pubDate"),
            "ticker":    ticker,
            "source":    prov.get("displayName",""),
            "text":      c.get("title",""),
            "url":       url
        })
    return pd.DataFrame(recs)


def fetch_reddit_posts_for_tickers(subreddit: str, tickers: list, limit: int = 100) -> pd.DataFrame:
    """
    Fetch hot posts from `subreddit` once, then for each post,
    emit one record per ticker that appears in the post (as word or cashtag).
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    try:
        posts = reddit.subreddit(subreddit).hot(limit=limit)
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
        return pd.DataFrame()

    # Precompile patterns for speed
    word_patterns    = {t: re.compile(rf'\b{re.escape(t)}\b', re.IGNORECASE) for t in tickers}
    cashtag_patterns = {t: re.compile(rf'\${re.escape(t)}\b', re.IGNORECASE) for t in tickers}

    records = []
    for post in posts:
        ts   = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
        body = post.title + (f" - {post.selftext}" if post.selftext else "")
        if not body.strip():
            continue
        # Truncate to first MAX_REDDIT_WORDS words
        text = " ".join(body.split()[:MAX_REDDIT_WORDS])

        # Check each ticker
        for ticker in tickers:
            if word_patterns[ticker].search(body) or cashtag_patterns[ticker].search(body):
                records.append({
                    "timestamp": ts,
                    "ticker":    ticker,
                    "source":    f"reddit.com/r/{subreddit}",
                    "text":      text
                })
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def fetch_sec_transcripts(cik: str, ticker: str, max_filings: int = 10) -> pd.DataFrame:
    feed_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    headers  = {"User-Agent": SEC_USER_AGENT}
    try:
        r    = requests.get(feed_url, headers=headers); r.raise_for_status()
        subs = r.json()
    except Exception as e:
        print(f"SEC feed error {cik}: {e}")
        return pd.DataFrame()

    forms      = subs.get("filings",{}).get("recent",{}).get("form", [])
    accessions = subs.get("filings",{}).get("recent",{}).get("accessionNumber", [])
    dates      = subs.get("filings",{}).get("recent",{}).get("filingDate", [])

    recs, cnt = [], 0
    for form, acc, date in zip(forms, accessions, dates):
        if form.upper()!="8-K" or cnt>=max_filings:
            continue
        txt_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{acc}.txt"
        try:
            full = requests.get(txt_url, headers=headers).text
        except Exception:
            continue
        html = extract_html_document(full)
        if not html:
            continue
        txt  = extract_key_items_full_text(html)
        if not txt.strip():
            continue
        dt   = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).isoformat()
        recs.append({"timestamp": dt, "ticker": ticker, "source":"SEC-EDGAR-8K", "text": txt})
        cnt += 1

    return pd.DataFrame(recs)

# --- Fetch Latest NASDAQ 100 Tickers ------------------------------------------

def get_nasdaq100_tickers():
    url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
    headers = { "user-agent": NASDAQ_USER_AGENT }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        json_data = res.json()

        rows = json_data.get("data", {}).get("data", {}).get("rows", [])
        if not rows:
            raise ValueError("Empty or malformed response structure")

        tickers = sorted(row["symbol"] for row in rows if "symbol" in row)
        return tickers

    except Exception as e:
        print(f"Failed to fetch latest NASDAQ-100 tickers: {e}")
        print("Using default tickers instead.")
        return DEFAULT_NASDAQ_100_TICKERS

# ─── Orchestrator ─────────────────────────────────────────────────────────────

def build_pipeline():
    # Latest NASDAQ-100 tickers
    tickers = get_nasdaq100_tickers()
    cik_map = {t: all_mappings.get(t) for t in tickers}

    frames = []

    # 1) news per ticker
    for t in tickers:
        frames.append(fetch_yahoo_news(t))

    # 2) reddit hot posts once, then split
    reddit_df = fetch_reddit_posts_for_tickers('stocks', tickers)
    if not reddit_df.empty:
        frames.append(reddit_df)

    # 3) SEC filings per ticker
    for t in tickers:
        cik = cik_map.get(t)
        if cik:
            frames.append(fetch_sec_transcripts(cik, t))

    if not frames:
        print("No data frames to concatenate.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # parse, clean, sort
    combined['timestamp'] = pd.to_datetime(combined['timestamp'], utc=True, errors='coerce')
    combined = combined.dropna(subset=['timestamp']).sort_values('timestamp')

    # —— apply cutoff ——
    cutoff   = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
    combined = combined[combined['timestamp'] >= cutoff]

    raw_path   = os.path.join(DATA_DIR, 'raw_data.csv')
    combined.to_csv(raw_path, index=False)
    print(f"Saved raw_data (last {CUTOFF_DAYS} days) to {raw_path}")

    clean = combined.drop_duplicates(subset=['timestamp','text'])
    clean = clean[clean['text'].str.strip().astype(bool)]
    clean_path = os.path.join(DATA_DIR, 'clean_data.csv')
    clean.to_csv(clean_path, index=False)
    print(f"Saved clean_data (last {CUTOFF_DAYS} days) to {clean_path}")

if __name__ == '__main__':
    build_pipeline()