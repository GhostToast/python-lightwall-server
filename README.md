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
of panels and the current price, in whole dollars, on the bottom. The baseline is
where the price sat 32 trading days ago; the filled area between it and the line
is the move since, green above and red below.

Prices show no cents. There is nowhere to put a decimal point -- a 1px dot falls
in the margin between panels, where a strut hides it -- and an implied decimal
misreads: `7448` looks like $7,448 rather than $74.48.

It is a still image. The wall repaints only when the data actually changes, and
the server does not even send a frame unless it would look different, so most
refreshes touch nothing at all. Nothing fades, pulses or animates -- at this
brightness any movement is distracting rather than informative. For the same
reason there is no pause control: there is nothing to pause.

Gains are green and losses red, at exact hues 120 and 0 with saturation 100 and
low lightness. At this pixel density up-is-green is worth keeping, since it reads
instantly where any other pairing has to be learned.

Lightness is the only knob for subduing this. Two things that seem like they
should work, and do not:

- **Nudging the hues off the primaries.** "Emerald" 142 and "crimson" 355 put
  blue at 39% and 13% of the dominant channel, and the panels showed aquamarine
  and magenta. Blue bleed matters far more than the numbers suggest because the
  fill covers most of the display. Saturation 100 at exactly 120 and 0 is what
  holds the off-channels at zero.
- **Desaturating.** A dark colour desaturated is just grey -- an amber at
  saturation 55, lightness 7 came out `(27, 19, 8)` and read as cream. Hue
  survives darkness; saturation does not.

What made the first version look like Christmas decoration was lightness alone:
at lightness 38 the green was `(0, 193, 0)`, near full output. It is 18 now.

Every colour is a named constant in the palette block above `stockChart()` in
`lightwall.ino`, including a single `stockBrightness` that scales the whole mode
-- tuning means editing a number there and reflashing. The `colors` map in
`static/app.js` mirrors it for the preview, deliberately lighter than the literal
values because an LED at close range is far brighter than the same numbers on a
monitor.

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
