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

# Route for RGBW color picker.
@app.route('/rgbw-color')
def rgw_color():
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

    print ("Sending..")
    print (request_string)
    
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
