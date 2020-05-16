import json, subprocess, time
from hwilib.serializations import PSBT
from hwilib.commands import get_client, enumerate as hwi_enumerate
from hwilib import bech32

from .specter_hwi import SpecterClient, enumerate as specter_enumerate

def _enumerate():
    try:
        res = hwi_enumerate()
        res += specter_enumerate()
        return res
    except Exception as e:
        print(e)
        return []

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

class HWIBridge:
    def __init__(self):
        self.devices = []
        self.last = None
        self.enumerate()

    def enumerate(self):
        t = time.time()
        # to avoid spamming by many components
        if self.last is None or self.last < t-1:
            self.devices = _enumerate()
            self.last = t
        return self.devices

    def get_client(self, fingerprint):
        self.enumerate()
        client = None
        for dev in self.devices:
            if dev["fingerprint"].lower() == fingerprint.lower():
                if dev["type"] == "specter":
                    return SpecterClient(dev["path"])
                else:
                    return get_client(dev["type"], dev["path"])