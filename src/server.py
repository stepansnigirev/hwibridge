from flask import (Flask, url_for, render_template, jsonify, 
                   request, make_response, redirect)
from hwibridge import get_psbt_meta
from hwibridge.blueprint import bridge, hwi

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/')
def index():
    return render_template('base.html', **app.kwargs)

@app.route('/tx/upload')
def upload():
    return render_template('upload.html', **app.kwargs)

@app.route('/tx/sign', methods=["POST"])
def sign():
    psbt = get_psbt_meta(request.form.get('psbt'))
    return render_template('sign.html', psbt=psbt, **app.kwargs)

def run_server(eel_port=None, debug=True):
    if eel_port:
        debug=False
    app.kwargs = {"eel_port": eel_port, "hwi": hwi}
    app.register_blueprint(bridge, url_prefix='/hwi')
    app.run(host='127.0.0.1', port=23948, threaded=True, debug=debug)

if __name__ == '__main__':
    run_server()