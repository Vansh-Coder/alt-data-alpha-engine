import os
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

# Configuration from .env
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# Output folder
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 1. Fetch news via Yahoo Finance Real‑Time API on RapidAPI

def fetch_yahoo_news(ticker: str, region: str = "US") -> pd.DataFrame:
    """
    Fetch latest news for `ticker` using Yahoo Finance Real-Time API via RapidAPI.
    Returns a DataFrame with columns [timestamp, ticker, source, text].
    """
    url = "https://yahoo-finance-real-time1.p.rapidapi.com/news"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {"symbol": ticker, "region": region}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    records = []
    for item in data.get("news", []):
        ts = item.get("date")
        title = item.get("title", "")
        publisher = item.get("publisher", "")
        records.append({
            "timestamp": ts,
            "ticker": ticker,
            "source": publisher,
            "text": title
        })
    return pd.DataFrame(records)

# 2. Fetch Reddit posts via PRAW

def fetch_reddit_posts(subreddit: str, limit: int = 100) -> pd.DataFrame:
    """
    Fetch top `limit` posts from `subreddit`.
    Returns a DataFrame with columns [timestamp, ticker, source, text].
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    posts = reddit.subreddit(subreddit).hot(limit=limit)

    records = []
    for post in posts:
        ts = datetime.utcfromtimestamp(post.created_utc).isoformat()
        text = post.title + (f" - {post.selftext}" if post.selftext else "")
        records.append({
            "timestamp": ts,
            "ticker": subreddit,
            "source": f"reddit.com/r/{subreddit}",
            "text": text,
        })
    return pd.DataFrame(records)

# 3. (Optional) Load SEC transcripts

def load_sec_transcripts(csv_path: str) -> pd.DataFrame:
    """
    Load SEC transcripts from a CSV with at least columns ['date', 'ticker', 'text'].
    """
    df = pd.read_csv(csv_path)
    df = df.rename(columns={
        'date': 'timestamp',
        'text': 'text'
    })
    df['source'] = 'SEC-EDGAR'
    return df[['timestamp', 'ticker', 'source', 'text']]

# 4. Combine sources, clean, and save

def build_pipeline():
    """Run all data fetching, combine, and save raw & cleaned data."""
    tickers = ['AAPL', 'TSLA', 'GOOG']

    all_frames = []
    for t in tickers:
        try:
            news_df = fetch_yahoo_news(t)
            all_frames.append(news_df)
        except Exception as e:
            print(f"Yahoo news fetch failed for {t}: {e}")

        try:
            reddit_df = fetch_reddit_posts('stocks')
            all_frames.append(reddit_df)
        except Exception as e:
            print(f"Reddit fetch failed: {e}")

    sec_path = os.path.join(DATA_DIR, 'sec_transcripts.csv')
    if os.path.exists(sec_path):
        sec_df = load_sec_transcripts(sec_path)
        all_frames.append(sec_df)

    combined = pd.concat(all_frames, ignore_index=True)
    combined['timestamp'] = pd.to_datetime(combined['timestamp'])
    combined = combined.sort_values('timestamp')

    raw_path = os.path.join(DATA_DIR, 'raw_data.csv')
    combined.to_csv(raw_path, index=False)
    print(f"Saved raw data to {raw_path}")

    clean = combined.drop_duplicates(subset=['timestamp', 'ticker', 'text'])
    clean = clean[clean['text'].str.strip() != '']
    clean_path = os.path.join(DATA_DIR, 'clean_data.csv')
    clean.to_csv(clean_path, index=False)
    print(f"Saved clean data to {clean_path}")


if __name__ == '__main__':
    build_pipeline()