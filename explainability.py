import os
import json
import time
from typing import List
import pandas as pd
from dotenv import load_dotenv
import openai

# Load OpenAI key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Cache file for explanations
CACHE_FILE = os.path.join('data', 'explanation_cache.json')
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'w') as f:
        json.dump({}, f)
with open(CACHE_FILE, 'r') as f:
    _cache = json.load(f)


def generate_explanation(text: str, score: float) -> str:
    """
    Given a text snippet and its sentiment score, return a 1-2 sentence rationale.
    Caches calls to avoid duplicate usage.
    """
    key = f"{score:.3f}: {text}"
    if key in _cache:
        return _cache[key]

    prompt = (
        "You are an expert financial analyst."
        "\nGiven the following news headline or post and its sentiment score,"
        " explain in 1-2 sentences why the score is appropriate."
        f"\n\nText: \"{text}\""
        f"\nSentiment score: {score:.2f}"
        "\nRationale:"
    )

    resp = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role':'system','content':'You are a helpful analyst.'},
                  {'role':'user','content':prompt}],
        temperature=0.0,
        max_tokens=60
    )
    explanation = resp.choices[0].message.content.strip()

    _cache[key] = explanation
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)
    time.sleep(0.2)
    return explanation


def batch_explain(signals_path: str, output_path: str) -> None:
    """
    Read a signals CSV, merge in the original text from sentiment_scored.csv, generate explanations,
    and write out a new CSV with 'Explanation'.
    """
    # Load signals
    signals = pd.read_csv(signals_path, parse_dates=['timestamp'])
    signals['date'] = signals['timestamp'].dt.date

    # Load scored data to get the text column
    scored_path = os.path.join('data', 'sentiment_scored.csv')
    raw = pd.read_csv(scored_path, parse_dates=['timestamp'])
    raw['date'] = raw['timestamp'].dt.date

    # Merge to bring in text for each signal by date and ticker
    df = pd.merge(
        signals,
        raw[['date', 'ticker', 'text']],
        on=['date', 'ticker'],
        how='left'
    )

    explanations: List[str] = []
    for _, row in df.iterrows():
        text = row.get('text', '') or ''
        score = row.get('agg_score', 0.0)
        explanations.append(generate_explanation(text, score))

    df['Explanation'] = explanations
    # Drop helper column
    df.drop(columns=['date'], inplace=True)
    df.to_csv(output_path, index=False)
    print(f"Explanations added and saved to {output_path}")

if __name__ == '__main__':
    # Example usage
    batch_explain(
        signals_path=os.path.join('data','signals.csv'),
        output_path=os.path.join('data','signals_with_explanations.csv')
    )