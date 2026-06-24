# copilot-teste

Simple Python example for stock sentiment on X (Twitter).

## Usage

Set your X API bearer token:

```bash
export X_BEARER_TOKEN="your-token"
```

Run the script with a ticker:

```bash
python x_stock_sentiment.py AAPL
```

Optional extra search filters:

```bash
python x_stock_sentiment.py TSLA --query "earnings OR delivery" --max-results 50
```

## What it does

- fetches recent English X posts for a stock symbol
- excludes retweets
- applies a small rule-based sentiment score
- prints JSON with a summary and per-post sentiment

This is a lightweight starter example and not a production sentiment model.