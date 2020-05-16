from flask import Blueprint, request
import json
from hwilib.serializations import PSBT
from hwibridge import (HWIBridge, 
                       get_address, get_psbt_meta)
from hwilib.serializations import PSBT

hwi = HWIBridge()
bridge = Blueprint('bridge', __name__)

@bridge.errorhandler(Exception)
def handle_exception(e):
    # normal exception
    return json.dumps({"error": f"{e}"}), 500

@bridge.route("/enumerate")
def hwi_enumerate():
    return json.dumps(hwi.enumerate())

@bridge.route("/sign", methods=["POST"])
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
