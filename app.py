from flask import Flask, render_template, jsonify, request
from tinydb import TinyDB, Query
import serial, json

# USB device, a Teensy 3.6 to send serial comms to.
TEENSY = '/dev/serial/by-id/usb-Teensyduino_USB_Serial_5220260-if00'

# Instantiate our web server and database.
app = Flask(__name__)
db = TinyDB('db.json')

# Route for homepage.
@app.route('/')
def index():
    return render_template('index.html')

# Route for matrix.
@app.route('/matrix')
def matrix():
    return render_template('matrix.html')

# Route to pause matrix.
@app.route('/_pause_matrix/', methods=['POST'])
def _pause_matrix():
    data = request.get_json()
 
    request_string = ("<pause," + str(data['pause']) + ">")
    print ("Sending: " + request_string)

    # Send request.
    ser = serial.Serial(TEENSY, 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    mode = ser.read()
    return jsonify({'response': mode})

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
    
    # Send request.
    ser = serial.Serial(TEENSY, 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    mode = ser.read()
    return jsonify({'response': mode})

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
            
    # Supply swatches to front end.
    swatch_query = Query()
    swatches = db.search(swatch_query.type == 'rgbw')
    return render_template('gradient-color.html', swatches=swatches, initialState=initial_state)

@app.route('/_post_gradient/', methods=['POST'])
def _post_grade():
    data = request.get_json()
    r = data['r']
    g = data['g']
    b = data['b']
    w = data['w']

    request_string = "<grade,"+str(r)+","+str(g)+","+str(b)+","+str(w)+">"

    print ("Sending: " + request_string)
    
    # Send request.
    ser = serial.Serial(TEENSY, 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    mode = ser.read()
    return jsonify({'response': mode})

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
            
    # Supply swatches to front end.
    swatch_query = Query()
    swatches = db.search(swatch_query.type == 'rgbw')
    return render_template('rgbw-color.html', swatches=swatches, initialState=initial_state)

# Get state of Teensy, to set initial values to web app.
def get_state():
    # Request mode
    ser = serial.Serial(TEENSY, 9600)
    ser.write(("<state>").encode())

    # Read response, remove whitespace and angle brackets.
    mode = ser.readline().strip().strip(b'<>')
    return mode.split(b',')

# Endpoint for posting rgbw color swatches (to update light wall).
@app.route('/_post_rgbw_color/', methods=['POST'])
def _post_rgbw_color():
    data = request.get_json()
    r = data['r']
    g = data['g']
    b = data['b']
    w = data['w']

    request_string = "<rgbw,"+str(r)+","+str(g)+","+str(b)+","+str(w)+">"

    print ("Sending: " + request_string)
    
    # Send request.
    ser = serial.Serial(TEENSY, 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    mode = ser.read()
    return jsonify({'response': mode})


# Endpoint for saving or deleting color swatches to data storage.
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
    app.run(debug=True, host='0.0.0.0')
