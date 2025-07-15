import os
import json
import hashlib
import time
from typing import List, Dict, Any

import pandas as pd
from dotenv import load_dotenv
import openai

from signals import load_signals

# Load OpenAI key and cache
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

CACHE_FILE = os.path.join('data', 'explanation_cache.json')
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'w') as f:
        json.dump({}, f)
with open(CACHE_FILE, 'r') as f:
    _cache: Dict[str, str] = json.load(f)

# Constants
MAX_TEXT_LEN  = 500   # truncate long texts
DEFAULT_BATCH = 20
RETRY_COUNT   = 3
RETRY_DELAY   = 1.0   # seconds backoff

def _make_key(text: str, score: float) -> str:
    """Generate a fixed-length cache key via SHA256 of truncated text+score."""
    txt = text[:MAX_TEXT_LEN] + '...' if len(text) > MAX_TEXT_LEN else text
    digest = hashlib.sha256(txt.encode('utf-8')).hexdigest()
    return f"{score:.3f}:{digest}"

def _ai_call(**kwargs) -> Any:
    """Wrapper for OpenAI chat completions with retry."""
    for i in range(RETRY_COUNT):
        try:
            return openai.chat.completions.create(**kwargs)
        except openai.RateLimitError:
            if i < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY * (2**i))
            else:
                raise
        except Exception:
            raise

def _fallback_explain(text: str, score: float) -> str:
    """Fallback single-item explanation."""
    txt = text[:MAX_TEXT_LEN] + '...' if len(text) > MAX_TEXT_LEN else text
    prompt = (
        f"Text: \"{txt}\"\nSentiment: {score:.2f}\n"
        "Explain in exactly one succinct sentence why this score fits."
    )
    messages = [
        {'role': 'system', 'content': 'You are a helpful financial analyst. Respond with exactly one sentence.'},
        {'role': 'user',   'content': prompt}
    ]
    resp = _ai_call(
        model='gpt-3.5-turbo',
        messages=messages,
        temperature=0.0,
        max_tokens=60
    )
    return resp.choices[0].message.content.strip()

def batch_explain_all(
    df: pd.DataFrame,
    batch_size: int = DEFAULT_BATCH
) -> List[str]:
    """
    Batch explanations for each row in df, with caching and retry.
    Returns list aligned with df.index.
    """
    explanations = [None] * len(df)
    to_call: List[Any] = []

    # Identify rows needing API calls
    for idx, row in df.iterrows():
        key = _make_key(row['text'], row['agg_score'])
        if key in _cache:
            explanations[idx] = _cache[key]
        else:
            txt = row['text'][:MAX_TEXT_LEN] + '...' if len(row['text']) > MAX_TEXT_LEN else row['text']
            to_call.append((idx, txt, row['agg_score'], key))

    # Process in batches
    for i in range(0, len(to_call), batch_size):
        chunk = to_call[i : i + batch_size]

        # Build batch prompt
        items = [
            f"{j+1}. Text: \"{txt}\"\n   Sentiment: {score:.2f}"
            for j, (_, txt, score, _) in enumerate(chunk)
        ]
        system_msg = (
            "You are an expert financial analyst. Provide one-sentence rationales. "
            "Respond with JSON only: a list of {index: int, rationale: string}."
        )
        messages = [
            {'role': 'system', 'content': system_msg},
            {'role': 'user',   'content': "\n\n".join(items)}
        ]

        raw = ""
        try:
            resp = _ai_call(
                model='gpt-3.5-turbo',
                messages=messages,
                temperature=0.0,
                max_tokens=1500
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            for item in parsed:
                idx, _, _, key = chunk[item['index'] - 1]
                rationale = item.get('rationale', '').strip()
                explanations[idx] = rationale
                _cache[key] = rationale
        except Exception:
            # fallback per item
            for idx, txt, score, key in chunk:
                try:
                    rationale = _fallback_explain(txt, score)
                except Exception:
                    rationale = ""
                explanations[idx] = rationale
                _cache[key] = rationale

    # Save cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)

    return explanations

def batch_explain(
    window: int,
    scored_path:  str = "data/sentiment_scored.csv",
    output_path:  str = None,
    batch_size:   int = DEFAULT_BATCH
) -> None:
    """
    Load signals for `window` days, merge with scored text, explain, and save.
    """
    # Load the signals for the given window
    sig = load_signals(window)
    # Load scored text
    scored = pd.read_csv(scored_path, parse_dates=['timestamp'])

    # Merge on timestamp + ticker
    df = pd.merge(
        sig[['timestamp','ticker','agg_score']],
        scored[['timestamp','ticker','text']],
        on=['timestamp','ticker'], how='left'
    )

    # Generate explanations
    df['Explanation'] = batch_explain_all(df, batch_size=batch_size)

    # Determine output path if not provided
    if output_path is None:
        output_path = f"data/signals_{window}d_with_explanations.csv"

    df.to_csv(output_path, index=False)
    print(f"Explanations written to {output_path}")

if __name__ == '__main__':
    # Change the window here if you want 1d, 3d, or 5d explanations
    batch_explain(window=1)