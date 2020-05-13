import json, subprocess, time
from hwilib.serializations import PSBT
from hwilib.commands import get_client, enumerate as hwi_enumerate

from .specter_hwi import SpecterClient, enumerate as specter_enumerate

def _enumerate():
    try:
        res = hwi_enumerate()
        res += specter_enumerate()
        return res
    except Exception as e:
        print(e)
        return []

class HWIBridge:
    def __init__(self):
        self.devices = []
        self.last = None

    def enumerate(self):
        t = time.time()
        # to avoid spamming by many components
        if self.last is None or self.last < t-1:
            self.devices = _enumerate()
            self.last = t
        return self.devices
