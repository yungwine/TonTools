import json
from pathlib import Path


file = Path(__file__).parent / 'jettons.json'


class _JettonMasterMeta(type):
    def __getattr__(cls, item):
        with open(file, 'r') as f:
            jettons = json.load(f)
        if item.upper() in jettons:
            return jettons[item.upper()]
        else:
            raise AttributeError(f"'{cls.__name__}' object has no attribute '{item}'")


class JettonMasterAddress(metaclass=_JettonMasterMeta):
    pass
