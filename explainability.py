import os
import json
import time
from typing import List, Dict
import pandas as pd
from dotenv import load_dotenv
import openai

# Load OpenAI key and cache
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

CACHE_FILE = os.path.join('data', 'explanation_cache.json')
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'w') as f:
        json.dump({}, f)
with open(CACHE_FILE, 'r') as f:
    _cache: Dict[str, str] = json.load(f)


def batch_explain_all(df: pd.DataFrame, batch_size: int = 20) -> List[str]:
    """
    Batch explanations for rows in df using OpenAI in chunks of batch_size.
    Returns a list of explanations aligned with df.index.
    """
    explanations = [None] * len(df)
    # Map each row to a unique cache key
    def make_key(text: str, score: float) -> str:
        return f"{score:.3f}: {text}"

    # Identify rows needing API calls
    to_call = []  # list of (idx, text, score)
    for idx, row in df.iterrows():
        key = make_key(row['text'], row['agg_score'])
        if key in _cache:
            explanations[idx] = _cache[key]
        else:
            to_call.append((idx, row['text'], row['agg_score'], key))

    # Process in batches
    for start in range(0, len(to_call), batch_size):
        chunk = to_call[start:start+batch_size]
        # Build prompt with numbered items
        items = []
        for i, (_, text, score, key) in enumerate(chunk, 1):
            items.append(
                f"{i}. Text: \"{text}\"\n   Sentiment: {score:.2f}"
            )
        prompt = (
            "You are an expert financial analyst.\n"
            "For each numbered item, provide a 1–2 sentence rationale explaining why the sentiment score is appropriate.\n"
            "Respond with valid JSON as a list of objects, each with 'index' and 'rationale', like:\n"
            "[{\"index\":1,\"rationale\":\"...\"}, ...] \n\n"
            + "\n".join(items)
        )
        # Call OpenAI once per chunk
        resp = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{'role':'system','content':'You are a helpful financial analyst.'},
                      {'role':'user','content':prompt}],
            temperature=0.0,
            max_tokens=1500
        )
        text_out = resp.choices[0].message.content.strip()
        # Parse JSON response
        try:
            parsed = json.loads(text_out)
            for item in parsed:
                idx, key = chunk[item['index']-1][0], chunk[item['index']-1][3]
                rationale = item.get('rationale', '').strip()
                _cache[key] = rationale
                explanations[idx] = rationale
        except Exception as e:
            # On parse error, fallback to single requests
            for idx, text, score, key in chunk:
                rationale = _fallback_explain(text, score)
                _cache[key] = rationale
                explanations[idx] = rationale
        # Optionally rate-limit
        time.sleep(0.2)

    # Persist cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)
    return explanations


def _fallback_explain(text: str, score: float) -> str:
    """
    Single-item fallback for explanation if batch parsing fails.
    """
    prompt = (
        "You are an expert financial analyst.\n"
        "Given this text and its sentiment score, explain in 1–2 sentences why the score is appropriate.\n\n"
        f"Text: \"{text}\"\nSentiment score: {score:.2f}\nRationale:"
    )
    resp = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role':'system','content':'You are a helpful financial analyst.'},
                  {'role':'user','content':prompt}],
        temperature=0.0,
        max_tokens=60
    )
    return resp.choices[0].message.content.strip()


def batch_explain(signals_path: str, output_path: str, batch_size: int = 20) -> None:
    """
    Read signals and scored data, merge text, generate batched explanations, and save.
    """
    # Load signals
    sig = pd.read_csv(signals_path, parse_dates=['timestamp'])
    sig['date'] = sig['timestamp'].dt.date
    # Load scored data for text
    scored = pd.read_csv(os.path.join('data','sentiment_scored.csv'), parse_dates=['timestamp'])
    scored['date'] = scored['timestamp'].dt.date
    # Only need text from scored; agg_score comes from signals
    df = pd.merge(
        sig,
        scored[['date','ticker','text']],
        on=['date','ticker'],
        how='left'
    )(sig, scored[['date','ticker','text','agg_score']], on=['date','ticker'], how='left')

    # Generate explanations in batches
    exps = batch_explain_all(df, batch_size)
    df['Explanation'] = exps
    df.drop(columns=['date'], inplace=True)
    df.to_csv(output_path, index=False)
    print(f"Explanations added and saved to {output_path}")


if __name__ == '__main__':
    batch_explain(
        signals_path=os.path.join('data','signals.csv'),
        output_path=os.path.join('data','signals_with_explanations.csv'),
        batch_size=20
    )