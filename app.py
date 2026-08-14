from flask import Flask, render_template, jsonify, request
from flask_basicauth import BasicAuth
from tinydb import TinyDB, Query
from decouple import config
import serial, json, threading

import sprites, stock

# USB device, a Teensy 3.6 to send serial comms to.
TEENSY = '/dev/serial/by-id/usb-Teensyduino_USB_Serial_5220260-if00'
BAUD = 9600

# Instantiate our web server and database.
app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = config('AUTH_USER')
app.config['BASIC_AUTH_PASSWORD'] = config('AUTH_PASS')
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)
db = TinyDB('db.json')

# One serial handle for the whole process, opened on first use and reused.
#
# This used to open a fresh serial.Serial() on every request and never close it,
# which leaked a file descriptor per request. That was survivable when only a
# human clicking buttons ever talked to the wall, but the stock poller sends a
# frame every minute unattended, so the leak would become hundreds of
# descriptors a day. The lock matters for the same reason: a poll and a user
# request landing together would otherwise interleave their bytes mid-frame and
# the Teensy would parse the result as garbage.
_serial = None
_serial_lock = threading.Lock()

def _port():
    global _serial
    if _serial is None or not _serial.is_open:
        _serial = serial.Serial(TEENSY, BAUD, timeout=2)
    return _serial

def send(request_string):
    """
    Put one command on the wire and return the Teensy's acknowledgement.

    Reconnects once if the port has gone away -- unplugging and replugging the
    Teensy should not require restarting the server.
    """
    global _serial
    with _serial_lock:
        for attempt in (1, 2):
            try:
                port = _port()
                # Drop anything still sitting in the buffer before writing. A
                # <state> request actually produces two lines -- the state reply
                # from processState, then the mode number from respondToServer --
                # and we only read one. Without this, that leftover line becomes
                # the next command's acknowledgement and every reply after it is
                # off by one.
                port.reset_input_buffer()
                port.write(request_string.encode('utf-8'))
                return port.readline().strip().strip(b'<>')
            except (serial.SerialException, OSError):
                if _serial is not None:
                    try:
                        _serial.close()
                    except Exception:
                        pass
                _serial = None
                if attempt == 2:
                    raise

# Get state of Teensy, to set initial values to web app.
def get_state():
    try:
        return send("<state>").split(b',')
    except (serial.SerialException, OSError) as error:
        print("Could not read state: %s" % error)
        return [b'']

def request_and_respond(request_string):
    print ("Sending: " + request_string)

    try:
        mode = send(request_string)
    except (serial.SerialException, OSError) as error:
        return jsonify({'error': str(error)}), 503

    # Remember which mode the wall is on, so the stock poller knows whether it
    # is allowed to draw. Without this it would happily overwrite fire or life.
    _note_active_mode(request_string)

    return jsonify({'response': mode})

# --- Active mode tracking -------------------------------------------------

# The command name most recently sent. The poller only pushes when this is a
# stock command, so selecting another mode in the UI silently parks it.
_active_command = None

def _note_active_mode(request_string):
    global _active_command
    _active_command = request_string.lstrip('<').split(',')[0].rstrip('>')

def stock_is_active():
    return _active_command == 'stock'


# --- Sprites --------------------------------------------------------------

# Sixteen 8x8 sprites, one per physical panel. Every other mode treats the struts
# between panels as damage to route around; here each panel holds exactly one
# sprite and the strut frames it.
SPRITE_PANELS = 16

def get_sprite_layout():
    record = db.get(Query().type == 'sprites')
    if record and len(record.get('layout', [])) == SPRITE_PANELS:
        return [_clamp_sprite(i) for i in record['layout']]
    # Default: one of each, in sheet order.
    return [i % len(sprites.SPRITE_NAMES) for i in range(SPRITE_PANELS)]

def get_sprite_brightness():
    record = db.get(Query().type == 'sprites')
    if record and 'brightness' in record:
        return stock.normalize_brightness(record['brightness'])
    return stock.DEFAULT_BRIGHTNESS

def _clamp_sprite(index):
    try:
        index = int(index)
    except (TypeError, ValueError):
        return 0
    return index if 0 <= index < len(sprites.SPRITE_NAMES) else 0

def _update_sprite_record(fields):
    query = Query()
    if db.get(query.type == 'sprites'):
        db.update(fields, query.type == 'sprites')
    else:
        record = {'type': 'sprites', 'layout': get_sprite_layout(),
                  'brightness': stock.DEFAULT_BRIGHTNESS}
        record.update(fields)
        db.insert(record)

def sprite_frame(layout, brightness):
    """
    <sprites,IIIIIIIIIIIIIIII,NNN> -- 16 choices as 'A'+index, then brightness.

    Choices only, never pixels: 16 sprites of 64 pixels each would be 1024
    values, far beyond one serial frame. The bitmaps live in the firmware.
    """
    choices = ''.join(chr(ord('A') + _clamp_sprite(i)) for i in layout)
    return '<sprites,%s,%d>' % (choices, stock.normalize_brightness(brightness))

def load_template_with_swatches(template, swatch_type, initial_state):
    # Supply swatches to front end.
    swatch_query = Query()
    swatches = db.search(swatch_query.type == swatch_type)
    return render_template(template, swatches=swatches, initialState=initial_state)

# Route for homepage.
@app.route('/')
def index():
    return render_template('index.html')

# Life's generation speed and per-cell fade stagger. Kept here rather than in
# stock.py -- normalize_brightness() there is the pattern to follow, but these
# values are Life-specific and nothing else needs them.
LIFE_DEFAULT_SPEED = 370
LIFE_MIN_SPEED = 80
LIFE_MAX_SPEED = 1500
LIFE_DEFAULT_ORGANIC = 50
LIFE_MIN_ORGANIC = 0
LIFE_MAX_ORGANIC = 100
LIFE_DEFAULT_MUTATION = 0
LIFE_MIN_MUTATION = 0
LIFE_MAX_MUTATION = 100
LIFE_DEFAULT_EMBER = 25
LIFE_MIN_EMBER = 0
LIFE_MAX_EMBER = 100

def normalize_life_speed(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return LIFE_DEFAULT_SPEED
    return max(LIFE_MIN_SPEED, min(LIFE_MAX_SPEED, value))

def normalize_life_organic(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return LIFE_DEFAULT_ORGANIC
    return max(LIFE_MIN_ORGANIC, min(LIFE_MAX_ORGANIC, value))

def normalize_life_mutation(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return LIFE_DEFAULT_MUTATION
    return max(LIFE_MIN_MUTATION, min(LIFE_MAX_MUTATION, value))

def normalize_life_ember(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return LIFE_DEFAULT_EMBER
    return max(LIFE_MIN_EMBER, min(LIFE_MAX_EMBER, value))

# Fireflies: glow shape (fade, hold), density (frequency), and hue spread.
# Same shape as the Life constants above -- Fireflies-specific, so kept here
# rather than in stock.py. Mirrors the firmware clamps in
# processFirefliesTiming(); the firmware clamps again, this is so the UI and
# the DB never carry a value the wall would silently reject.
FIREFLIES_DEFAULT_HUE = 60
FIREFLIES_DEFAULT_FADE = 700
FIREFLIES_MIN_FADE = 100
FIREFLIES_MAX_FADE = 2500
FIREFLIES_DEFAULT_HOLD = 300
FIREFLIES_MIN_HOLD = 0
FIREFLIES_MAX_HOLD = 3000
FIREFLIES_DEFAULT_FREQUENCY = 40
FIREFLIES_MIN_FREQUENCY = 0
FIREFLIES_MAX_FREQUENCY = 100
FIREFLIES_DEFAULT_VARIATION = 40
FIREFLIES_MIN_VARIATION = 0
FIREFLIES_MAX_VARIATION = 100

def normalize_fireflies_hue(value):
    """Wrap to 0-359, tolerating junk input. get_state() hands us bytes, which
    int() accepts."""
    try:
        return int(value) % 360
    except (TypeError, ValueError):
        return FIREFLIES_DEFAULT_HUE

def normalize_fireflies_fade(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return FIREFLIES_DEFAULT_FADE
    return max(FIREFLIES_MIN_FADE, min(FIREFLIES_MAX_FADE, value))

def normalize_fireflies_hold(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return FIREFLIES_DEFAULT_HOLD
    return max(FIREFLIES_MIN_HOLD, min(FIREFLIES_MAX_HOLD, value))

def normalize_fireflies_frequency(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return FIREFLIES_DEFAULT_FREQUENCY
    return max(FIREFLIES_MIN_FREQUENCY, min(FIREFLIES_MAX_FREQUENCY, value))

def normalize_fireflies_variation(value):
    """Clamp to the range the firmware will accept, tolerating junk input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return FIREFLIES_DEFAULT_VARIATION
    return max(FIREFLIES_MIN_VARIATION, min(FIREFLIES_MAX_VARIATION, value))

# Route for Conway's Game of Life.
@app.route('/life')
def life():
    initial_state = {
        'type': 'life',
        'h': 0,
        's': 0,
        'l': 0,
        'speed': LIFE_DEFAULT_SPEED,
        'organic': LIFE_DEFAULT_ORGANIC,
        'mutation': LIFE_DEFAULT_MUTATION,
        'ember': LIFE_DEFAULT_EMBER,
        'minSpeed': LIFE_MIN_SPEED,
        'maxSpeed': LIFE_MAX_SPEED,
        }

    state = get_state()
    if (b'life' == state[0]):
        # <life,h,s,l,speed,organic,mutation,ember> -- newer fields are absent
        # from an older firmware, so default rather than index off the end.
        initial_state = {
            'type': 'life',
            'h': state[1],
            's': state[2],
            'l': state[3],
            'speed': normalize_life_speed(state[4]) if len(state) > 4 else LIFE_DEFAULT_SPEED,
            'organic': normalize_life_organic(state[5]) if len(state) > 5 else LIFE_DEFAULT_ORGANIC,
            'mutation': normalize_life_mutation(state[6]) if len(state) > 6 else LIFE_DEFAULT_MUTATION,
            'ember': normalize_life_ember(state[7]) if len(state) > 7 else LIFE_DEFAULT_EMBER,
            'minSpeed': LIFE_MIN_SPEED,
            'maxSpeed': LIFE_MAX_SPEED,
            }
    elif (b'lifepause' == state[0]):
        # <lifepause,N,speed,organic,mutation,ember> -- no color here, so h/s/l
        # stay at the defaults above, but the sliders still need to restore
        # while paused.
        initial_state = {
            'type': 'life',
            'h': 0,
            's': 0,
            'l': 0,
            'speed': normalize_life_speed(state[2]) if len(state) > 2 else LIFE_DEFAULT_SPEED,
            'organic': normalize_life_organic(state[3]) if len(state) > 3 else LIFE_DEFAULT_ORGANIC,
            'mutation': normalize_life_mutation(state[4]) if len(state) > 4 else LIFE_DEFAULT_MUTATION,
            'ember': normalize_life_ember(state[5]) if len(state) > 5 else LIFE_DEFAULT_EMBER,
            'minSpeed': LIFE_MIN_SPEED,
            'maxSpeed': LIFE_MAX_SPEED,
            }

    return load_template_with_swatches('life.html', 'hsl', initial_state)

# Endpoint for posting life color swatches (to set color for conway's game of life).
@app.route('/_post_life_color/', methods=['POST'])
def _post_life_color():
    data = request.get_json()
    h = data['h']
    s = data['s']
    l = data['l']

    return request_and_respond("<life,"+str(h)+","+str(s)+","+str(l)+">");

# Route to pause/play Conway's Game of Life.
@app.route('/_pause_life/', methods=['POST'])
def _life():
    data = request.get_json()
    return request_and_respond("<lifepause," + str(data['pause']) + ">")

# Endpoint for Life's speed and organic (fade stagger) sliders. Deliberately a
# separate command from <life,...>, which recolors the whole board and would
# erase accumulated genetic drift on every drag -- see processLifeTiming() in
# the firmware.
@app.route('/_post_life_timing/', methods=['POST'])
def _post_life_timing():
    data = request.get_json()
    speed = normalize_life_speed(data.get('speed'))
    organic = normalize_life_organic(data.get('organic'))
    mutation = normalize_life_mutation(data.get('mutation'))
    ember = normalize_life_ember(data.get('ember'))

    return request_and_respond("<lifetiming,"+str(speed)+","+str(organic)+","+str(mutation)+","+str(ember)+">")

# Route for fire.
@app.route('/fire')
def fire():
    initial_state = {
        'type': 'hsl',
        'h':0,
        's':10,
        'l':10
        }

    state = get_state()
    if (b'fire' == state[0]):
        initial_state = {
            'type': 'hsl',
            'h': state[1],
            's': 100,
            'l': 50
            }

    return load_template_with_swatches('fire.html', 'hsl', initial_state)

# Route to pause/play (with) fire.
@app.route('/_pause_fire/', methods=['POST'])
def _fire():
    data = request.get_json()

    return request_and_respond("<firepause," + str(data['pause']) + ">")

# Route to send custom fire color.
@app.route('/_post_fire_color/', methods=['POST'])
def _post_fire_color():
    data = request.get_json()
    h = data['h']
    
    return request_and_respond("<fire,"+str(h)+">")

# Endpoint for posting special .
@app.route('/_post_fire_special/', methods=['POST'])
def _post_fire_special():
    data = request.get_json()
    special = data['special']
    
    return request_and_respond("<specialfire,"+str(special)+">")

# Route for fireflies.
@app.route('/fireflies')
def fireflies():
    initial_state = {
        'type': 'fireflies',
        'h': FIREFLIES_DEFAULT_HUE,
        's': 100,
        'l': 50,
        'fade': FIREFLIES_DEFAULT_FADE,
        'hold': FIREFLIES_DEFAULT_HOLD,
        'frequency': FIREFLIES_DEFAULT_FREQUENCY,
        'variation': FIREFLIES_DEFAULT_VARIATION,
        'minFade': FIREFLIES_MIN_FADE,
        'maxFade': FIREFLIES_MAX_FADE,
        'minHold': FIREFLIES_MIN_HOLD,
        'maxHold': FIREFLIES_MAX_HOLD,
        }

    state = get_state()
    if (b'fireflies' == state[0]):
        # <fireflies,hue,fade,hold,frequency,variation> -- newer fields are
        # absent from an older firmware, so default rather than index off the
        # end. s/l are not on the wire: like Fire, this mode is hue-only and
        # the picker is fed a fixed s=100/l=50.
        initial_state.update({
            'h': normalize_fireflies_hue(state[1]) if len(state) > 1 else FIREFLIES_DEFAULT_HUE,
            'fade': normalize_fireflies_fade(state[2]) if len(state) > 2 else FIREFLIES_DEFAULT_FADE,
            'hold': normalize_fireflies_hold(state[3]) if len(state) > 3 else FIREFLIES_DEFAULT_HOLD,
            'frequency': normalize_fireflies_frequency(state[4]) if len(state) > 4 else FIREFLIES_DEFAULT_FREQUENCY,
            'variation': normalize_fireflies_variation(state[5]) if len(state) > 5 else FIREFLIES_DEFAULT_VARIATION,
            })
    elif (b'firefliespause' == state[0]):
        # <firefliespause,N,fade,hold,frequency,variation> -- no hue here, so
        # it stays at the default above, but the sliders still need to
        # restore while paused. Same shape as the lifepause branch, which
        # likewise doesn't surface the pause flag itself into initial_state --
        # keeping parity rather than introducing an unprecedented field.
        initial_state.update({
            'fade': normalize_fireflies_fade(state[2]) if len(state) > 2 else FIREFLIES_DEFAULT_FADE,
            'hold': normalize_fireflies_hold(state[3]) if len(state) > 3 else FIREFLIES_DEFAULT_HOLD,
            'frequency': normalize_fireflies_frequency(state[4]) if len(state) > 4 else FIREFLIES_DEFAULT_FREQUENCY,
            'variation': normalize_fireflies_variation(state[5]) if len(state) > 5 else FIREFLIES_DEFAULT_VARIATION,
            })

    return load_template_with_swatches('fireflies.html', 'hsl', initial_state)

# Route to pause/play fireflies.
@app.route('/_pause_fireflies/', methods=['POST'])
def _pause_fireflies():
    data = request.get_json()

    return request_and_respond("<firefliespause," + str(data['pause']) + ">")

# Route to send the fireflies color. Hue only, like Fire.
@app.route('/_post_fireflies_color/', methods=['POST'])
def _post_fireflies_color():
    data = request.get_json()
    h = normalize_fireflies_hue(data['h'])

    return request_and_respond("<fireflies,"+str(h)+">")

# Endpoint for the fireflies glow and density sliders. A separate command from
# <fireflies,H> for the same reason /_post_life_timing/ is separate from the
# Life color endpoint -- see processFirefliesTiming() in the firmware.
@app.route('/_post_fireflies_timing/', methods=['POST'])
def _post_fireflies_timing():
    data = request.get_json()
    fade = normalize_fireflies_fade(data.get('fade'))
    hold = normalize_fireflies_hold(data.get('hold'))
    frequency = normalize_fireflies_frequency(data.get('frequency'))
    variation = normalize_fireflies_variation(data.get('variation'))

    return request_and_respond("<firefliestiming,"+str(fade)+","+str(hold)+","+str(frequency)+","+str(variation)+">")

# Route for matrix.
@app.route('/matrix')
def matrix():
    return render_template('matrix.html')

# Route to play/pause matrix.
@app.route('/_pause_matrix/', methods=['POST'])
def _pause_matrix():
    data = request.get_json()

    return request_and_respond("<pausematrix," + str(data['pause']) + ">")

# Endpoint for posting prebuilt matrix color mode.
@app.route('/_post_matrix/', methods=['POST'])
def _post_matrix():
    data = request.get_json()
    request_string = ("<matrix," +
        str(data[0][0])+"," +
        str(data[0][1])+"," +
        str(data[1][0])+"," +
        str(data[1][1])+"," +
        str(data[2][0])+"," +
        str(data[2][1])+"," +
        str(data[3][0])+"," +
        str(data[3][1])+">")

    print ("Sending: " + request_string)
    
    return request_and_respond(request_string)

# Route for Gradient picker.
@app.route('/gradient-color')
def gradient_color():
    initial_state = {
    'type': 'rgbw',
    'r': 0,
    'g': 0,
    'b': 0,
    'w': 10
    }

    state = get_state()
    if (b'rgbw' == state[0]):
        initial_state = {
            'type': 'rgbw',
            'r': state[1],
            'g': state[2],
            'b': state[3],
            'w': state[4]
            }

    return load_template_with_swatches('gradient-color.html', 'rgbw', initial_state)

@app.route('/_post_gradient/', methods=['POST'])
def _post_grade():
    data = request.get_json()
    r = data['r']
    g = data['g']
    b = data['b']
    w = data['w']

    return request_and_respond("<grade,"+str(r)+","+str(g)+","+str(b)+","+str(w)+">")

# Route for HSL color picker.
@app.route('/hsl-color')
def hsl_color():
    initial_state = {
        'type': 'hsl',
        'h':0,
        's':10,
        'l':10
        }

    state = get_state()
    if (b'hsl' == state[0]):
        initial_state = {
            'type': 'hsl',
            'h': state[1],
            's': state[2],
            'l': state[3]
            }

    return load_template_with_swatches('hsl-color.html', 'hsl', initial_state)

# Endpoint for posting hsl color swatches (to update light wall).
@app.route('/_post_hsl_color/', methods=['POST'])
def _post_hsl_color():
    data = request.get_json()
    h = data['h']
    s = data['s']
    l = data['l']

    return request_and_respond("<hsl,"+str(h)+","+str(s)+","+str(l)+">")

# Endpoint for posting hsl color swatches (to update light wall).
@app.route('/_post_hsl_special/', methods=['POST'])
def _post_hsl_special():
    data = request.get_json()
    special = data['special']

    return request_and_respond("<specialhsl,"+str(special)+">")

# Endpoint for saving or deleting HSL color swatches to data storage.
@app.route('/_hsl_swatch_data/', methods=['PUT', 'DELETE'])
def _hsl_swatch_data():
    data = request.get_json()
    status = 'failed';

    print (data)
    
    if ('DELETE' == request.method):
        swatch_query = Query()
        record = db.remove(
            (swatch_query.type == data['type']) &
            (swatch_query.h == data['h']) &
            (swatch_query.s == data['s']) &
            (swatch_query.l == data['l'])
            )
        if (record):
            status = 'record deleted'

    if ('PUT' == request.method):
        record = db.insert({'type': data['type'], 'h': data['h'], 's': data['s'], 'l': data['l']})
        if (record):
            status = 'record added'

    return jsonify({'response': status})

# Route for RGBW color picker.
@app.route('/rgbw-color')
def rgbw_color():
    initial_state = {
        'type': 'rgbw',
        'r': 0,
        'g': 0,
        'b': 0,
        'w': 10
        }
    
    state = get_state()
    if (b'rgbw' == state[0]):
        initial_state = {
            'type': 'rgbw',
            'r': state[1],
            'g': state[2],
            'b': state[3],
            'w': state[4]
            }

    return load_template_with_swatches('rgbw-color.html', 'rgbw', initial_state)

# Endpoint for posting rgbw color swatches (to update light wall).
@app.route('/_post_rgbw_color/', methods=['POST'])
def _post_rgbw_color():
    data = request.get_json()
    r = data['r']
    g = data['g']
    b = data['b']
    w = data['w']
    s = data['s']

    return request_and_respond("<rgbw,"+str(r)+","+str(g)+","+str(b)+","+str(w)+","+str(s)+">")


# Endpoint for saving or deleting RGBW color swatches to data storage.
@app.route('/_rgbw_swatch_data/', methods=['PUT', 'DELETE'])
def _rgbw_swatch_data():
    data = request.get_json()
    status = 'failed';

    print (data)
    
    if ('DELETE' == request.method):
        swatch_query = Query()
        record = db.remove(
            (swatch_query.type == data['type']) &
            (swatch_query.r == data['r']) &
            (swatch_query.g == data['g']) &
            (swatch_query.b == data['b']) &
            (swatch_query.w == data['w'])
            )
        if (record):
            status = 'record deleted'

    if ('PUT' == request.method):
        record = db.insert({'type': data['type'], 'r': data['r'], 'g': data['g'], 'b': data['b'], 'w': data['w']})
        if (record):
            status = 'record added'

    return jsonify({'response': status})


# --- Stock chart ----------------------------------------------------------

# The chosen symbol lives in TinyDB alongside the color swatches, so it survives
# a restart. Only ever one record of this type.
def get_stock_symbol():
    record = db.get(Query().type == 'stock')
    return record['symbol'] if record else ''

def set_stock_symbol(symbol):
    _update_stock_record({'symbol': symbol})

def get_stock_brightness():
    record = db.get(Query().type == 'stock')
    if record and 'brightness' in record:
        return stock.normalize_brightness(record['brightness'])
    return stock.DEFAULT_BRIGHTNESS

def set_stock_brightness(value):
    _update_stock_record({'brightness': stock.normalize_brightness(value)})

def _update_stock_record(fields):
    query = Query()
    if db.get(query.type == 'stock'):
        db.update(fields, query.type == 'stock')
    else:
        record = {'type': 'stock', 'symbol': '', 'brightness': stock.DEFAULT_BRIGHTNESS}
        record.update(fields)
        db.insert(record)

# Refreshes the wall while it is on stock mode. Collaborators are passed in so
# stock.py never has to import this module back.
poller = stock.Poller(
    send=send,
    get_symbol=get_stock_symbol,
    is_active=stock_is_active,
    get_brightness=get_stock_brightness,
    )

# Route for the stock chart.
@app.route('/stock')
def stock_page():
    # No get_state() call here: the symbol comes from the database, and there is
    # nothing else about this mode the Teensy knows better than we do. Skipping it
    # keeps the page load off the serial port entirely.
    initial_state = {
        'type': 'stock',
        'symbol': get_stock_symbol(),
        # Reported rather than hardcoded in the template, so the legend and the
        # slider stay correct if these ever change.
        'days': stock.WINDOW,
        'brightness': get_stock_brightness(),
        'minBrightness': stock.MIN_BRIGHTNESS,
        'maxBrightness': stock.MAX_BRIGHTNESS,
        }

    return render_template('stock.html', initialState=initial_state)

# Endpoint for choosing which symbol to display.
@app.route('/_post_stock/', methods=['POST'])
def _post_stock():
    data = request.get_json()
    symbol = stock.normalize_symbol(data.get('symbol', ''))
    if not symbol:
        return jsonify({'error': 'Enter a ticker symbol.'}), 400

    # Fetch before persisting, so a typo is reported rather than saved. force
    # sends the frame even though the wall is not on stock mode yet, which is
    # what actually switches it over.
    try:
        result = poller.push(symbol, force=True)
    except stock.StockError as error:
        return jsonify({'error': str(error)}), 400
    except (serial.SerialException, OSError) as error:
        return jsonify({'error': str(error)}), 503

    set_stock_symbol(symbol)
    _note_active_mode('<stock')

    return jsonify({
        'response': 'ok',
        'symbol': result['symbol'],
        'price': result['price'],
        'currency': result.get('currency', 'USD'),
        'closes': result['closes'],
        })

# Endpoint for the overall brightness of the stock chart.
@app.route('/_post_stock_brightness/', methods=['POST'])
def _post_stock_brightness():
    data = request.get_json()
    brightness = stock.normalize_brightness(data.get('brightness'))
    set_stock_brightness(brightness)

    # Redraw from cache rather than refetching: only a display setting changed,
    # so going back to the provider would burn a request for identical prices.
    try:
        poller.repaint()
    except stock.StockError:
        # No data cached yet, so there is nothing to redraw. The value is saved
        # and will apply to the first frame.
        pass
    except (serial.SerialException, OSError) as error:
        return jsonify({'error': str(error)}), 503

    return jsonify({'response': 'ok', 'brightness': brightness})

# Endpoint for the web UI's preview, which renders the same layout as the wall.
@app.route('/_stock_data/')
def _stock_data():
    snapshot = poller.snapshot()
    snapshot['symbol'] = get_stock_symbol()
    return jsonify(snapshot)


# Route for the sprite demo.
@app.route('/sprites')
def sprites_page():
    initial_state = {
        'type': 'sprites',
        'layout': get_sprite_layout(),
        'brightness': get_sprite_brightness(),
        'minBrightness': stock.MIN_BRIGHTNESS,
        'maxBrightness': stock.MAX_BRIGHTNESS,
        'names': sprites.SPRITE_NAMES,
        # The palette and bitmaps go to the browser so the preview draws from the
        # same data the firmware does, rather than a hand-made approximation.
        'palette': ['#%02x%02x%02x' % c for c in sprites.SPRITE_PALETTE],
        'sprites': sprites.SPRITE_DATA,
        }

    return render_template('sprites.html', initialState=initial_state)

# Endpoint for placing sprites and setting their brightness.
@app.route('/_post_sprites/', methods=['POST'])
def _post_sprites():
    data = request.get_json()

    layout = data.get('layout')
    if layout is None:
        layout = get_sprite_layout()
    if len(layout) != SPRITE_PANELS:
        return jsonify({'error': 'Expected %d sprite choices.' % SPRITE_PANELS}), 400
    layout = [_clamp_sprite(i) for i in layout]

    brightness = stock.normalize_brightness(
        data.get('brightness', get_sprite_brightness()))

    _update_sprite_record({'layout': layout, 'brightness': brightness})

    try:
        response = send(sprite_frame(layout, brightness))
    except (serial.SerialException, OSError) as error:
        return jsonify({'error': str(error)}), 503
    _note_active_mode('<sprites')

    return jsonify({'response': response.decode('utf-8', 'replace'),
                    'layout': layout, 'brightness': brightness})


# Run locally, accessible via any device on network.
if __name__ == '__main__':
    poller.start()
    app.run(debug=False, host='0.0.0.0', port=config('PORT'))
