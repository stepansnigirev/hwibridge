"""
HWI bridge server.

Runs a flask server that creates a web interface for HWI
and optionally gives access to hardware wallets from any website.
Domains that can have access to HWI bridge API can be configured in the web interface.
API is a simple JSON-RPC on top of HWIBridge class (see hwibridge/logic.py)
"""
from flask import (Flask, url_for, render_template, jsonify, 
                   request, make_response, redirect, Response)
from hwibridge import HWIBridge
import json, traceback

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
hwi = HWIBridge()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route("/hwi", methods=["POST"])
def api():
    """JSON-RPC for ... anything. In this case - HWI Bridge"""
    try:
        data = json.loads(request.data)
    except:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}), 500
    return jsonify(hwi.jsonrpc(data))

@app.route('/')
def index():
    return redirect(url_for('upload'))

@app.route('/tx/upload')
def upload():
    return render_template('upload.html', **app.kwargs)

@app.route('/tx/sign', methods=["POST"])
def sign():
    # parse psbt and get back a dict with 
    # inputs, outputs and device fingerprints
    b64_psbt = request.form.get('psbt')
    psbt = hwi.get_psbt_meta(b64_psbt)
    psbt["base64"] = b64_psbt
    return render_template('sign.html', psbt=psbt, **app.kwargs)

def run_server(eel_port=None, debug=True):
    """
    Runs an hwibridge server. 
    If eel_port is provided - includes an iframe with eel, so
    server shuts down when the window is closed.

    Parameters:
        eel_port (int): The port where eel is running. 
                        None by default.
        debug (bool):   Run server in debug mode (hot reload). 
                        Default - True. 
                        If eel_port is defined - always False.
    """
    if eel_port:
        debug=False
    app.kwargs = {"eel_port": eel_port, "hwi": hwi}
    app.run(host='127.0.0.1', port=25441, threaded=True, debug=debug)

if __name__ == '__main__':
    run_server()