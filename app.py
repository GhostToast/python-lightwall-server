from flask import Flask, render_template, jsonify, request
import serial

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solid-color')
def solid_color():
    return render_template('solid-color.html')

@app.route('/rgbw-color')
def rgw_color():
    return render_template('rgbw-color.html')

@app.route('/_post_solid_color/', methods=['POST'])
def _post_solid_color():
    color = request.form['color']

    # send request.
    ser = serial.Serial('/dev/ttyACM0', 9600)
    ser.write(color.encode())
    input = ser.read()
    print ("Response: " + str(input))

    return jsonify({'color': color, 'response': input})

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
