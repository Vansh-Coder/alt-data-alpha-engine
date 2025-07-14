# import os
# import pandas as pd
# import requests
# from datetime import datetime, timezone
# from dotenv import load_dotenv
# import praw
# import yfinance as yf
# import re
# from bs4 import BeautifulSoup
# from sec_cik_mapper import StockMapper

# # Load environment variables
# load_dotenv()

# # Configuration
# REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
# REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
# REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
# SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

# # Output directory
# DATA_DIR = "data"
# os.makedirs(DATA_DIR, exist_ok=True)

# # ticker to cik mapper
# mapper = StockMapper()
# all_mappings = mapper.ticker_to_cik # dict: ticker to CIK

# # Word limits for text field
# MAX_NEWS_WORDS = 30
# MAX_REDDIT_WORDS = 75
# MAX_SEC_WORDS = 75

# def extract_html_document(document_text):
#     """Extracts HTML <TEXT>...</TEXT> for the .htm 8-K block."""
#     document_blocks = re.split(r'<DOCUMENT>', document_text, flags=re.IGNORECASE)

#     for block in document_blocks:
#         if re.search(r'<TYPE>\s*8-K', block, re.IGNORECASE) and re.search(r'<FILENAME>.*\.htm', block, re.IGNORECASE):
#             html_match = re.search(r'<TEXT>(.*?)</TEXT>', block, re.DOTALL | re.IGNORECASE)
#             if html_match:
#                 return html_match.group(1)

#     return None

# def extract_key_items_full_text(document_text):
#     """Extracts all text under key 'Item X.XX' sections."""
#     important_items = {'1.01', '2.02', '4.02', '5.02', '5.07', '8.01'}
    
#     soup = BeautifulSoup(document_text, "html.parser")
#     cleaned_text = soup.get_text(separator=' ')
#     cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

#     # Truncate before signature block if it exists
#     truncation_match = re.search(r'(SIGNATURE|Pursuant to the requirements of the Securities Exchange Act)', cleaned_text, re.IGNORECASE)
#     if truncation_match:
#         cleaned_text = cleaned_text[:truncation_match.start()].strip()

#     item_pattern = re.compile(r'(Item[\s\xa0]*([1-9]\.\d{2}))', re.IGNORECASE)
#     matches = list(item_pattern.finditer(cleaned_text))

#     summary_parts = []

#     for i, match in enumerate(matches):
#         item_code = match.group(2)
#         item_header = match.group(1)
#         if item_code not in important_items:
#             continue

#         start = match.end()
#         end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_text)
#         section_text = cleaned_text[start:end].strip()

#         if section_text:
#             words = section_text.split()
#             truncated = " ".join(words[:MAX_SEC_WORDS])
#         else:
#             truncated = ""

#         summary_parts.append(f"({item_header}) {truncated}")

#     return '\n\n'.join(summary_parts)

# # 1. Fetch news via yfinance

# def fetch_yahoo_news(ticker: str) -> pd.DataFrame:
#     """
#     Fetch latest news articles for `ticker` using yfinance.
#     Returns a DataFrame with [timestamp, ticker, source, text, url].
#     """
#     try:
#         raw = yf.Ticker(ticker).news or []
#     except Exception as e:
#         print(f"yfinance news fetch failed for {ticker}: {e}")
#         return pd.DataFrame()

#     records = []
#     for item in raw:
#         # content = item.get("content") or {}
#         # title = content.get("title") or "",
#         # summary = content.get("summary") or ""
#         # brief_summary = " ".join(summary.split()[:MAX_NEWS_WORDS]) or ""
#         # provider = content.get("provider") or {}
#         # # Extract URL
#         # ctu = content.get("clickThroughUrl") or {}
#         # cano = content.get("canonicalUrl") or {}
#         # url = ctu.get("url") or cano.get("url") or ""
#         # records.append({
#         #     "timestamp": content.get("pubDate"),
#         #     "ticker": ticker,
#         #     "source": provider.get("displayName") or "",
#         #     "text": brief_summary or title or "",
#         #     "url": url,
#         # })
#         content = item.get("content") or {}
#         title = content.get("title") or ""
#         if title:
#             words = title.split()
#             text = " ".join(words[:MAX_NEWS_WORDS])
#         else:
#             text = ""
#         provider = content.get("provider") or {}
#         # Extract URL
#         ctu = content.get("clickThroughUrl") or {}
#         cano = content.get("canonicalUrl") or {}
#         url = ctu.get("url") or cano.get("url") or ""
#         records.append({
#             "timestamp": content.get("pubDate"),
#             "ticker": ticker,
#             "source": provider.get("displayName") or "",
#             "text": text,
#             "url": url,
#         })
#     return pd.DataFrame(records)

# # 2. Fetch Reddit posts via PRAW

# def fetch_reddit_posts(subreddit: str, ticker: str, limit: int = 100) -> pd.DataFrame:
#     """
#     Fetch latest hot posts from `subreddit` via PRAW, but only return
#     those whose title or selftext mentions the given `ticker` (e.g. "AAPL" or "$AAPL").
#     """
#     reddit = praw.Reddit(
#         client_id=REDDIT_CLIENT_ID,
#         client_secret=REDDIT_CLIENT_SECRET,
#         user_agent=REDDIT_USER_AGENT,
#     )
#     try:
#         posts = reddit.subreddit(subreddit).hot(limit=limit)
#     except Exception as e:
#         print(f"Error fetching Reddit posts: {e}")
#         return pd.DataFrame()

#     records = []
#     ticker_pattern = re.compile(rf'\b{re.escape(ticker)}\b', re.IGNORECASE)
#     cashtag_pattern = re.compile(rf'\${re.escape(ticker)}\b', re.IGNORECASE)

#     for post in posts:
#         ts = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
#         body = (post.title + (f" - {post.selftext}" if post.selftext else "")).strip() or ""

#         # only keep if ticker appears as a word or as a cashtag
#         if not (ticker_pattern.search(body) or cashtag_pattern.search(body)):
#             continue

#         if body:
#             words = body.split()
#             text = " ".join(words[:MAX_REDDIT_WORDS])
#         else:
#             text = ""

#         records.append({
#             "timestamp": ts,
#             "ticker": ticker,
#             "source": f"reddit.com/r/{subreddit}",
#             "text": text,
#         })
    
#     return pd.DataFrame(records)

# # 3. Fetch SEC 8-K transcripts via EDGAR API

# def fetch_sec_transcripts(cik: str, ticker: str, max_filings: int = 3) -> pd.DataFrame:
#     feed_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
#     headers = {"User-Agent": SEC_USER_AGENT}
#     try:
#         r = requests.get(feed_url, headers=headers)
#         r.raise_for_status()
#         subs = r.json()
#     except Exception as e:
#         print(f"Error fetching SEC feed for CIK {cik}: {e}")
#         return pd.DataFrame()

#     filings = subs.get("filings", {}).get("recent", {})
#     forms = filings.get("form", [])
#     accessions = filings.get("accessionNumber", [])
#     dates = filings.get("filingDate", [])

#     records = []
#     count = 0
#     for form, acc, date in zip(forms, accessions, dates):
#         if form.upper() != "8-K" or count >= max_filings:
#             continue
#         acc_nodash = acc.replace("-", "")
#         txt_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{acc}.txt"
#         try:
#             txt_resp = requests.get(txt_url, headers=headers)
#             txt_resp.raise_for_status()
#             full_text = txt_resp.text
#         except Exception:
#             continue

#         extracted_html = extract_html_document(full_text)
#         extracted_text = extract_key_items_full_text(extracted_html)
#         dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).isoformat()
#         records.append({
#             "timestamp": dt,
#             "ticker": ticker,
#             "source": "SEC-EDGAR-8K",
#             "text": extracted_text
#         })
#         count += 1
    
#     return pd.DataFrame(records)

# # 4. Combine sources, clean, and save

# def build_pipeline():
#     # Tickers to process
#     tickers = [
#         'AAPL','MSFT','GOOG','AMZN','META','TSLA','NVDA','JPM','JNJ',
#         'PG','UNH','HD','DIS','MA','BAC','XOM','PFE','ADBE','CMCSA',
#         'NFLX','KO','ABT','CSCO','PEP','CVX','INTC','CRM','NKE','MRK',
#         'ORCL','TMO','WMT','ACN','COST','LLY','TXN','MCD','UNP','MDT',
#         'NEE','QCOM','PM','SCHW','AMGN','IBM','BMY','ELV','VRTX','HON',
#         'UPS','C','GE','LIN','LMT','DE','MMM','AXP','BKNG','RTX','PLD',
#         'ADP','BA','SBUX','GILD','BLK','CAT','SPGI','GS','NOW','AMAT',
#         'SYK','ISRG','ZTS','CI','CVS','LRCX','ADI','EL','CB','MDLZ',
#         'MU','TEAM','TGT','USB','CCI','CME','DHR','BDX','ADSK','APD',
#         'EQIX','PNC','CSX','MO','SO','TMUS','SPG','MS','CL','AON'
#     ]

#     # Build cik_map using mapper
#     cik_map = {t: all_mappings[t] for t in tickers if t in all_mappings}

#     frames = []
#     # Ticker-specific news and SEC filings
#     for t in tickers:
#         frames.append(fetch_yahoo_news(t))
#         # Reddit posts from r/stocks
#         frames.append(fetch_reddit_posts('stocks', t))
#         cik = cik_map.get(t)
#         frames.append(fetch_sec_transcripts(cik, t))

#     combined = pd.concat(frames, ignore_index=True)
#     # Parse and clean timestamps
#     combined['timestamp'] = pd.to_datetime(combined['timestamp'], utc=True, errors='coerce')
#     combined = combined.dropna(subset=['timestamp']).sort_values('timestamp')

#     raw_path = os.path.join(DATA_DIR, 'raw_data.csv')
#     combined.to_csv(raw_path, index=False)
#     print(f"Saved raw data to {raw_path}")

#     # Drop exact duplicates per ticker
#     clean = combined.drop_duplicates(subset=['timestamp','text'])
#     clean = clean[clean['text'].str.strip().astype(bool)]
#     clean_path = os.path.join(DATA_DIR, 'clean_data.csv')
#     clean.to_csv(clean_path, index=False)
#     print(f"Saved clean data to {clean_path}")


# if __name__ == '__main__':
#     build_pipeline()
import os
import pandas as pd
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import praw
import yfinance as yf
import re
from bs4 import BeautifulSoup
from sec_cik_mapper import StockMapper

# Load environment variables
load_dotenv()

# Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

# Output directory
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ticker to cik mapper
mapper = StockMapper()
all_mappings = mapper.ticker_to_cik # dict: ticker to CIK

def extract_html_document(document_text):
    """Extracts HTML <TEXT>...</TEXT> for the .htm 8-K block."""
    document_blocks = re.split(r'<DOCUMENT>', document_text, flags=re.IGNORECASE)

    for block in document_blocks:
        if re.search(r'<TYPE>\s*8-K', block, re.IGNORECASE) and re.search(r'<FILENAME>.*\.htm', block, re.IGNORECASE):
            html_match = re.search(r'<TEXT>(.*?)</TEXT>', block, re.DOTALL | re.IGNORECASE)
            if html_match:
                return html_match.group(1)

    return None

def extract_key_items_full_text(document_text, max_words=75):
    """Extracts all text under key 'Item X.XX' sections."""
    important_items = {'1.01', '2.02', '4.02', '5.02', '5.07', '8.01'}

    soup = BeautifulSoup(document_text, "html.parser")
    cleaned_text = soup.get_text(separator=' ')
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    # Truncate before signature block if it exists
    truncation_match = re.search(r'(SIGNATURE|Pursuant to the requirements of the Securities Exchange Act)', cleaned_text, re.IGNORECASE)
    if truncation_match:
        cleaned_text = cleaned_text[:truncation_match.start()].strip()

    item_pattern = re.compile(r'(Item[\s\xa0]*([1-9]\.\d{2}))', re.IGNORECASE)
    matches = list(item_pattern.finditer(cleaned_text))

    summary_parts = []

    for i, match in enumerate(matches):
        item_code = match.group(2)
        item_header = match.group(1)
        if item_code not in important_items:
            continue

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_text)
        section_text = cleaned_text[start:end].strip()

        words = section_text.split()
        truncated = " ".join(words[:max_words])

        summary_parts.append(f"({item_header}) {truncated}")

    return '\n\n'.join(summary_parts)

# 1. Fetch news via yfinance

def fetch_yahoo_news(ticker: str) -> pd.DataFrame:
    """
    Fetch latest news articles for `ticker` using yfinance.
    Returns a DataFrame with [timestamp, ticker, source, text, url].
    """
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception as e:
        print(f"yfinance news fetch failed for {ticker}: {e}")
        return pd.DataFrame()

    records = []
    for item in raw:
        content = item.get("content") or {}
        provider = content.get("provider") or {}
        # Extract URL
        ctu = content.get("clickThroughUrl") or {}
        cano = content.get("canonicalUrl") or {}
        url = ctu.get("url") or cano.get("url") or ""
        records.append({
            "timestamp": content.get("pubDate"),
            "ticker": ticker,
            "source": provider.get("displayName") or "",
            "text": content.get("title") or "",
            "url": url,
        })
    return pd.DataFrame(records)

# 2. Fetch Reddit posts via PRAW

def fetch_reddit_posts(subreddit: str, ticker: str, limit: int = 100) -> pd.DataFrame:
    """
    Fetch latest hot posts from `subreddit` via PRAW, but only return
    those whose title or selftext mentions the given `ticker` (e.g. "AAPL" or "$AAPL").
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    try:
        posts = reddit.subreddit(subreddit).hot(limit=limit)
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
        return pd.DataFrame()

    records = []
    ticker_pattern = re.compile(rf'\b{re.escape(ticker)}\b', re.IGNORECASE)
    cashtag_pattern = re.compile(rf'\${re.escape(ticker)}\b', re.IGNORECASE)

    for post in posts:
        ts = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
        body = post.title + (f" - {post.selftext}" if post.selftext else "")

        # only keep if ticker appears as a word or as a cashtag
        if not (ticker_pattern.search(body) or cashtag_pattern.search(body)):
            continue

        records.append({
            "timestamp": ts,
            "ticker": ticker,
            "source": f"reddit.com/r/{subreddit}",
            "text": body,
        })

    return pd.DataFrame(records)

# 3. Fetch SEC 8-K transcripts via EDGAR API

def fetch_sec_transcripts(cik: str, ticker: str, max_filings: int = 3) -> pd.DataFrame:
    feed_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        r = requests.get(feed_url, headers=headers)
        r.raise_for_status()
        subs = r.json()
    except Exception as e:
        print(f"Error fetching SEC feed for CIK {cik}: {e}")
        return pd.DataFrame()

    filings = subs.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    records = []
    count = 0
    for form, acc, date in zip(forms, accessions, dates):
        if form.upper() != "8-K" or count >= max_filings:
            continue
        acc_nodash = acc.replace("-", "")
        txt_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{acc}.txt"
        try:
            txt_resp = requests.get(txt_url, headers=headers)
            txt_resp.raise_for_status()
            full_text = txt_resp.text
        except Exception:
            continue

        extracted_html = extract_html_document(full_text)
        extracted_text = extract_key_items_full_text(extracted_html)
        dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).isoformat()
        records.append({
            "timestamp": dt,
            "ticker": ticker,
            "source": "SEC-EDGAR-8K",
            "text": extracted_text
        })
        count += 1

    return pd.DataFrame(records)

# 4. Combine sources, clean, and save

def build_pipeline():
    # Tickers to process
    tickers = [
        'AAPL','MSFT','GOOG','AMZN','META','TSLA','NVDA','JPM','JNJ',
        'PG','UNH','HD','DIS','MA','BAC','XOM','PFE','ADBE','CMCSA',
        'NFLX','KO','ABT','CSCO','PEP','CVX','INTC','CRM','NKE','MRK',
        'ORCL','TMO','WMT','ACN','COST','LLY','TXN','MCD','UNP','MDT',
        'NEE','QCOM','PM','SCHW','AMGN','IBM','BMY','ELV','VRTX','HON',
        'UPS','C','GE','LIN','LMT','DE','MMM','AXP','BKNG','RTX','PLD',
        'ADP','BA','SBUX','GILD','BLK','CAT','SPGI','GS','NOW','AMAT',
        'SYK','ISRG','ZTS','CI','CVS','LRCX','ADI','EL','CB','MDLZ',
        'MU','TEAM','TGT','USB','CCI','CME','DHR','BDX','ADSK','APD',
        'EQIX','PNC','CSX','MO','SO','TMUS','SPG','MS','CL','AON'
    ]

    # Build cik_map using mapper
    cik_map = {t: all_mappings[t] for t in tickers if t in all_mappings}

    frames = []
    # Ticker-specific news and SEC filings
    for t in tickers:
        frames.append(fetch_yahoo_news(t))
        # Reddit posts from r/stocks
        frames.append(fetch_reddit_posts('stocks', t))
        cik = cik_map.get(t)
        frames.append(fetch_sec_transcripts(cik, t))

    combined = pd.concat(frames, ignore_index=True)
    # Parse and clean timestamps
    combined['timestamp'] = pd.to_datetime(combined['timestamp'], utc=True, errors='coerce')
    combined = combined.dropna(subset=['timestamp']).sort_values('timestamp')

    raw_path = os.path.join(DATA_DIR, 'raw_data.csv')
    combined.to_csv(raw_path, index=False)
    print(f"Saved raw data to {raw_path}")

    # Drop exact duplicates per ticker
    clean = combined.drop_duplicates(subset=['timestamp','text'])
    clean = clean[clean['text'].str.strip().astype(bool)]
    clean_path = os.path.join(DATA_DIR, 'clean_data.csv')
    clean.to_csv(clean_path, index=False)
    print(f"Saved clean data to {clean_path}")


if __name__ == '__main__':
    build_pipeline()