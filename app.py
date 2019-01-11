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
    r = request.form['red']
    g = request.form['green']
    b = request.form['blue']
    w = request.form['white']

    request_string = "<rgbw,"+str(r)+","+str(g)+","+str(b)+","+str(w)+">"

    print ("Sending..")
    print (request_string)
    
    # send request.
    ser = serial.Serial('/dev/ttyACM0', 9600)
    ser.write(request_string.encode('utf-8'))
    
    input = ser.read()
    return jsonify({'response': input})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
