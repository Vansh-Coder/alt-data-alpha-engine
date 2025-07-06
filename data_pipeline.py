import os
import pandas as pd
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import praw
from yahooquery import Ticker

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

# 1. Fetch news via yahooquery

def fetch_yahoo_news(ticker: str, count: int = 20) -> pd.DataFrame:
    """
    Fetch latest news articles for `ticker` using yahooquery.
    Returns a DataFrame with [timestamp, ticker, source, text, url].
    """
    tkr = Ticker(ticker)
    try:
        articles = tkr.news(count)
    except Exception as e:
        print(f"Yahooquery news fetch failed for {ticker}: {e}")
        return pd.DataFrame()

    # Flatten if dict of lists
    if isinstance(articles, dict):
        flat = []
        for v in articles.values():
            if isinstance(v, list):
                flat.extend(v)
        articles = flat
    if not isinstance(articles, list):
        print(f"Unexpected news format for {ticker}: {type(articles)}")
        return pd.DataFrame()

    records = []
    for art in articles:
        if not isinstance(art, dict):
            continue
        pub_ts = art.get("providerPublishTime")
        ts = datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat() if isinstance(pub_ts, (int, float)) else None
        publisher = art.get("publisher")
        source = publisher.get("name") if isinstance(publisher, dict) else art.get("source") or ""
        records.append({
            "timestamp": ts,
            "ticker": ticker,
            "source": source,
            "text": art.get("title") or "",
            "url": art.get("link") or ""
        })
    return pd.DataFrame(records)

# 2. Fetch Reddit posts via PRAW

def fetch_reddit_posts(subreddit: str, limit: int = 100) -> pd.DataFrame:
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
    for post in posts:
        ts = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
        text = post.title + (f" - {post.selftext}" if post.selftext else "")
        records.append({
            "timestamp": ts,
            "ticker": subreddit,
            "source": f"reddit.com/r/{subreddit}",
            "text": text,
        })
    return pd.DataFrame(records)

# 3. Fetch SEC 8-K transcripts via EDGAR API

def fetch_sec_transcripts(cik: str, max_filings: int = 3) -> pd.DataFrame:
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

        records.append({
            "timestamp": date,
            "ticker": cik,
            "source": "SEC-EDGAR-8K",
            "text": full_text
        })
        count += 1
    return pd.DataFrame(records)

# 4. Combine sources, clean, and save

def build_pipeline():
    tickers = ['AAPL', 'TSLA', 'GOOG']
    cik_map = {'AAPL': '0000320193', 'TSLA': '0001318605', 'GOOG': '0001652044'}

    frames = []
    for t in tickers:
        frames.append(fetch_yahoo_news(t))
        frames.append(fetch_reddit_posts('stocks'))
        cik = cik_map.get(t)
        if cik:
            frames.append(fetch_sec_transcripts(cik))

    combined = pd.concat(frames, ignore_index=True)
    combined['timestamp'] = pd.to_datetime(combined['timestamp'], utc=True, errors='coerce')
    combined = combined.dropna(subset=['timestamp']).sort_values('timestamp')

    raw_path = os.path.join(DATA_DIR, 'raw_data.csv')
    combined.to_csv(raw_path, index=False)
    print(f"Saved raw data to {raw_path}")

    clean = combined.drop_duplicates(subset=['timestamp', 'ticker', 'text'])
    clean = clean[clean['text'].str.strip().astype(bool)]
    clean_path = os.path.join(DATA_DIR, 'clean_data.csv')
    clean.to_csv(clean_path, index=False)
    print(f"Saved clean data to {clean_path}")


if __name__ == '__main__':
    build_pipeline()