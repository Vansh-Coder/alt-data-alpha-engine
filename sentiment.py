import os
import json
import time
from typing import List
from dotenv import load_dotenv
import openai
import pandas as pd

# Load environment variables and set API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Caching file for sentiment calls
CACHE_FILE = os.path.join("data", "sentiment_cache.json")

# Ensure cache exists
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'w') as f:
        json.dump({}, f)

# Load cache
with open(CACHE_FILE, 'r') as f:
    _cache = json.load(f)


def get_sentiment(text: str) -> float:
    """
    Returns a sentiment score between -1 (negative) and +1 (positive) for the given text.
    Caches results in sentiment_cache.json to avoid duplicate API calls.
    """
    key = text.strip()
    if key in _cache:
        return _cache[key]

    # Build prompt
    prompt = (
        "On a scale from -1 to 1, rate the sentiment of the following text. "
        "Return only the number.\n\n"
        f"Text: \"{text}\"\n"
        "Sentiment:"
    )

    # Call OpenAI
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=5
    )
    try:
        score_str = response.choices[0].message.content.strip()
        score = float(score_str)
    except Exception:
        score = 0.0

    # Cache and persist
    _cache[key] = score
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)

    # Avoid rate limits
    time.sleep(0.2)
    return score


def batch_sentiment(df: pd.DataFrame, text_col: str = "text", score_col: str = "SentimentScore") -> pd.DataFrame:
    """
    Adds a sentiment score column to the DataFrame by applying get_sentiment in batches.
    """
    scores = []
    for text in df[text_col].astype(str).tolist():
        score = get_sentiment(text)
        scores.append(score)
    df[score_col] = scores
    return df


if __name__ == '__main__':
    # Example usage
    raw = pd.read_csv(os.path.join("data", "clean_data.csv"))
    out = batch_sentiment(raw)
    out.to_csv(os.path.join("data", "sentiment_scored.csv"), index=False)
    print("Sentiment scoring complete. Output saved to data/sentiment_scored.csv")