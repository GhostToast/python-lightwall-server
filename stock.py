"""
Stock position display mode for the lightwall.

All of the arithmetic for this mode lives here rather than in the firmware: we
fetch prices, autoscale them into the wall's 32x32 chart space, pick the glyphs
for the ticker and price, and hand the Teensy a precomputed frame it only has to
blit. That matches how every other mode works -- the server decides, the wall
draws.

Standard library only, so this adds no new dependencies to the project.

Run standalone to see the layout without touching the hardware:

    python3 stock.py NYT
    python3 stock.py TSLA PFE GOOGL NOTAREALTICKER
"""

import sys

# Fail loudly and specifically rather than with a confusing stdlib import error.
# Under Python 2 "import urllib.error" reports 'No module named error', which
# gives no hint that the interpreter is the real problem.
if sys.version_info[0] < 3:
    raise ImportError(
        'stock.py requires Python 3; this is %s. Start the server with '
        'python3 (and install its dependencies for python3).'
        % '.'.join(str(n) for n in sys.version_info[:3]))

import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, time as dt_time

# python-decouple is already a project dependency and reads .env, but we fall
# back to the environment so this module still runs standalone for previews.
try:
    from decouple import config as _config
except ImportError:  # pragma: no cover
    def _config(key, default=''):
        return os.environ.get(key, default)


# --- Geometry ---------------------------------------------------------------
#
# The wall is 16 discrete 8x8 panels in a 4x4 grid with physical struts between
# them, which the firmware models as a 38x41 virtual space. We work in a clean
# 32x32 "chart space" here and let the firmware's lookup tables map it onto
# usable virtual coordinates, so nothing in this file has to know about struts.
#
# The one thing we do care about: text must be panel-aligned, because a glyph
# spanning a strut gets bisected by a wooden bar. Each panel holds one 5x7
# glyph, so each text band is exactly 4 characters.

CHART_W = 32
CHART_H = 32

WINDOW = 32           # Trading days shown. Exactly one per usable column.
GLYPH_W = 5
GLYPH_H = 7
TEXT_SLOTS = 4        # 4 panels across, one glyph each.

TOP_BAND_ROW = 0                      # Ticker occupies chart rows 0-6.
BOTTOM_BAND_ROW = CHART_H - GLYPH_H   # Price occupies chart rows 25-31.

# Chart row 0-31 encodes to a single printable character. 'A' + 31 is '`', so
# the whole range avoids the ',' '<' '>' that delimit the wire protocol.
ROW_BASE = ord('A')

PAD = '_'             # Blank glyph. A literal space would be fragile over serial.


# --- Font ------------------------------------------------------------------
#
# 5x7 glyphs, one row per entry, low 5 bits used, MSB is the leftmost pixel.
# This table is mirrored in lightwall/lightwall/font.h -- keep the two in sync.

FONT_5X7 = {
    '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    '2': [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    '3': [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
    '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    'A': [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    'D': [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
    'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'I': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1F],
    'J': [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    'K': [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    'M': [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    'N': [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    'Q': [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    'S': [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'V': [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    'W': [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    'X': [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    'Z': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    '-': [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
    '+': [0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00],
    PAD: [0x00] * GLYPH_H,
}

# Anything we cannot draw becomes blank rather than raising mid-render.
GLYPHS = set(FONT_5X7)


# --- Providers -------------------------------------------------------------

USER_AGENT = 'Mozilla/5.0'
TIMEOUT = 10

YAHOO_URL = ('https://query1.finance.yahoo.com/v8/finance/chart/'
             '{symbol}?range=2mo&interval=1d')
FINNHUB_QUOTE_URL = 'https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}'
ALPHA_DAILY_URL = ('https://www.alphavantage.co/query?function=TIME_SERIES_DAILY'
                   '&symbol={symbol}&apikey={key}')


class StockError(Exception):
    """A provider could not supply usable data for a symbol."""


def _get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        # Decode explicitly rather than handing the raw stream to json.load().
        # urlopen yields bytes, and json only started accepting those in Python
        # 3.6 -- on 3.5 it raises "the JSON object must be str, not 'bytes'".
        charset = response.headers.get_content_charset() or 'utf-8'
        body = response.read()
    return json.loads(body.decode(charset))


def yahoo(symbol):
    """
    Primary provider. One call returns both the daily series and the live price,
    with no API key. It does require a User-Agent header -- without one the
    endpoint answers 429 rather than 200.

    This endpoint is undocumented, so treat a shape change as expected
    eventually. That is what the fallbacks below are for.
    """
    try:
        payload = _get_json(YAHOO_URL.format(symbol=symbol))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise StockError('unknown symbol %s' % symbol)
        raise StockError('yahoo http %s' % error.code)

    result = (payload.get('chart') or {}).get('result')
    if not result:
        detail = ((payload.get('chart') or {}).get('error') or {})
        raise StockError(detail.get('description') or 'no data for %s' % symbol)

    result = result[0]
    meta = result.get('meta') or {}
    quote = (result.get('indicators') or {}).get('quote') or [{}]
    closes = [c for c in (quote[0].get('close') or []) if c is not None]
    if len(closes) < 2:
        raise StockError('not enough history for %s' % symbol)

    return {
        'closes': closes[-WINDOW:],
        'price': meta.get('regularMarketPrice') or closes[-1],
        'currency': meta.get('currency') or 'USD',
    }


def finnhub_alpha(symbol):
    """
    Documented fallback, used only if Yahoo fails. Needs two providers because
    no single free tier covers both live price and history well: Finnhub serves
    the quote, Alpha Vantage the daily series (25 requests/day, end-of-day only
    -- realtime there is paid, gated by exchange licensing).

    Whether Finnhub's free tier still includes historical candles could not be
    confirmed, which is why the series comes from Alpha Vantage instead.
    """
    finnhub_key = _config('FINNHUB_KEY', default='')
    alpha_key = _config('ALPHAVANTAGE_KEY', default='')
    if not finnhub_key or not alpha_key:
        raise StockError('fallback providers need FINNHUB_KEY and ALPHAVANTAGE_KEY')

    series = _get_json(ALPHA_DAILY_URL.format(symbol=symbol, key=alpha_key))
    daily = series.get('Time Series (Daily)')
    if not daily:
        raise StockError(series.get('Note') or series.get('Error Message')
                         or 'alphavantage returned no series')
    closes = [float(daily[day]['4. close']) for day in sorted(daily)][-WINDOW:]
    if len(closes) < 2:
        raise StockError('not enough history for %s' % symbol)

    quote = _get_json(FINNHUB_QUOTE_URL.format(symbol=symbol, key=finnhub_key))
    price = quote.get('c') or closes[-1]

    return {'closes': closes, 'price': price, 'currency': 'USD'}


# Tried in order; the first one that returns wins.
PROVIDERS = [yahoo, finnhub_alpha]


def fetch(symbol):
    """
    Ask each provider in turn for a symbol. Raises StockError with every
    provider's complaint if they all fail, so the caller can surface something
    specific to the UI.
    """
    symbol = normalize_symbol(symbol)
    if not symbol:
        raise StockError('no symbol given')

    problems = []
    for provider in PROVIDERS:
        try:
            data = provider(symbol)
        except StockError as error:
            problems.append('%s: %s' % (provider.__name__, error))
        except (urllib.error.URLError, ValueError, KeyError, IndexError) as error:
            problems.append('%s: %s' % (provider.__name__, error))
        else:
            data['symbol'] = symbol
            return data

    raise StockError('; '.join(problems))


def normalize_symbol(symbol):
    """Uppercase and strip anything we cannot draw or safely put on the wire."""
    if not symbol:
        return ''
    cleaned = ''.join(c for c in symbol.strip().upper() if c.isalnum() or c in '.-')
    return cleaned[:12]


# --- Frame building --------------------------------------------------------

def scale(closes, height=CHART_H):
    """
    Map prices onto chart rows, 0 at the top. Autoscales to the window's own
    range with a little padding so the series never touches the edge.
    """
    low, high = min(closes), max(closes)
    if high == low:
        # A perfectly flat series has no range to scale against. Expand
        # symmetrically so it draws down the middle rather than at an edge.
        low, high = low - 0.5, high + 0.5
    pad = (high - low) * 0.06
    low -= pad
    high += pad
    span = high - low
    return [int(round((height - 1) * (1 - (close - low) / span))) for close in closes]


def format_price(price):
    """
    Fit a price into 4 glyphs, as whole dollars.

    No cents, deliberately. There is nowhere to put a decimal point -- a 1px dot
    would fall in the margin between panels, where a wooden strut hides it -- and
    an implied decimal does not read as one. '7448' looks like $7,448, not
    $74.48. Whole dollars are unambiguous at a glance, which is the whole point
    of a display you read from across the room.

        74.48   -> '__74'
       336.21   -> '_336'
      1234.50   -> '1234'
     12345.00   -> '_12K'   thousands, once 4 digits will not fit
    """
    if price is None:
        return PAD * TEXT_SLOTS
    if price < 10000:
        text = str(int(round(price)))
    else:
        text = str(int(round(price / 1000))) + 'K'
    return text[-TEXT_SLOTS:].rjust(TEXT_SLOTS, PAD)


def format_ticker(symbol):
    """
    Fit a ticker into 4 glyphs. Longer symbols truncate rather than scroll, so
    GOOGL renders as GOOG. Characters with no glyph become blanks.
    """
    text = normalize_symbol(symbol)[:TEXT_SLOTS]
    text = ''.join(c if c in GLYPHS else PAD for c in text)
    return text.ljust(TEXT_SLOTS, PAD)


def build_frame(symbol, closes, price, stale=False):
    """
    Produce the serial frame for one update.

        <stock,SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS,B,TTTT,PPPP,F>

    S  32 chart rows, one character per trading day
    B  baseline row (the oldest close in the window)
    T  ticker, 4 glyphs
    P  price, 4 glyphs
    F  flag bitfield; bit0 set means the data is stale

    52 characters of payload, which is why the firmware's buffSize had to rise
    from 40. Single-character encoding keeps this to one atomic frame instead of
    a chunked protocol with ordering state.
    """
    closes = list(closes)[-WINDOW:]
    if len(closes) < 2:
        raise StockError('need at least 2 closes to draw a chart')

    # Pad a short history by repeating the oldest close, so a newly listed
    # symbol still fills the width instead of drawing a partial chart.
    while len(closes) < WINDOW:
        closes.insert(0, closes[0])

    rows = scale(closes)
    series = ''.join(chr(ROW_BASE + row) for row in rows)
    baseline = chr(ROW_BASE + rows[0])
    flags = 1 if stale else 0

    return '<stock,%s,%s,%s,%s,%d>' % (
        series, baseline, format_ticker(symbol), format_price(price), flags)


def decode_frame(frame):
    """Inverse of build_frame, for tests and the preview renderer."""
    body = frame.strip()
    if not (body.startswith('<') and body.endswith('>')):
        raise ValueError('frame is not delimited by <>')
    parts = body[1:-1].split(',')
    if len(parts) != 6 or parts[0] != 'stock':
        raise ValueError('unexpected frame shape: %r' % (parts,))

    _, series, baseline, ticker, price, flags = parts
    if len(series) != WINDOW:
        raise ValueError('expected %d series chars, got %d' % (WINDOW, len(series)))

    return {
        'rows': [ord(c) - ROW_BASE for c in series],
        'baseline': ord(baseline) - ROW_BASE,
        'ticker': ticker,
        'price': price,
        'stale': bool(int(flags) & 1),
    }


# --- Preview rendering ----------------------------------------------------
#
# One implementation serves both the terminal preview and the web UI's canvas.
# The browser gets these tokens and only has to map each to a color, which keeps
# the font and the layout rules in one place per language instead of three.

CELL_EMPTY = ' '
CELL_GAIN_FILL = 'g'
CELL_GAIN_LINE = 'G'
CELL_LOSS_FILL = 'r'
CELL_LOSS_LINE = 'R'
CELL_BASELINE = '-'
CELL_TEXT = '@'

# How each token draws in a terminal.
ASCII_TOKENS = {
    CELL_EMPTY: ' ',
    CELL_GAIN_FILL: '+',
    CELL_GAIN_LINE: '#',
    CELL_LOSS_FILL: '.',
    CELL_LOSS_LINE: '#',
    CELL_BASELINE: '-',
    CELL_TEXT: '@',
}


def render_cells(frame):
    """
    Turn an encoded frame into a 32x32 grid of tokens, mirroring what the
    firmware's stockChart() draws. Deliberately renders from the encoded frame
    rather than the raw prices, so this doubles as a round-trip check of the
    wire format.
    """
    data = decode_frame(frame)
    rows, baseline = data['rows'], data['baseline']
    grid = [[CELL_EMPTY] * CHART_W for _ in range(CHART_H)]

    for x, y in enumerate(rows):
        up = y <= baseline  # A lower row number is a higher price.

        # Area between the line and the baseline.
        for fill in range(min(y, baseline), max(y, baseline) + 1):
            grid[fill][x] = CELL_GAIN_FILL if up else CELL_LOSS_FILL

        # The baseline itself, over the fill so it stays readable.
        grid[baseline][x] = CELL_BASELINE

        # Line, interpolated from the previous day so steep moves stay joined.
        previous = rows[x - 1] if x else y
        for step in range(min(y, previous), max(y, previous) + 1):
            grid[step][x] = CELL_GAIN_LINE if up else CELL_LOSS_LINE

    _blit(grid, data['ticker'], TOP_BAND_ROW)
    _blit(grid, data['price'], BOTTOM_BAND_ROW)

    return [''.join(row) for row in grid]


def _blit(grid, text, top):
    """
    Knock out a 1px halo, then draw the glyphs. Same two passes as the firmware:
    without the halo the text sits directly on the chart fill and turns to mush
    wherever the series is dense.
    """
    cells = [(slot * 8 + 1, FONT_5X7.get(char, FONT_5X7[PAD]))
             for slot, char in enumerate(text)]

    for pass_ in (0, 1):
        for left, bitmap in cells:
            for row, bits in enumerate(bitmap):
                for column in range(GLYPH_W):
                    if not bits >> (GLYPH_W - 1 - column) & 1:
                        continue
                    if pass_ == 0:
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                y, x = top + row + dy, left + column + dx
                                if 0 <= y < CHART_H and 0 <= x < CHART_W:
                                    grid[y][x] = CELL_EMPTY
                    else:
                        grid[top + row][left + column] = CELL_TEXT


def render_ascii(frame):
    """
    Draw a frame as ASCII with the panel struts marked, so the layout can be
    judged from a terminal.

        @ text (with knockout halo)   # line
        + gain fill                   . loss fill
        - baseline
    """
    cells = render_cells(frame)
    rule = '+' + '+'.join(['-' * 8] * 4) + '+'

    lines = [rule]
    for y, row in enumerate(cells):
        if y and y % 8 == 0:
            lines.append(rule)
        art = ''.join(ASCII_TOKENS[token] for token in row)
        lines.append('|' + '|'.join(art[i:i + 8] for i in range(0, CHART_W, 8)) + '|')
    lines.append(rule)

    if decode_frame(frame)['stale']:
        lines.append('(stale data)')
    return '\n'.join(lines)


# --- Polling ---------------------------------------------------------------

# zoneinfo is stdlib from 3.9. On anything older, fall back to computing the US
# Eastern offset from the DST rule directly -- it is only a handful of lines and
# saves requiring pytz just to decide whether the market is open.
try:
    from zoneinfo import ZoneInfo
    MARKET_TZ = ZoneInfo('America/New_York')
except ImportError:  # pragma: no cover - only on Python < 3.9
    MARKET_TZ = None

MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)

OPEN_INTERVAL = 60         # Seconds between polls while the market is open.
CLOSED_INTERVAL = 900      # Slower outside hours, to catch pre/post drift.
MAX_BACKOFF = 1800         # Ceiling for error backoff.
STALE_AFTER = 3600         # Data older than this is flagged on the wall.


def _eastern_offset(utc):
    """
    Hours to add to UTC to get US Eastern. Daylight saving runs from 2am on the
    second Sunday in March to 2am on the first Sunday in November.
    """
    def first_sunday(year, month):
        # weekday() is Monday 0 .. Sunday 6.
        return 1 + (6 - datetime(year, month, 1).weekday()) % 7

    year = utc.year
    starts = datetime(year, 3, first_sunday(year, 3) + 7, 7)  # 2am EST is 7am UTC
    ends = datetime(year, 11, first_sunday(year, 11), 6)      # 2am EDT is 6am UTC
    return -4 if starts <= utc < ends else -5


def market_now():
    """Current wall-clock time in New York, as a naive datetime."""
    if MARKET_TZ is not None:
        return datetime.now(MARKET_TZ).replace(tzinfo=None)
    utc = datetime.utcnow()
    return utc + timedelta(hours=_eastern_offset(utc))


def is_market_hours(now=None):
    """
    Weekday and clock check against US market hours. Deliberately ignores
    market holidays: polling on Thanksgiving is harmless, since the provider
    just returns the previous close.
    """
    if now is None:
        now = market_now()
    elif now.tzinfo is not None:
        now = (now.astimezone(MARKET_TZ) if MARKET_TZ else now).replace(tzinfo=None)

    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


class Poller(threading.Thread):
    """
    Background thread that refreshes the wall while it is showing stock mode.

    Collaborators are injected rather than imported so this module never has to
    reach back into app.py:

        send        called with a frame string to put it on the wire
        get_symbol  returns the symbol to display, or a falsy value for none
        is_active   returns True only when the wall is actually in stock mode

    That last one matters: without it, a poll would yank the display away from
    whatever mode the user had selected.
    """

    def __init__(self, send, get_symbol, is_active):
        super().__init__(daemon=True, name='stock-poller')
        self._send = send
        self._get_symbol = get_symbol
        self._is_active = is_active
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._cache = None       # Last good {symbol, closes, price, fetched_at}.
        self._error = None
        self._last_frame = None  # Suppresses redundant repaints; see push().

    # -- public API --

    def refresh_soon(self):
        """Wake the thread for an immediate poll, e.g. after a symbol change."""
        self._wake.set()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def snapshot(self):
        """
        Current cached data and error, for the web UI. Includes the token grid so
        the browser can paint exactly what the wall is drawing without
        reimplementing the font and layout rules.
        """
        with self._lock:
            cache = dict(self._cache) if self._cache else None
            error = self._error
        if cache:
            cache['stale'] = self._is_stale(cache)
            try:
                cache['cells'] = render_cells(build_frame(
                    cache['symbol'], cache['closes'], cache['price'],
                    stale=cache['stale']))
            except (StockError, ValueError):
                cache['cells'] = None
        return {'data': cache, 'error': error}

    def push(self, symbol=None, force=False):
        """
        Fetch and display a symbol now, on the calling thread. Used by the
        route that sets a new symbol so the UI can report a bad ticker
        immediately instead of waiting for the next poll.
        """
        symbol = symbol or self._get_symbol()
        if not symbol:
            raise StockError('no symbol selected')

        data = fetch(symbol)
        with self._lock:
            self._cache = {
                'symbol': data['symbol'],
                'closes': data['closes'],
                'price': data['price'],
                'currency': data.get('currency', 'USD'),
                'fetched_at': time.time(),
            }
            self._error = None

        # Only put a frame on the wire when it would actually change the wall.
        # Prices often do not move between polls -- outside market hours they
        # never do -- and the chart rounds to 32 rows, so most refreshes encode
        # to a byte-identical frame. Skipping those keeps the panels untouched.
        if force or self._is_active():
            frame = build_frame(data['symbol'], data['closes'], data['price'])
            if force or frame != self._last_frame:
                self._send(frame)
                self._last_frame = frame
        return data

    # -- thread body --

    def run(self):
        backoff = 0
        while not self._stop.is_set():
            interval = OPEN_INTERVAL if is_market_hours() else CLOSED_INTERVAL

            if self._is_active() and self._get_symbol():
                try:
                    self.push()
                except (StockError, OSError) as error:
                    with self._lock:
                        self._error = str(error)
                    backoff = min(max(backoff * 2, OPEN_INTERVAL), MAX_BACKOFF)
                    interval = backoff
                    self._resend_stale()
                else:
                    backoff = 0

            self._wake.wait(interval)
            self._wake.clear()

    # -- internals --

    def _is_stale(self, cache):
        return (time.time() - cache['fetched_at']) > STALE_AFTER

    def _resend_stale(self):
        """
        Keep the last good chart on the wall when fetching fails, but flag it so
        a dead poller is visible rather than silently showing old prices.
        """
        with self._lock:
            cache = dict(self._cache) if self._cache else None
        if not cache:
            return
        try:
            frame = build_frame(cache['symbol'], cache['closes'],
                                cache['price'], stale=self._is_stale(cache))
            if frame != self._last_frame:
                self._send(frame)
                self._last_frame = frame
        except (StockError, OSError):
            pass


# --- CLI ------------------------------------------------------------------

def _preview(symbols):
    status = 0
    for symbol in symbols:
        print('\n=== %s ===' % normalize_symbol(symbol))
        try:
            data = fetch(symbol)
        except StockError as error:
            print('failed: %s' % error)
            status = 1
            continue

        frame = build_frame(data['symbol'], data['closes'], data['price'])
        closes = data['closes']
        change = (closes[-1] / closes[0] - 1) * 100
        print('%d closes, %.2f -> %.2f (%+.1f%%), live %.2f %s'
              % (len(closes), closes[0], closes[-1], change,
                 data['price'], data['currency']))
        print('frame (%d payload chars): %s' % (len(frame) - 2, frame))
        print(render_ascii(frame))
    return status


if __name__ == '__main__':
    sys.exit(_preview(sys.argv[1:] or ['NYT']))
