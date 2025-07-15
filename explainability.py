import os
import json
import hashlib
import time
import logging
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv
import openai

# Setup logging for errors
ERROR_LOG = os.path.join('data', 'explain_errors.log')
logging.basicConfig(filename=ERROR_LOG, level=logging.ERROR,
                    format='%(asctime)s %(levelname)s %(message)s')

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
MAX_TEXT_LEN    = 500  # truncate long texts
DEFAULT_BATCH   = 20
RETRY_COUNT     = 3
RETRY_DELAY     = 1.0  # seconds backoff


def _make_key(text: str, score: float) -> str:
    """Generate a fixed-length cache key via SHA256 of truncated text+score"""
    txt = (text[:MAX_TEXT_LEN] + '...') if len(text) > MAX_TEXT_LEN else text
    digest = hashlib.sha256(txt.encode('utf-8')).hexdigest()
    return f"{score:.3f}:{digest}"


def _ai_call(**kwargs) -> Any:
    """Wrapper for new OpenAI v1 chat completion API with retry."""
    for i in range(RETRY_COUNT):
        try:
            # Use new API path
            return openai.chat.completions.create(**kwargs)
        except openai.RateLimitError as e:
            if i < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY * (2**i))
            else:
                logging.error(f"RateLimitError: {e}")
                raise
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            raise


def _fallback_explain(text: str, score: float) -> str:
    """Single-item fallback rationale in one sentence."""
    txt = text[:MAX_TEXT_LEN] + '...' if len(text) > MAX_TEXT_LEN else text
    prompt = (
        f"Text: \"{txt}\"\nSentiment: {score:.2f}\n"
        "Explain in exactly one succinct sentence why this score fits."  
    )
    messages = [
        {'role': 'system', 'content': (
            'You are a helpful financial analyst. Respond with exactly one sentence.')},
        {'role': 'user', 'content': prompt}
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
    Batch explanations for each row in df, with caching, retry, and logging.
    Returns list aligned with df.index.
    """
    explanations = [None] * len(df)
    to_call: List[Any] = []  # (idx, text, score, key)

    # Determine rows needing API calls
    for idx, row in df.iterrows():
        key = _make_key(row['text'], row['agg_score'])
        if key in _cache:
            explanations[idx] = _cache[key]
        else:
            txt = row['text']
            txt = txt[:MAX_TEXT_LEN] + '...' if len(txt) > MAX_TEXT_LEN else txt
            to_call.append((idx, txt, row['agg_score'], key))

    # Split into chunks
    chunks = [to_call[i:i+batch_size] for i in range(0, len(to_call), batch_size)]

    for chunk in chunks:
        # Build the batch prompt
        items = []
        for i, (_, txt, score, _) in enumerate(chunk, start=1):
            items.append(f"{i}. Text: \"{txt}\"\n   Sentiment: {score:.2f}")
        system_msg = (
            "You are an expert financial analyst. Provide one-sentence rationales. "
            "Respond with JSON only: a list of {index: int, rationale: string}."
        )
        user_prompt = system_msg + "\n\n" + "\n".join(items)
        messages = [
            {'role': 'system', 'content': system_msg},
            {'role': 'user', 'content': user_prompt}
        ]

        raw = ""  # ensure defined
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
        except Exception as e:
            logging.error(f"Chunk parse or API error: {e}\nRaw response: {raw}")
            # Fallback: individual calls
            for idx, txt, score, key in chunk:
                try:
                    rationale = _fallback_explain(txt, score)
                except Exception as e2:
                    logging.error(f"Fallback error: {e2}")
                    rationale = ""
                explanations[idx] = rationale
                _cache[key] = rationale

    # Persist cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)

    return explanations


def batch_explain(
    signals_path: str,
    scored_path:  str,
    output_path:  str,
    batch_size:   int = DEFAULT_BATCH
) -> None:
    """
    Merge on full timestamp + ticker, then explain and save.
    """
    sig = pd.read_csv(signals_path, parse_dates=['timestamp'])
    scored = pd.read_csv(scored_path, parse_dates=['timestamp'])

    # Merge on timestamp + ticker
    df = pd.merge(
        sig[['timestamp','ticker','agg_score']],
        scored[['timestamp','ticker','text']],
        on=['timestamp','ticker'], how='left'
    )

    df['Explanation'] = batch_explain_all(df, batch_size=batch_size)
    df.to_csv(output_path, index=False)
    print(f"Explanations written to {output_path}")


if __name__ == '__main__':
    batch_explain(
        signals_path=os.path.join('data', 'signals.csv'),
        scored_path=os.path.join('data', 'sentiment_scored.csv'),
        output_path=os.path.join('data', 'signals_with_explanations.csv'),
        batch_size=DEFAULT_BATCH
    )