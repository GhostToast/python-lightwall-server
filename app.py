from flask import Flask, render_template, jsonify, request
from flask_basicauth import BasicAuth
from tinydb import TinyDB, Query
from decouple import config
import serial, json

# USB device, a Teensy 3.6 to send serial comms to.
TEENSY = '/dev/serial/by-id/usb-Teensyduino_USB_Serial_5220260-if00'

# Instantiate our web server and database.
app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = config('AUTH_USER')
app.config['BASIC_AUTH_PASSWORD'] = config('AUTH_PASS')
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)
db = TinyDB('db.json')

# Get state of Teensy, to set initial values to web app.
def get_state():
    # Request mode
    ser = serial.Serial(TEENSY, 9600)
    ser.write(("<state>").encode())

    # Read response, remove whitespace and angle brackets.
    mode = ser.readline().strip().strip(b'<>')
    return mode.split(b',')

def request_and_respond(request_string):
    print ("Sending: " + request_string)

    # Send request.
    ser = serial.Serial(TEENSY, 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    mode = ser.read()
    return jsonify({'response': mode})

def load_template_with_swatches(template, swatch_type, initial_state):
    # Supply swatches to front end.
    swatch_query = Query()
    swatches = db.search(swatch_query.type == swatch_type)
    return render_template(template, swatches=swatches, initialState=initial_state)

# Route for homepage.
@app.route('/')
def index():
    return render_template('index.html')

# Route for Conway's Game of Life.
@app.route('/life')
def life():
    initial_state = {
        'type': 'life',
        'h': 0,
        's': 0,
        'l': 0
        }
    
    state = get_state()
    if (b'life' == state[0]):
        initial_state = {
            'type': 'life',
            'h': state[1],
            's': state[2],
            'l': state[3]
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
        

# Run locally, accessible via any device on network.
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=config('PORT'))
