import json, time, os, subprocess
from functools import wraps

from flask import (Flask, url_for, render_template, jsonify, 
                   request, make_response, redirect)
from hwibridge import get_psbt_meta

from hwilib.serializations import PSBT
from api import bridge, hwi

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
app.token = os.urandom(32).hex()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/')
def index():
    return render_template('base.html', token=app.token, devices=hwi.devices)

@app.route('/tx/upload')
def upload():
    return render_template('upload.html', token=app.token, devices=hwi.devices)

@app.route('/tx/sign', methods=["POST"])
def sign():
    psbt = get_psbt_meta(request.form.get('psbt'))
    return render_template('sign.html', token=app.token, devices=hwi.devices, psbt=psbt)


def main():
    app.register_blueprint(bridge, url_prefix='/hwi')
    app.run(host='127.0.0.1', port=23948, threaded=True, debug=True)

if __name__ == '__main__':
    main()