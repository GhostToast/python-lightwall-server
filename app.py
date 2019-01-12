from flask import Flask, render_template, jsonify, request
from tinydb import TinyDB, Query
import serial, json

app = Flask(__name__)
db = TinyDB('db.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solid-color')
def solid_color():
    return render_template('solid-color.html')

@app.route('/rgbw-color')
def rgw_color():
    swatch_query = Query()
    swatches = db.search(swatch_query.type == 'rgbw')
    return render_template('rgbw-color.html', swatches=swatches)

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
    
    # send request.
    ser = serial.Serial('/dev/ttyACM0', 9600)
    ser.write(request_string.encode('utf-8'))

    # Send back simple response.
    input = ser.read()
    return jsonify({'response': input})

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
        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
