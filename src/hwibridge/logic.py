import json, subprocess, time
from hwilib.serializations import PSBT
from hwilib.commands import get_client, enumerate as hwi_enumerate
from hwilib import bech32

from .specter_hwi import SpecterClient, enumerate as specter_enumerate

def _enumerate():
    """Standard HWI enumerate() command + Specter."""
    res = hwi_enumerate()
    res += specter_enumerate()
    return res

def get_address(txout, testnet=False):
    """Returns a bech32 address of the txout from it's scriptpubkey"""
    addr = txout.scriptPubKey.hex()
    is_witness, ver, sc = txout.is_witness()
    # TODO: add nested segwit and legacy support here
    if is_witness:
        hrp = "tb" if testnet else "bc"
        addr = bech32.encode(hrp, ver, sc)
    return addr

class HWIBridge:
    """
    A class that represents HWI JSON-RPC methods.

    All methods of this class are callable over JSON-RPC, except _underscored.
    """
    def __init__(self):
        self.devices = []
        self.last = None
        self.enumerate()

    def enumerate(self):
        """
        Returns a list of all connected devices (dicts).
        Updates at most once per second, no matter how often this function is called.
        """
        t = time.time()
        # to avoid spamming by many components
        # we limit update rate to once per second
        if self.last is None or self.last < t-1:
            self.devices = _enumerate()
            self.last = t
        return self.devices

    def get_client(self, fingerprint=None, path=None):
        """
        Returns a hardware wallet class instance 
        with specific fingerprint or/and path
        or None if not connected.
        """
        self.enumerate()
        devs = []
        if fingerprint is not None:
            devs = [dev for dev in self.devices if dev["fingerprint"].lower() == fingerprint.lower()]
        if path is not None:
            devs = [dev for dev in self.devices if dev["path"] == path]
        if len(devs) > 0:
            dev = devs[0]
            if dev["type"] == "specter":
                return SpecterClient(dev["path"])
            else:
                return get_client(dev["type"], dev["path"])
    
    def get_psbt_meta(self, b64_psbt):
        """Parses PSBT transaction and returns a dictionary with useful information.

        Parameters:
            b64_psbt: base64-encoded PSBT transaction.
        Returns:
            A dictionary with keys:
            inputs:  [{ amount, address }, ...]
            outputs: [{ amount, address }, ...]
            fee: value in satoshis
            fingerprints: list of device fingerprints involved in the transaction (hex)
        """
        b64_psbt = b64_psbt.strip()
        psbt = PSBT()
        psbt.deserialize(b64_psbt)
        obj = {
            "inputs": [],
            "outputs": [],
            "fee": 0,
            "fingerprints": [],
        }
        fee = 0
        for inp in psbt.inputs:
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
        for out in psbt.tx.vout:
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
    
    def sign(self, psbt=None, fingerprint=None, path=None):
        """
        Signs base-64 encoded psbt transaction with a device.
        
        Device can be specified by fingerprint or path.
        Returns a base64-encoded psbt trasaction 
        with partial signatures from device.
        """
        client = self.get_client(fingerprint)
        tx = PSBT()
        tx.deserialize(psbt)
        signed_tx = PSBT()
        signed_tx.deserialize(client.sign_tx(tx)['psbt'])
        # copy partial sigs from inputs to initial psbt
        # because signed_psbt may drop certain fields (i.e. in Specter)
        for i,inp in enumerate(signed_tx.inputs):
            for k in inp.partial_sigs:
                tx.inputs[i].partial_sigs[k] = inp.partial_sigs[k]
        return tx.serialize()