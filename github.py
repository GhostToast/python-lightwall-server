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
import urllib.parse
import urllib.request
from datetime import date, timedelta

import stock  # Sibling module, not an external dependency -- reuses its
              # brightness normalization/defaults rather than duplicating them.


# --- Geometry ---------------------------------------------------------------
#
# The wall is 32 columns wide (see lightwall.ino's chartWidth), but that no
# longer bounds how much history exists: the firmware owns a continuous
# scroll through the full grid, wrapping from oldest week back to newest on
# its own clock. The server's job is to fetch that full history once and hand
# over a precomputed grid -- no arithmetic on the wire, no per-frame
# scroll-position round-trip.
#
# Day-cells are square: DAY_BLOCK rows tall AND DAY_BLOCK columns wide, so one
# week is DAY_BLOCK screen-columns, not one. Within that footprint, only the
# leading (DAY_BLOCK - 1) rows/columns are actually lit -- the trailing row
# and column are left dark as a 1px gap, so adjacent cells read as distinct
# squares instead of blending into one solid blob. The gap is carved out of
# each cell's own footprint rather than inserted between cells, so it costs
# no extra chart width: a week is still exactly DAY_BLOCK screen-columns, the
# same number of weeks are still visible at once, and no cell's data is ever
# split across the gap or hidden by it.
#
# The browser preview mirrors this shape exactly, just as a tail window --
# CHART_W // DAY_BLOCK weeks, the same width the wall shows at any instant,
# not a scroll-phase-accurate mirror of it (the firmware owns that offset
# independently).

CHART_W = 32
CHART_H = 32

GRID_DAYS = 7
DAY_BLOCK = 4                         # Rows (and columns) per day-square, gap row/column included.
# The wall is 4 panels stacked vertically, 8 rows each -- a physical strut
# sits between every panel, permanently (rows never scroll, unlike columns).
# 7 days * DAY_BLOCK leaves a remainder of 4 rows against the 32-row chart;
# splitting that remainder top/bottom (the old (CHART_H - ...) // 2 = 2)
# offsets every day-block by 2, which is not a multiple of DAY_BLOCK, so
# every other day straddles a strut and is permanently sliced in half. Only
# a margin that is itself a multiple of DAY_BLOCK keeps every block inside
# one panel-half. The remainder can't be split evenly (2 isn't a multiple of
# 4), so it all goes on one side -- here, the bottom, leaving Sunday flush
# with the top edge.
TOP_MARGIN = 0

PREVIEW_WEEKS = CHART_W // DAY_BLOCK  # Weeks visible in the preview at this cell width -- 8.
HISTORY_YEARS = 5    # Default lifetime window fetched from GitHub.
WEEKS_PER_YEAR = 53  # Only used to report an approximate year count in render_ascii; the grid itself is sized from real fetch boundaries, not this.

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


def _fetch_html(username, from_date=None, to_date=None):
    url = CONTRIBUTIONS_URL.format(username=username)
    if from_date and to_date:
        url += '?' + urllib.parse.urlencode(
            {'from': from_date.isoformat(), 'to': to_date.isoformat()})
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


def _fetch_year_days(username, year, today=None):
    """{'YYYY-MM-DD': level} for one calendar year, clamped to today if it's
    the current (partial) year."""
    today = today or date.today()
    start = date(year, 1, 1)
    end = date(year, 12, 31) if year < today.year else today
    return _parse_days(_fetch_html(username, start, end))


def fetch_historical(username, years=HISTORY_YEARS, today=None):
    """
    Every day from all *complete* years before the current one, merged into
    one dict. One HTTP request per year -- only worth re-running when the
    username changes, since this data cannot change once a year has ended.
    """
    today = today or date.today()
    days = {}
    for year in range(today.year - years + 1, today.year):
        days.update(_fetch_year_days(username, year, today))
    return days


def fetch_current_year(username, today=None):
    """Just this calendar year -- cheap enough to run on every poll tick."""
    today = today or date.today()
    return _fetch_year_days(username, today.year, today)


def _full_grid(days_by_date, years=HISTORY_YEARS, today=None):
    """
    Sunday-aligned window running from the oldest date fetch_historical()
    actually queries (Jan 1 of today.year - years + 1) through the current
    partial week -- the lifetime-scroll analogue of the old 32-week
    _window_grid. Anchored to that real fetch boundary rather than a fixed
    years * WEEKS_PER_YEAR week count: counting back a fixed number of weeks
    from today overshoots how far fetch_historical/fetch_current_year
    actually reach, and the overshot cells silently default to level 0 --
    indistinguishable from real quiet weeks, which read as a chunk of missing
    history that never appears no matter how long the scroll runs.

    Because the window starts on a Sunday, the loop index *is*
    week*7+weekday with no extra math. Dates the scrape didn't return
    (before the account existed, say) default to level 0 -- a blank square
    is the correct answer there, not a workaround.
    """
    today = today or date.today()
    this_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    earliest = date(today.year - years + 1, 1, 1)
    start = earliest - timedelta(days=(earliest.weekday() + 1) % 7)
    total_weeks = (this_sunday - start).days // 7 + 1
    cells = total_weeks * GRID_DAYS
    grid = [0] * cells
    for i in range(cells):
        level = days_by_date.get((start + timedelta(days=i)).isoformat())
        if level is not None:
            grid[i] = level
    return grid


def _grid_from_days(days_by_date, years=HISTORY_YEARS, today=None):
    grid = _full_grid(days_by_date, years, today)
    # The markup has no data-count, only the already-bucketed data-level, so
    # this is the one derived stat available -- no invented precision.
    active_days = sum(1 for level in grid if level > 0)
    return grid, active_days


def fetch(username, years=HISTORY_YEARS):
    """
    Scrape a user's full lifetime contribution history (years-1 complete
    years plus the current partial year, one HTTP request apiece). Raises
    GithubError with a specific complaint on failure, so the caller can
    surface something useful to the UI.
    """
    username = normalize_username(username)
    if not username:
        raise GithubError('no username given')

    today = date.today()
    days = fetch_historical(username, years, today)
    days.update(fetch_current_year(username, today))
    if not days:
        raise GithubError('no contribution data for %s' % username)

    grid, active_days = _grid_from_days(days, years, today)
    return {'username': username, 'grid': grid, 'active_days': active_days}


# --- Frame building ----------------------------------------------------------

def build_frame(grid, brightness, stale=False):
    """
    Produce the serial frame for one update.

        <github,LLLLLLLL...L (grid chars, a multiple of 7),F,NNN>

    L  contribution levels, one character per day, '0'-'4', flat index
       week*7+day, oldest week first. Length varies with how many years of
       history were fetched -- the firmware owns the scroll through however
       much arrives.
    F  flag bitfield; bit0 set means the data is stale
    N  overall brightness, 5-255 as decimal

    No default for brightness -- the caller always supplies one, matching
    sprite_frame(layout, brightness)'s precedent in app.py.
    """
    if len(grid) % GRID_DAYS != 0:
        raise GithubError('grid length must be a multiple of %d days' % GRID_DAYS)

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
    if len(series) % GRID_DAYS != 0:
        raise ValueError(
            'grid length must be a multiple of %d days, got %d' % (GRID_DAYS, len(series)))

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

# How each level draws in a terminal, roughly in increasing density. Level 0
# (no commits) renders identically to the untouched margin -- same reasoning
# as githubLevelLight's 0 in lightwall.ino/app.js: a blank day has to actually
# look blank, not just dim, or the grid never reads as empty anywhere.
ASCII_TOKENS = {
    CELL_EMPTY: ' ',
    '0': ' ',
    '1': ':',
    '2': '+',
    '3': '#',
    '4': '@',
}


def render_cells(frame, weeks=PREVIEW_WEEKS):
    """
    Turn an encoded frame into a 32x32 grid of tokens: the most recent `weeks`
    weeks of whatever grid the frame carries, laid out as square day-cells
    with the same trailing 1px gap the firmware's githubShow() leaves --
    see the geometry comment above. The wall itself no longer draws a static
    window like this -- it scrolls continuously through the full grid on its
    own clock -- so this is a tail-slice sanity check, not a live mirror.
    Deliberately renders from the encoded frame rather than the raw grid, so
    this doubles as a round-trip check of the wire format.
    """
    data = decode_frame(frame)
    grid = data['grid']
    total_weeks = len(grid) // GRID_DAYS
    weeks = min(weeks, total_weeks)
    tail = grid[(total_weeks - weeks) * GRID_DAYS:]

    cells = [[CELL_EMPTY] * CHART_W for _ in range(CHART_H)]
    for week in range(weeks):
        left = week * DAY_BLOCK
        for day in range(GRID_DAYS):
            token = str(tail[week * GRID_DAYS + day])
            top = TOP_MARGIN + day * DAY_BLOCK
            for sub in range(DAY_BLOCK - 1):        # Trailing row left as a gap.
                for col in range(DAY_BLOCK - 1):    # Trailing column left as a gap.
                    cells[top + sub][left + col] = token

    return [''.join(row) for row in cells]


def render_ascii(frame):
    """
    Print the grid's lifetime stats, then draw the most recent 32 weeks as
    ASCII with the panel struts marked -- printing years of history as ASCII
    art would be unusable in a terminal, so this mirrors the browser preview.
    """
    data = decode_frame(frame)
    total_weeks = len(data['grid']) // GRID_DAYS
    active_days = sum(1 for level in data['grid'] if level > 0)

    lines = ['%d week(s) of history (~%.1f years), %d active day(s)' %
             (total_weeks, total_weeks / WEEKS_PER_YEAR, active_days)]

    cells = render_cells(frame, weeks=PREVIEW_WEEKS)
    rule = '+' + '+'.join(['-' * 8] * 4) + '+'

    lines.append(rule)
    for y, row in enumerate(cells):
        if y and y % 8 == 0:
            lines.append(rule)
        art = ''.join(ASCII_TOKENS.get(token, '?') for token in row)
        lines.append('|' + '|'.join(art[i:i + 8] for i in range(0, CHART_W, 8)) + '|')
    lines.append(rule)

    if data['stale']:
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
        self._historical_days = None  # {date_iso: level} for years before this one.
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

    def push(self, username=None, force=False, full=False):
        """
        Fetch and display a username now, on the calling thread. Used by the
        route that sets a new username so the UI can report a bad one
        immediately instead of waiting for the next poll.

        The historical (pre-current-year) days are cached across calls and
        only refetched when `full` is set, the username changed, or nothing
        is cached yet -- that data cannot change once a year has ended, so
        re-fetching it every routine tick would be five HTTP requests for
        nothing. The current year is always refetched; it is the only part
        that can actually change.
        """
        username = normalize_username(username or self._get_username())
        if not username:
            raise GithubError('no username selected')

        today = date.today()
        with self._lock:
            cached_username = self._cache['username'] if self._cache else None
            historical = self._historical_days

        if full or historical is None or cached_username != username:
            historical = fetch_historical(username, HISTORY_YEARS, today)

        current = fetch_current_year(username, today)
        days = dict(historical)
        days.update(current)
        if not days:
            raise GithubError('no contribution data for %s' % username)

        grid, active_days = _grid_from_days(days, HISTORY_YEARS, today)

        with self._lock:
            self._historical_days = historical
            self._cache = {
                'username': username,
                'grid': grid,
                'active_days': active_days,
                'fetched_at': time.time(),
            }
            self._error = None
            result = self._cache

        # Only put a frame on the wire when it would actually change the wall.
        if force or self._is_active():
            frame = build_frame(grid, self._get_brightness())
            if force or frame != self._last_frame:
                self._send(frame)
                self._last_frame = frame
        return result

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
        print('frame (%d payload chars): %s' % (len(frame) - 2, frame))
        print(render_ascii(frame))
    return status


if __name__ == '__main__':
    sys.exit(_preview(sys.argv[1:] or ['GhostToast']))
