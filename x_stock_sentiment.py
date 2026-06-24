#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any

POSITIVE_WORDS = {
    "beat",
    "beats",
    "breakout",
    "bullish",
    "buy",
    "buying",
    "gain",
    "gains",
    "growth",
    "green",
    "long",
    "moon",
    "outperform",
    "rally",
    "strong",
    "surge",
    "up",
    "upside",
}

NEGATIVE_WORDS = {
    "bearish",
    "crash",
    "cut",
    "cuts",
    "decline",
    "down",
    "downgrade",
    "drop",
    "dump",
    "loss",
    "losses",
    "miss",
    "misses",
    "red",
    "risk",
    "sell",
    "selling",
    "short",
    "weak",
}
SCORE_PRECISION = 3


def build_query(symbol: str, extra_query: str | None) -> str:
    """Build an X recent-search query for ticker mentions in English posts."""
    base = f"({symbol} OR ${symbol}) lang:en -is:retweet"
    return f"{base} {extra_query}".strip() if extra_query else base


def fetch_posts(query: str, max_results: int, bearer_token: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,lang,public_metrics",
        }
    )
    request = urllib.request.Request(
        f"https://api.x.com/2/tweets/search/recent?{params}",
        headers={
            "Authorization": "Bearer " + bearer_token,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"X API error {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc

    return payload.get("data", [])


def tokenize(text: str) -> list[str]:
    """Split text into lowercase words, keeping optional ticker-style $ prefixes."""
    return re.findall(r"\$?[a-zA-Z']+", text.lower())


def score_text(text: str) -> tuple[int, str]:
    """Return the net lexicon score and a positive/neutral/negative label."""
    score = 0
    for word in tokenize(text):
        word = word.lstrip("$")
        if word in POSITIVE_WORDS:
            score += 1
        elif word in NEGATIVE_WORDS:
            score -= 1

    if score > 0:
        return score, "positive"
    if score < 0:
        return score, "negative"
    return score, "neutral"


def analyze_posts(posts: list[dict]) -> dict[str, Any]:
    """Return a summary block and per-post sentiment results."""
    labels = Counter()
    scored_posts = []

    for post in posts:
        text = post.get("text", "")
        score, label = score_text(text)
        labels[label] += 1
        scored_posts.append(
            {
                "id": post.get("id"),
                "created_at": post.get("created_at"),
                "sentiment": label,
                "score": score,
                "text": text,
            }
        )

    total = len(scored_posts)
    average_score = (
        round(sum(item["score"] for item in scored_posts) / total, SCORE_PRECISION)
        if total > 0
        else 0
    )
    return {
        "summary": {
            "total_posts": total,
            "positive": labels["positive"],
            "neutral": labels["neutral"],
            "negative": labels["negative"],
            "average_score": average_score,
        },
        "posts": scored_posts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch recent X posts about a stock ticker and run simple sentiment scoring."
    )
    parser.add_argument("symbol", help="Stock ticker symbol, for example AAPL or TSLA")
    parser.add_argument(
        "--query",
        help="Extra query terms to narrow the X search, for example 'earnings OR guidance'",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        choices=range(10, 101),
        metavar="[10-100]",
        help="Number of posts to fetch from X recent search",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bearer_token = os.getenv("X_BEARER_TOKEN")

    if not bearer_token:
        print("Missing X_BEARER_TOKEN environment variable.", file=sys.stderr)
        return 1

    query = build_query(args.symbol.upper(), args.query)

    try:
        posts = fetch_posts(query, args.max_results, bearer_token)
        result = analyze_posts(posts)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output = {
        "symbol": args.symbol.upper(),
        "query": query,
        **result,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
