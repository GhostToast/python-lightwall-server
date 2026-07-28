# python lightwall server
Python server for bluetooth-controlled light wall using NeoPixels/NeoMatrix

## Configuration

Read from a gitignored `.env` via `python-decouple`:

| Key | Required | Purpose |
| --- | --- | --- |
| `AUTH_USER` | yes | HTTP basic auth username |
| `AUTH_PASS` | yes | HTTP basic auth password |
| `PORT` | yes | Port to serve on |
| `FINNHUB_KEY` | no | Fallback price source for stock mode |
| `ALPHAVANTAGE_KEY` | no | Fallback history source for stock mode |

The two stock keys are only consulted if the primary source fails, so stock mode
works without them.

## Stock mode

`/stock` shows a 32 day sparkline for one ticker, with the symbol on the top row
of panels and the current price on the bottom. The baseline is where the price
sat 32 trading days ago; the filled area between it and the line is the move
since, green above and red below. The rightmost column is today and breathes
gently, so a live display is distinguishable from a frozen one.

Prices come from Yahoo's chart endpoint, which needs no API key but does need a
browser `User-Agent` header -- without one it answers 429. One call returns both
the daily series and the current price. It is an undocumented endpoint, so
`stock.py` keeps a `PROVIDERS` list and falls back to Finnhub plus Alpha Vantage
if it ever changes shape. Note the price is roughly 15 minutes delayed.

A background thread refreshes every minute during market hours and every 15
minutes outside them. It only draws while the wall is actually on stock mode, so
selecting another mode parks it rather than fighting for the display. If fetching
fails it keeps the last good chart up but flags it, and the wall dims to half
brightness rather than presenting stale prices as current.

To iterate on the layout without the hardware:

    python3 stock.py NYT
    python3 stock.py TSLA PFE GOOGL

## Roadmap
- Water effect
- Text mode
- Weather integration
- 3-color gradient
- Horizontal gradient
- Icon/graphic support
- Rotating stock watchlist
