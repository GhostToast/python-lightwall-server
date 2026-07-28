"""
Extract 8x8 sprites from a sprite sheet into the two generated files:

    ../../lightwall/lightwall/sprites.h   firmware palette + bitmaps
    ../sprites.py                         the same data, for the web preview

Usage:
    python3 tools/extract_sprites.py path/to/sheet.png

Standard library only, including a small PNG reader -- the sheet is 8-bit
truecolor and Pillow is not a dependency of this project.

The sheet this was written against is a 15x8 grid of 8x8 sprites on a
transparency checkerboard, upscaled with resampling. That resampling is why the
sampling below takes a majority vote over the middle of each logical pixel
rather than reading a single point, and why colours get merged onto a shared
palette afterwards -- straight extraction gave the heart 25 colours for its 25
pixels.
"""
import os
import struct
import sys
import zlib
from collections import Counter


# --- Which sprites to take -------------------------------------------------
#
# Chosen for clear silhouettes with useful negative space. Nearly solid sprites
# are deliberately excluded: the floppy disk fills 62 of its 64 pixels and would
# read as a bright square through frosted plexiglass rather than as an object.

CHOSEN = [
    (2, 0, 'heart'),   (7, 0, 'skull'),    (4, 0, 'key'),      (11, 0, 'bolt'),
    (1, 0, 'bell'),    (13, 0, 'flask'),   (2, 1, 'mushroom'), (5, 1, 'cactus'),
    (14, 1, 'ghost'),  (3, 2, 'droplet'),  (9, 2, 'pacman'),   (10, 2, 'cloud'),
    (3, 3, 'star'),    (8, 3, 'lock'),     (13, 3, 'globe'),   (1, 3, 'invader'),
]

# Manhattan distance below which two colours are treated as the same. Tuned to
# collapse resampling noise without flattening real shading.
MERGE_DISTANCE = 78

# Ink thresholds that isolate the cell grid. These are specific to this sheet;
# Sheet() checks the resulting band count and complains rather than guessing.
COLUMN_THRESHOLD = 25
ROW_THRESHOLD = 40
GRID_COLUMNS = 15
GRID_ROWS = 8


# --- PNG reading -----------------------------------------------------------

def read_png(path):
    """Return (width, height, channels, rows) for an 8-bit PNG."""
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('%s is not a PNG' % path)

    pos, idat, meta = 8, [], {}
    while pos < len(data):
        length, ctype = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if ctype == b'IHDR':
            width, height, depth, colour = struct.unpack('>IIBB', body[:10])
            meta.update(width=width, height=height, depth=depth, colour=colour)
        elif ctype == b'IDAT':
            idat.append(body)
        elif ctype == b'IEND':
            break
        pos += 12 + length

    if meta['depth'] != 8:
        raise ValueError('only 8-bit PNGs are supported, got %d' % meta['depth'])
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[meta['colour']]
    width, height = meta['width'], meta['height']
    raw = zlib.decompress(b''.join(idat))
    stride = width * channels

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)

    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                line[i] = (line[i] + paeth(a, b, c)) & 0xFF
        rows.append(bytes(line))
        prev = line
    return width, height, channels, rows


class Sheet(object):
    """A sprite sheet, with its cell grid located and checkerboard learned."""

    def __init__(self, path):
        self.width, self.height, self.channels, self.rows = read_png(path)
        self.columns = self._bands(
            [any(self._sum(x, y) > COLUMN_THRESHOLD for y in range(self.height))
             for x in range(self.width)])
        self.rowbands = self._bands(
            [any(self._sum(x, y) > ROW_THRESHOLD for x in range(self.width))
             for y in range(self.height)])
        if len(self.columns) != GRID_COLUMNS or len(self.rowbands) != GRID_ROWS:
            raise ValueError(
                'expected a %dx%d grid, found %dx%d -- the ink thresholds are '
                'tuned to one specific sheet and need adjusting for another'
                % (GRID_COLUMNS, GRID_ROWS, len(self.columns), len(self.rowbands)))
        self.checker = self._learn_checker()

    def pixel(self, x, y):
        offset = x * self.channels
        row = self.rows[y]
        if self.channels >= 3:
            return (row[offset], row[offset + 1], row[offset + 2])
        return (row[offset],) * 3

    def _sum(self, x, y):
        return sum(self.pixel(x, y))

    @staticmethod
    def _bands(profile):
        """Start and length of each run of True."""
        out, current, start = [], profile[0], 0
        for i in range(1, len(profile)):
            if profile[i] != current:
                if current:
                    out.append((start, i - start))
                current, start = profile[i], i
        if current:
            out.append((start, len(profile) - start))
        return out

    def _learn_checker(self):
        """The checkerboard shades, sampled from cells holding no sprite."""
        seen = Counter()
        for column in range(GRID_COLUMNS - 5, GRID_COLUMNS):
            bx, bw = self.columns[column]
            by, bh = self.rowbands[GRID_ROWS - 1]
            for y in range(by, by + bh):
                for x in range(bx, bx + bw):
                    seen[self.pixel(x, y)] += 1
        return [colour for colour, _ in seen.most_common(3)]

    def is_transparent(self, colour):
        if sum(colour) <= 20:
            return True
        if any(distance(colour, k) <= 40 for k in self.checker):
            return True
        # The checkerboard is a dim desaturated purple: red and blue near equal,
        # green below both. Catches blended shades between the two squares.
        r, g, b = colour
        return r + g + b < 150 and abs(r - b) < 26 and g < r and g < b

    def extract(self, column, row):
        """An 8x8 grid of (r, g, b), or None where transparent."""
        bx, bw = self.columns[column]
        by, bh = self.rowbands[row]
        grid = []
        for ly in range(8):
            line = []
            for lx in range(8):
                xa, xb = bx + int(bw * (lx + .28) / 8), bx + int(bw * (lx + .72) / 8)
                ya, yb = by + int(bh * (ly + .28) / 8), by + int(bh * (ly + .72) / 8)
                votes = Counter(self.pixel(x, y)
                                for y in range(ya, yb + 1)
                                for x in range(xa, xb + 1))
                colour = votes.most_common(1)[0][0]
                line.append(None if self.is_transparent(colour) else colour)
            grid.append(line)
        return grid


# --- Palette quantisation -------------------------------------------------

def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def build_palette(sprites):
    """Most common colours first, skipping any close to one already kept."""
    counts = Counter()
    for grid in sprites:
        for row in grid:
            for colour in row:
                if colour:
                    counts[colour] += 1
    palette = []
    for colour, _ in counts.most_common():
        if all(distance(colour, kept) > MERGE_DISTANCE for kept in palette):
            palette.append(colour)
    return palette


def quantise(grid, palette):
    """Palette indices, where 0 means unlit and entries start at 1."""
    out = []
    for row in grid:
        line = []
        for colour in row:
            if colour is None:
                line.append(0)
            else:
                nearest = min(range(len(palette)),
                              key=lambda i: distance(colour, palette[i]))
                line.append(nearest + 1)
        out.append(line)
    return out


# --- Output ---------------------------------------------------------------

def header_note(palette):
    return """\
   Extracted from a sprite sheet by tools/extract_sprites.py in the server repo.
   The sheet was a resampled upscale, so every logical pixel came out a slightly
   different shade -- the heart used 25 colours for its 25 pixels. Colours within
   a Manhattan distance of %d were therefore merged onto one shared palette. That
   removes the noise and also suits the wall: behind frosted plexiglass subtle
   shading is lost anyway, so bold flat colour reads better.

   Palette index 0 means unlit. Entries 1..%d index the palette below.

   Sprites were chosen for clear silhouettes with useful negative space. Nearly
   solid ones were rejected on purpose -- one filling 62 of 64 pixels reads as a
   bright square through diffusion, not as an object.""" % (MERGE_DISTANCE, len(palette))


def emit_h(names, palette, indexed):
    out = ['/**',
           "   8x8 sprites for the lightwall's sprite mode.",
           '',
           header_note(palette),
           '',
           "   Generated -- do not hand edit. Mirrored by the server's sprites.py.",
           '*/',
           '',
           '#ifndef LIGHTWALL_SPRITES_H',
           '#define LIGHTWALL_SPRITES_H',
           '',
           '#define SPRITE_COUNT %d' % len(indexed),
           '#define SPRITE_SIZE 8',
           '#define SPRITE_PALETTE_SIZE %d' % len(palette),
           '',
           '// Red, green, blue. The white channel stays 0 -- these are colour',
           '// sprites, and mixing in W would only wash them out.',
           'const uint8_t spritePalette[SPRITE_PALETTE_SIZE][3] = {']
    for i, c in enumerate(palette):
        out.append('  { %3d, %3d, %3d }, // %2d  #%02x%02x%02x'
                   % (c[0], c[1], c[2], i + 1, c[0], c[1], c[2]))
    out += ['};',
            '',
            '// Row-major, 64 palette indices per sprite. 0 is unlit.',
            'const uint8_t spriteData[SPRITE_COUNT][SPRITE_SIZE * SPRITE_SIZE] = {']
    for i, (name, grid) in enumerate(zip(names, indexed)):
        out.append('  { // %d %s' % (i, name))
        for row in grid:
            out.append('    ' + ', '.join('%2d' % v for v in row) + ',')
        out.append('  },')
    out += ['};', '', '#endif']
    return '\n'.join(out) + '\n'


def emit_py(names, palette, indexed):
    out = ['"""',
           '8x8 sprite data for the lightwall sprite mode.',
           '',
           header_note(palette).replace('   ', ''),
           '',
           'Generated -- do not hand edit. Mirrored by lightwall/lightwall/sprites.h.',
           '"""',
           '',
           'SPRITE_SIZE = 8',
           '',
           'SPRITE_NAMES = [']
    for name in names:
        out.append('    %r,' % name)
    out += [']',
            '',
            '# (r, g, b) for palette indices 1..%d.' % len(palette),
            'SPRITE_PALETTE = [']
    for i, c in enumerate(palette):
        out.append('    (%3d, %3d, %3d),  # %2d  #%02x%02x%02x'
                   % (c[0], c[1], c[2], i + 1, c[0], c[1], c[2]))
    out += [']',
            '',
            '# Row-major palette indices, 0 is unlit.',
            'SPRITE_DATA = [']
    for i, (name, grid) in enumerate(zip(names, indexed)):
        out.append('    [  # %d %s' % (i, name))
        for row in grid:
            out.append('        ' + ', '.join('%2d' % v for v in row) + ',')
        out.append('    ],')
    out += [']', '']
    return '\n'.join(out)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())

    sheet = Sheet(sys.argv[1])
    sprites = [sheet.extract(column, row) for column, row, _ in CHOSEN]
    names = [name for _, _, name in CHOSEN]
    palette = build_palette(sprites)
    indexed = [quantise(grid, palette) for grid in sprites]

    here = os.path.dirname(os.path.abspath(__file__))
    h_path = os.path.normpath(
        os.path.join(here, '..', '..', 'lightwall', 'lightwall', 'sprites.h'))
    py_path = os.path.normpath(os.path.join(here, '..', 'sprites.py'))
    open(h_path, 'w').write(emit_h(names, palette, indexed))
    open(py_path, 'w').write(emit_py(names, palette, indexed))

    print('%d sprites, %d shared colours' % (len(indexed), len(palette)))
    for name, grid in zip(names, indexed):
        lit = sum(1 for row in grid for v in row if v)
        used = len({v for row in grid for v in row if v})
        print('  %-9s %2d lit, %d colours' % (name, lit, used))
    print('wrote %s' % h_path)
    print('wrote %s' % py_path)


if __name__ == '__main__':
    main()
