"""
GitHub contribution calendar display mode for the lightwall.

Mirrors stock.py's shape and reasoning: the server does the fetching and
layout arithmetic, and hands the Teensy a precomputed frame it only has to
blit. No arithmetic on the wire, no API key, no new dependency -- this scrapes
the same HTML fragment github.com's own profile page loads via AJAX to render
its contribution calendar:

    https://github.com/users/{username}/contributions

Every day cell is a <td class="ContributionCalendar-day"> carrying
data-date (YYYY-MM-DD) and data-level (0-4, GitHub's own quartile bucketing --
no need to reimplement that math).

Run standalone to see the layout without touching the hardware:

    python3 github.py GhostToast
    python3 github.py torvalds notarealuser123456789
"""

import sys

if sys.version_info[0] < 3:
    raise ImportError(
        'github.py requires Python 3; this is %s. Start the server with '
        'python3 (and install its dependencies for python3).'
        % '.'.join(str(n) for n in sys.version_info[:3]))

import re
import threading
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

import stock  # Sibling module, not an external dependency -- reuses its
              # brightness normalization/defaults rather than duplicating them.


# --- Geometry ---------------------------------------------------------------
#
# The wall is 32 columns wide (see lightwall.ino's chartCol/chartRow), which
# hard-caps history at 32 weeks. One column per week, oldest left, this week
# right, exactly like github.com's own grid. Each day is a 1-wide x DAY_BLOCK-
# tall block of chart rows rather than a single pixel, for chunky, GitHub-
# esque squares instead of a thin sparkline.

CHART_W = 32
CHART_H = 32

GRID_WEEKS = 32
GRID_DAYS = 7
GRID_CELLS = GRID_WEEKS * GRID_DAYS  # 224

DAY_BLOCK = 4                         # Rows per day-square.
TOP_MARGIN = (CHART_H - GRID_DAYS * DAY_BLOCK) // 2  # 2.

PAD = '_'  # Unused here (no text bands), kept for symmetry with stock.py.


# --- Provider ----------------------------------------------------------------

USER_AGENT = 'Mozilla/5.0'
TIMEOUT = 10

CONTRIBUTIONS_URL = 'https://github.com/users/{username}/contributions'

# Every <td ...> tag, so the ones that aren't a contribution day can be
# filtered out below. Order-agnostic on the two attributes we care about --
# HTML attribute order isn't a contract -- so date and level are each found
# with their own regex rather than one combined pattern.
TD_RE = re.compile(r'<td\b[^>]*>', re.IGNORECASE)
DATE_RE = re.compile(r'data-date="([\d-]+)"')
LEVEL_RE = re.compile(r'data-level="(\d+)"')


class GithubError(Exception):
    """The provider could not supply usable data for a username."""


def normalize_username(username):
    """
    Strip anything we cannot safely put on the wire or in a URL. Case is left
    alone -- unlike a ticker symbol, a GitHub username is not case-normalized.
    """
    if not username:
        return ''
    cleaned = ''.join(c for c in username.strip() if c.isalnum() or c == '-')
    return cleaned[:39]  # GitHub's own username length ceiling.


def _fetch_html(username):
    url = CONTRIBUTIONS_URL.format(username=username)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return response.read().decode(charset)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise GithubError('unknown user %s' % username)
        raise GithubError('github http %s' % error.code)


def _parse_days(html):
    """{'YYYY-MM-DD': level} for every contribution day cell in the page."""
    days = {}
    for tag in TD_RE.findall(html):
        if 'ContributionCalendar-day' not in tag:
            continue
        date_match = DATE_RE.search(tag)
        level_match = LEVEL_RE.search(tag)
        if not date_match or not level_match:
            continue
        level = min(4, max(0, int(level_match.group(1))))
        days[date_match.group(1)] = level
    return days


def _window_grid(days_by_date, today=None):
    """
    The most recent GRID_WEEKS weeks, Sunday-aligned like GitHub's own grid.
    Because the window starts on a Sunday, the loop index *is* week*7+weekday
    with no extra math. Dates the scrape didn't return (before the account
    existed, say) default to level 0 -- a blank square is the correct answer
    there, not a workaround.
    """
    today = today or date.today()
    this_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    start = this_sunday - timedelta(weeks=GRID_WEEKS - 1)
    grid = [0] * GRID_CELLS
    for i in range(GRID_CELLS):
        level = days_by_date.get((start + timedelta(days=i)).isoformat())
        if level is not None:
            grid[i] = level
    return grid


def fetch(username):
    """
    Scrape a user's contribution calendar. Raises GithubError with a specific
    complaint on failure, so the caller can surface something useful to the UI.
    """
    username = normalize_username(username)
    if not username:
        raise GithubError('no username given')

    html = _fetch_html(username)
    days = _parse_days(html)
    if not days:
        raise GithubError('no contribution data for %s' % username)

    grid = _window_grid(days)
    # The markup has no data-count, only the already-bucketed data-level, so
    # this is the one derived stat available -- no invented precision.
    active_days = sum(1 for level in grid if level > 0)

    return {'username': username, 'grid': grid, 'active_days': active_days}


# --- Frame building ----------------------------------------------------------

def build_frame(grid, brightness, stale=False):
    """
    Produce the serial frame for one update.

        <github,LLLLLLLL...L (224 chars),F,NNN>

    L  224 contribution levels, one character per day, '0'-'4', flat index
       week*7+day, oldest week first
    F  flag bitfield; bit0 set means the data is stale
    N  overall brightness, 5-255 as decimal

    No default for brightness -- the caller always supplies one, matching
    sprite_frame(layout, brightness)'s precedent in app.py.
    """
    if len(grid) != GRID_CELLS:
        raise GithubError('need %d grid cells to draw a calendar' % GRID_CELLS)

    series = ''.join(str(min(4, max(0, level))) for level in grid)
    flags = 1 if stale else 0

    return '<github,%s,%d,%d>' % (
        series, flags, stock.normalize_brightness(brightness))


def decode_frame(frame):
    """Inverse of build_frame, for tests and the preview renderer."""
    body = frame.strip()
    if not (body.startswith('<') and body.endswith('>')):
        raise ValueError('frame is not delimited by <>')
    parts = body[1:-1].split(',')
    if len(parts) != 4 or parts[0] != 'github':
        raise ValueError('unexpected frame shape: %r' % (parts,))

    series, flags, brightness = parts[1:4]
    if len(series) != GRID_CELLS:
        raise ValueError('expected %d grid chars, got %d' % (GRID_CELLS, len(series)))

    return {
        'grid': [int(c) for c in series],
        'stale': bool(int(flags) & 1),
        'brightness': int(brightness),
    }


# --- Preview rendering --------------------------------------------------------
#
# One implementation serves both the terminal preview and the web UI's canvas,
# same reasoning as stock.py's render_cells: the browser gets these tokens and
# only has to map each to a color, so the layout rule lives in one place.

CELL_EMPTY = ' '  # Top/bottom margin rows -- never drawn by the firmware.

# How each level draws in a terminal, roughly in increasing density.
ASCII_TOKENS = {
    CELL_EMPTY: ' ',
    '0': '.',
    '1': ':',
    '2': '+',
    '3': '#',
    '4': '@',
}


def render_cells(frame):
    """
    Turn an encoded frame into a 32x32 grid of tokens, mirroring what the
    firmware's githubShow() draws -- day blocks included, so the browser
    preview is provably what the wall shows. Deliberately renders from the
    encoded frame rather than the raw grid, so this doubles as a round-trip
    check of the wire format.
    """
    data = decode_frame(frame)
    grid = data['grid']
    cells = [[CELL_EMPTY] * CHART_W for _ in range(CHART_H)]

    for week in range(GRID_WEEKS):
        for day in range(GRID_DAYS):
            token = str(grid[week * GRID_DAYS + day])
            top = TOP_MARGIN + day * DAY_BLOCK
            for sub in range(DAY_BLOCK):
                cells[top + sub][week] = token

    return [''.join(row) for row in cells]


def render_ascii(frame):
    """
    Draw a frame as ASCII with the panel struts marked, so the layout can be
    judged from a terminal.
    """
    cells = render_cells(frame)
    rule = '+' + '+'.join(['-' * 8] * 4) + '+'

    lines = [rule]
    for y, row in enumerate(cells):
        if y and y % 8 == 0:
            lines.append(rule)
        art = ''.join(ASCII_TOKENS.get(token, '?') for token in row)
        lines.append('|' + '|'.join(art[i:i + 8] for i in range(0, CHART_W, 8)) + '|')
    lines.append(rule)

    if decode_frame(frame)['stale']:
        lines.append('(stale data)')
    return '\n'.join(lines)


# --- Polling ------------------------------------------------------------------

# A contribution calendar changes at most once a day, so there is no "market
# hours" analogue to Stock -- one flat interval governs the cadence.
POLL_INTERVAL = 900       # 15 minutes, matching Stock's CLOSED_INTERVAL.
MAX_BACKOFF = 1800        # Ceiling for error backoff.
STALE_AFTER = 3600        # Data older than this is flagged on the wall.


class Poller(threading.Thread):
    """
    Background thread that refreshes the wall while it is showing GitHub mode.

    Collaborators are injected rather than imported so this module never has
    to reach back into app.py:

        send            called with a frame string to put it on the wire
        get_username    returns the username to display, or a falsy value for none
        is_active       returns True only when the wall is actually in github mode
        get_brightness  returns the overall brightness to draw at

    Mirrors stock.Poller closely, minus the market-hours logic.
    """

    def __init__(self, send, get_username, is_active, get_brightness=None):
        super().__init__(daemon=True, name='github-poller')
        self._send = send
        self._get_username = get_username
        self._is_active = is_active
        self._get_brightness = get_brightness or (lambda: stock.DEFAULT_BRIGHTNESS)
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._cache = None       # Last good {username, grid, active_days, fetched_at}.
        self._error = None
        self._last_frame = None  # Suppresses redundant repaints; see push().

    # -- public API --

    def refresh_soon(self):
        """Wake the thread for an immediate poll, e.g. after a username change."""
        self._wake.set()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def snapshot(self):
        """
        Current cached data and error, for the web UI. Includes the token grid
        so the browser can paint exactly what the wall is drawing without
        reimplementing the layout rules.
        """
        with self._lock:
            cache = dict(self._cache) if self._cache else None
            error = self._error
        brightness = stock.normalize_brightness(self._get_brightness())
        if cache:
            cache['stale'] = self._is_stale(cache)
            cache['brightness'] = brightness
            try:
                cache['cells'] = render_cells(build_frame(
                    cache['grid'], brightness, stale=cache['stale']))
            except (GithubError, ValueError):
                cache['cells'] = None
        return {'data': cache, 'error': error, 'brightness': brightness}

    def push(self, username=None, force=False):
        """
        Fetch and display a username now, on the calling thread. Used by the
        route that sets a new username so the UI can report a bad one
        immediately instead of waiting for the next poll.
        """
        username = username or self._get_username()
        if not username:
            raise GithubError('no username selected')

        data = fetch(username)
        with self._lock:
            self._cache = {
                'username': data['username'],
                'grid': data['grid'],
                'active_days': data['active_days'],
                'fetched_at': time.time(),
            }
            self._error = None

        # Only put a frame on the wire when it would actually change the wall.
        if force or self._is_active():
            frame = build_frame(data['grid'], self._get_brightness())
            if force or frame != self._last_frame:
                self._send(frame)
                self._last_frame = frame
        return data

    def repaint(self):
        """
        Redraw from cache without refetching. Used when only a display setting
        changed -- brightness, say -- where going back to GitHub would be
        pointless and would burn a request against the scrape endpoint.
        """
        with self._lock:
            cache = dict(self._cache) if self._cache else None
        if not cache:
            raise GithubError('nothing to redraw yet')

        frame = build_frame(cache['grid'], self._get_brightness(),
                            stale=self._is_stale(cache))
        self._send(frame)
        self._last_frame = frame

    # -- thread body --

    def run(self):
        backoff = 0
        while not self._stop.is_set():
            interval = POLL_INTERVAL

            if self._is_active() and self._get_username():
                try:
                    self.push()
                except (GithubError, OSError) as error:
                    with self._lock:
                        self._error = str(error)
                    backoff = min(max(backoff * 2, POLL_INTERVAL), MAX_BACKOFF)
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
        Keep the last good calendar on the wall when fetching fails, but flag
        it so a dead poller is visible rather than silently showing old data.
        """
        with self._lock:
            cache = dict(self._cache) if self._cache else None
        if not cache:
            return
        try:
            frame = build_frame(cache['grid'], self._get_brightness(),
                                stale=self._is_stale(cache))
            if frame != self._last_frame:
                self._send(frame)
                self._last_frame = frame
        except (GithubError, OSError):
            pass


# --- CLI ----------------------------------------------------------------------

def _preview(usernames):
    status = 0
    for username in usernames:
        print('\n=== %s ===' % normalize_username(username))
        try:
            data = fetch(username)
        except GithubError as error:
            print('failed: %s' % error)
            status = 1
            continue

        frame = build_frame(data['grid'], stock.DEFAULT_BRIGHTNESS)
        print('%d active day(s) of %d' % (data['active_days'], GRID_CELLS))
        print('frame (%d payload chars): %s' % (len(frame) - 2, frame))
        print(render_ascii(frame))
    return status


if __name__ == '__main__':
    sys.exit(_preview(sys.argv[1:] or ['GhostToast']))
