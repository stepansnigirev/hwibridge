import json, time, os, subprocess
from functools import wraps

from flask import (Flask, url_for, render_template, jsonify, 
                   request, make_response, redirect)

from hwibridge import HWIBridge
from hwilib.serializations import PSBT
from hwilib import bech32

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
app.token = os.urandom(32).hex()

hwi = HWIBridge()

def format_addr(addr, letters=6, separator=" "):
    extra = ""
    if len(addr) % letters > 0:
        extra = " "*(letters-(len(addr) % letters))
    return separator.join([addr[i:i+letters] for i in range(0, len(addr), letters)])+extra

def get_address(txout):
    addr = txout.scriptPubKey.hex()
    is_witness, ver, sc = txout.is_witness()
    if is_witness:
        addr = bech32.encode("bc", ver, sc)
    return addr


def get_psbt_meta(data):
    data = data.strip()
    psbt = PSBT()
    psbt.deserialize(data)# request.args.get('psbt0')
    obj = {
        "inputs": [],
        "outputs": [],
        "fee": 0,
        "fingerprints": [],
        "base64": data,
    }
    fee = 0
    for i, inp in enumerate(psbt.inputs):
        o = {
            "amount": None,
            "address": None
        }
        if inp.witness_utxo is not None:
            o["amount"] = inp.witness_utxo.nValue
            o["address"] = addr = get_address(inp.witness_utxo)
        if fee is not None and o["amount"] is not None:
            fee += o["amount"]
        # add fingerprints
        for k in inp.hd_keypaths:
            fingerprint = inp.hd_keypaths[k][0].to_bytes(4,'little').hex()
            if fingerprint not in obj["fingerprints"]:
                obj["fingerprints"].append(fingerprint)

        obj["inputs"].append(o)
    for i, out in enumerate(psbt.tx.vout):
        addr = get_address(out)
        o = {
            "amount": out.nValue,
            "address": addr,
        }
        if fee is not None:
            fee -= o["amount"]
        obj["outputs"].append(o)
    obj["fee"] = fee
    return obj

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route("/hwi/enumerate")
def hwi_enumerate():
    return json.dumps(hwi.enumerate())

@app.route("/hwi/sign", methods=["POST"])
def hwi_sign():
    data = json.loads(request.data)
    fingerprint = data["fingerprint"].lower()
    psbt = data["psbt"]
    client = hwi.get_client(fingerprint)
    psbt = PSBT()
    psbt.deserialize(data["psbt"])
    signed_psbt = PSBT()
    signed_psbt.deserialize(client.sign_tx(psbt)['psbt'])
    for i,inp in enumerate(signed_psbt.inputs):
        for k in inp.partial_sigs:
            psbt.inputs[i].partial_sigs[k] = inp.partial_sigs[k]
    data["signed_psbt"] = psbt.serialize()
    return json.dumps(data)

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
    hwi.enumerate()
    app.run(host='127.0.0.1', port=23948, threaded=True, debug=True)

if __name__ == '__main__':
    main()