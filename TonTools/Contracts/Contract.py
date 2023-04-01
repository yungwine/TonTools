import base64
import json

from tonsdk.utils import Address, InvalidAddressError
from .utils import transaction_status


def isBase64(sb):
    try:
        base64.b64decode(sb).decode()
        if isinstance(sb, str):
            sb_bytes = bytes(sb, 'ascii')
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False


class InMsg:
    def __init__(self, data: dict):
        self.created_lt = data['created_lt']
        self.source = data['source']
        self.destination = data['destination']
        self.value = data['value']
        self.msg_data = base64.b64decode(data['msg_data']).decode().split('\x00')[-1] if isBase64(data['msg_data']) else data['msg_data']

    def to_dict(self):
        return {
                'created_lt': self.created_lt,
                'source': self.source,
                'destination': self.destination,
                'value': self.value,
                'msg_data': self.msg_data
            }


class OutMsg:
    def __init__(self, data: dict):
        self.created_lt = data['created_lt']
        self.source = data['source']
        self.destination = data['destination']
        self.value = data['value']
        self.msg_data = base64.b64decode(data['msg_data']).decode().split('\x00')[-1] if isBase64(data['msg_data']) else data['msg_data']

    def to_dict(self):
        return {
                'created_lt': self.created_lt,
                'source': self.source,
                'destination': self.destination,
                'value': self.value,
                'msg_data': self.msg_data
            }


class Transaction:
    def __init__(self, data: dict):
        self.utime = data['utime']
        self.fee = data['fee']
        self.data = data['data']
        self.hash = data['hash']
        self.lt = data['lt']
        self.status = transaction_status(data['data'])
        self.in_msg = InMsg(data['in_msg'])
        self.out_msgs = [OutMsg(out_msg) for out_msg in data['out_msgs']]

    def to_dict(self):
        return {
            'utime': self.utime,
            'fee': self.fee,
            'data': self.data,
            'hash': self.hash,
            'in_msg': self.in_msg.to_dict(),
            'out_msgs': [out_msg.to_dict() for out_msg in self.out_msgs]
        }

    def to_dict_user_friendly(self):
        if not self.out_msgs:
            return {
                'type': 'in',
                'utime': self.utime,
                'status': self.status,
                'hash': self.hash,
                'value': int(self.in_msg.value) / 10**9,
                'from': self.in_msg.source,
                'to': self.in_msg.destination,
                'comment': self.in_msg.msg_data if 'te6' not in self.in_msg.msg_data else ''
            }
        else:
            return {
                'type': 'out',
                'utime': self.utime,
                'status': self.status,
                'hash': self.hash,
                'value': int(self.out_msgs[0].value) / 10**9 if len(self.out_msgs) == 1 else [int(out_msg.value) / 10**9 for out_msg in self.out_msgs],
                'from': self.out_msgs[0].source,
                'to': self.out_msgs[0].destination if len(self.out_msgs) == 1 else [out_msg.destination for out_msg in self.out_msgs],
                'comment': (self.out_msgs[0].msg_data if 'te6' not in self.out_msgs[0].msg_data else '') if len(self.out_msgs) == 1 else [out_msg.msg_data if 'te6' not in out_msg.msg_data else '' for out_msg in self.out_msgs],
            }

    def __str__(self):
        return 'Transaction(' + json.dumps(self.to_dict_user_friendly()) + ')'


class ContractError(BaseException):
    pass


class Contract:
    def __init__(self, address, provider):
        Address(address)  # raises tonsdk.utils.InvalidAddressError if address is not valid
        self.address = address
        self.provider = provider

    async def get_transactions(self, limit: int = 10**9, limit_per_one_request: int = 100):
        return await self.provider.get_transactions(self.address, limit, limit_per_one_request)

    async def run_get_method(self, method: str, stack: list):  # TonCenterClient or LsClient required
        """
        Please, note that currently the response types for TonCenterClient and LsClient are different.
        Will be improved in future versions.
        """
        return await self.provider.run_get_method(method=method, address=self.address, stack=stack)

    async def get_balance(self):  # returns nanoTons
        return await self.provider.get_balance(self.address)

    async def get_state(self):
        return await self.provider.get_state(self.address)