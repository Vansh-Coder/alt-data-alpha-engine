import os
import json
from typing import List, Dict
import pandas as pd
from dotenv import load_dotenv
import openai
import concurrent.futures

# Load OpenAI key and cache
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

CACHE_FILE = os.path.join('data', 'explanation_cache.json')
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'w') as f:
        json.dump({}, f)
with open(CACHE_FILE, 'r') as f:
    _cache: Dict[str, str] = json.load(f)


def _fallback_explain(text: str, score: float) -> str:
    """
    Single-item fallback for explanation if batch parsing fails.
    """
    prompt = (
        "You are an expert financial analyst.\n"
        "Given this text and its sentiment score, explain in single sentences why the score is appropriate.\n\n"
        f"Text: \"{text}\"\nSentiment score: {score:.2f}\nRationale:"
    )
    resp = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are a helpful financial analyst.'},
            {'role': 'user',   'content': prompt}
        ],
        temperature=0.0,
        max_tokens=60
    )
    return resp.choices[0].message.content.strip()


def batch_explain_all(df: pd.DataFrame, batch_size: int = 20, max_workers: int = 5) -> List[str]:
    """
    Batch explanations for rows in df using OpenAI in parallel chunks of batch_size.
    Returns a list of explanations aligned with df.index.
    """
    explanations = [None] * len(df)

    def make_key(text: str, score: float) -> str:
        return f"{score:.3f}: {text}"

    # Collect which rows actually need an API call
    to_call = []  # list of (idx, text, score, key)
    for idx, row in df.iterrows():
        key = make_key(row['text'], row['agg_score'])
        if key in _cache:
            explanations[idx] = _cache[key]
        else:
            to_call.append((idx, row['text'], row['agg_score'], key))

    # Split into batches
    chunks = [
        to_call[i : i + batch_size]
        for i in range(0, len(to_call), batch_size)
    ]

    def _explain_chunk(chunk):
        # Build a single prompt for this chunk
        items = [
            f"{i}. Text: \"{text}\"\n   Sentiment: {score:.2f}"
            for i, (_, text, score, _) in enumerate(chunk, start=1)
        ]
        prompt = (
            "You are an expert financial analyst.\n"
            "For each numbered item, provide a single sentence rationale explaining why the sentiment score is appropriate.\n"
            "Respond with valid JSON as a list of objects, each with 'index' and 'rationale', like:\n"
            "[{\"index\":1,\"rationale\":\"...\"}, ...]\n\n"
            + "\n".join(items)
        )

        resp = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': 'You are a helpful financial analyst.'},
                {'role': 'user',   'content': prompt}
            ],
            temperature=0.0,
            max_tokens=1500
        )
        text_out = resp.choices[0].message.content.strip()

        results = []
        try:
            parsed = json.loads(text_out)
            for item in parsed:
                idx, _, _, key = chunk[item['index'] - 1]
                rationale = item.get('rationale', '').strip()
                results.append((idx, key, rationale))
        except Exception:
            # fallback one by one
            for idx, text, score, key in chunk:
                rationale = _fallback_explain(text, score)
                results.append((idx, key, rationale))

        return results

    # Fire off all chunks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_explain_chunk, c) for c in chunks]
        for future in concurrent.futures.as_completed(futures):
            for idx, key, rationale in future.result():
                explanations[idx] = rationale
                _cache[key] = rationale

    # Persist cache once
    with open(CACHE_FILE, 'w') as f:
        json.dump(_cache, f, indent=2)

    return explanations


def batch_explain(signals_path: str, output_path: str, batch_size: int = 20) -> None:
    """
    Read signals.csv (with agg_score) and sentiment_scored.csv (with text),
    merge them, call batch_explain_all, and write out the results.
    """
    # Load signals.csv (has agg_score)
    sig = pd.read_csv(signals_path, parse_dates=['timestamp'])
    sig['date'] = sig['timestamp'].dt.date

    # Load the text file
    scored = pd.read_csv(
        os.path.join('data', 'sentiment_scored.csv'),
        parse_dates=['timestamp']
    )
    scored['date'] = scored['timestamp'].dt.date

    # Merge so each row has text + agg_score
    df = pd.merge(
        sig,
        scored[['date', 'ticker', 'text']],
        on=['date', 'ticker'],
        how='left'
    )

    # Explain in parallel
    df['Explanation'] = batch_explain_all(df, batch_size=batch_size, max_workers=5)

    # Drop helper column and save
    df.drop(columns=['date'], inplace=True)
    df.to_csv(output_path, index=False)
    print(f"Explanations added and saved to {output_path}")


if __name__ == '__main__':
    batch_explain(
        signals_path=os.path.join('data', 'signals.csv'),
        output_path=os.path.join('data', 'signals_with_explanations.csv'),
        batch_size=20
    )