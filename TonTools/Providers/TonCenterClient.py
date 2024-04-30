import asyncio
from math import ceil

import aiohttp
import base64
from tonsdk.boc import Cell
from ton.utils.cell import read_address
from tonsdk.utils import Address, bytes_to_b64str

from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Wallet import Wallet
from ..Contracts.Jetton import Jetton, JettonWallet
from ..Enums.Address import AddressForm
from .utils import markets_adresses, get, process_jetton_data
from ._orbs_ton_access import get_http_endpoint


class TonCenterClientError(BaseException):
    pass


class GetMethodError(TonCenterClientError):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except Exception:
        raise TonCenterClientError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise TonCenterClientError(f'TonCenter failed with error: {response_dict["error"]}')
    else:
        return response_dict


class TonCenterClient:
    def __init__(self,
                 key: str = None,
                 addresses_form: str = AddressForm.USER_FRIENDLY,
                 base_url=None,
                 testnet=False,
                 orbs_access=False  # https://www.orbs.com/ton-access/
                 ):
        self.form = addresses_form
        self.delay = 0
        self.base_url = base_url
        self.testnet = testnet
        if orbs_access:
            self.headers = {}
            if testnet:
                self.base_url = get_http_endpoint({'network': 'testnet', 'protocol': 'rest'})
                return
            self.base_url = get_http_endpoint({'protocol': 'rest'})
            return
        if testnet:
            if base_url is None:
                self.base_url = 'https://testnet.toncenter.com/api/v2/'
            else:
                self.base_url = base_url
        else:
            if base_url is None:
                self.base_url = 'https://toncenter.com/api/v2/'
            else:
                self.base_url = base_url
        if key:
            self.headers = {
                'X-API-Key': key
            }
        else:
            self.headers = {}

    def _process_address(self, address):
        if self.form == AddressForm.RAW:
            return Address(address).to_string(is_user_friendly=False)
        elif self.form == AddressForm.USER_FRIENDLY:
            if self.testnet:
                return Address(address).to_string(True, True, True, True)
            else:
                return Address(address).to_string(True, True, True)

    def set_delay(self, delay: float = 0.1):
        self.delay = delay

    async def run_get_method(self, method: str, address: str, stack: list):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'runGetMethod'
            data = {
                "address": address,
                "method": method,
                "stack": stack
            }
            await asyncio.sleep(self.delay)
            response = await session.post(url=url, json=data, headers=self.headers)
            response = await process_response(response)
            if response['result']['exit_code'] != 0:
                raise GetMethodError(
                    f'get method {method} for address {self._process_address(address)} exit code is {response["result"]["exit_code"]}')
            return response['result']['stack']

    async def get_nft_owner(self, nft_address: str):
        sale = await self._get_nft_sale(nft_address)
        if not sale:
            data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])
            owner_address = read_address(Cell.one_from_boc(base64.b64decode(data[3][1]['bytes']))).to_string()
        else:
            owner_address = sale['owner']
        return Wallet(self, self._process_address(owner_address))

    async def get_nft_items(self, nft_addresses: list):
        return await asyncio.gather(*[self._get_nft_item(nft_address) for nft_address in nft_addresses])

    async def _get_nft_item(self, nft_address: str):
        data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])

        result = {
            'address': self._process_address(nft_address),
            'index': int(data[1][1], 16),
            'collection_address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2][1]['bytes'])))),
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[3][1]['bytes'])))),
            'collection': {
                'address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2][1]['bytes']))))
            }
        }
        content_data = await self.run_get_method(method='get_nft_content', address=result['collection_address'], stack=[['num', result['index']], ['tvm.Cell', data[4][1]['bytes']]])
        collection_content_url = Cell.one_from_boc(base64.b64decode(content_data[0][1]['bytes'])).bits.get_top_upped_array().decode().split('\x01')[-1]
        # if '\x01' in collection_content_url:
        #     collection_content_url = collection_content_url.split('\x01')[1]
        nft_content_url = collection_content_url + Cell.one_from_boc(base64.b64decode(content_data[0][1]['bytes'])).refs[0].bits.get_top_upped_array().decode()

        result['metadata'] = await get(nft_content_url)

        sale = await self._get_nft_sale(nft_address)
        if not sale:
            return NftItem(result, provider=self)
        else:
            result['sale'] = sale
            return NftItem(result, provider=self)

    async def _get_nft_sale(self, nft_address: str):
        data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])
        owner_address = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[3][1]['bytes']))).to_string())
        try:
            data = await self.run_get_method(method='get_sale_data', address=owner_address, stack=[])
            if len(data) == 10:
                market_address = read_address(Cell.one_from_boc(base64.b64decode(data[3][1]['bytes']))).to_string()
                market_name = markets_adresses.get(market_address, '')
                market_address = self._process_address(market_address)
                real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[5][1]['bytes']))).to_string())
                price = int(data[6][1], 16)
                return {
                    'address': owner_address,
                    'market': {
                        'address': market_address,
                        'name': market_name
                    },
                    'owner': real_owner,
                    'price': {
                        'token_name': 'TON',
                        'value': price,
                    }
                }
            elif len(data) == 7:
                market_address = read_address(Cell.one_from_boc(base64.b64decode(data[0][1]['bytes']))).to_string()
                market_name = markets_adresses.get(market_address, '')
                market_address = self._process_address(market_address)
                real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2][1]['bytes']))).to_string())
                price = int(data[3][1], 16)
                return {
                    'address': owner_address,
                    'market': {
                        'address': market_address,
                        'name': market_name
                    },
                    'owner': real_owner,
                    'price': {
                        'token_name': 'TON',
                        'value': price,
                    }
                }
            elif len(data) >= 11:
                market_address = read_address(Cell.one_from_boc(base64.b64decode(data[3][1]['bytes']))).to_string()
                market_name = markets_adresses.get(market_address, '')
                market_address = self._process_address(market_address)
                real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[5][1]['bytes']))).to_string())
                price = max(int(data[6][1], 16), int(data[16][1], 16)) if len(data) >= 16 else int(data[6][1], 16)
                return {
                    'address': owner_address,
                    'market': {
                        'address': market_address,
                        'name': market_name
                    },
                    'owner': real_owner,
                    'price': {
                        'token_name': 'TON',
                        'value': price,
                    }
                }
        except GetMethodError:
            return False

    async def get_collection(self, collection_address):
        data = await self.run_get_method(method='get_collection_data', address=collection_address, stack=[])
        collection_content_url = Cell.one_from_boc(base64.b64decode(data[1][1]['bytes'])).bits.get_top_upped_array().decode().split('\x01')[-1]
        # if '\x01' in collection_content_url:
        #     collection_content_url = collection_content_url.split('\x01')[1]
        collection_metadata = await get(collection_content_url)
        result = {
            'address': self._process_address(collection_address),
            'next_item_index': int(data[0][1], 16),
            'metadata': collection_metadata,
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2][1]['bytes']))))
        }
        return NftCollection(result, self)

    async def get_collection_items(self, collection: NftCollection, limit_per_one_request=0):
        if not collection.is_full():
            await collection.update()
        if not limit_per_one_request:
            items = await asyncio.gather(*[self.run_get_method(address=collection.address, method='get_nft_address_by_index', stack=[['num', i]]) for i in range(collection.next_item_index)])
        else:
            items = []
            for p in range(ceil(collection.next_item_index / limit_per_one_request)):
                items += await asyncio.gather(*[
                    self.run_get_method(address=collection.address, method='get_nft_address_by_index', stack=[['num', i]]) for i in range(p * limit_per_one_request, min(collection.next_item_index, limit_per_one_request * (p + 1)))])

        result = []
        for data in items:
            result.append(NftItem(self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[0][1]['bytes'])))), self))
        return result

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 100):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'getTransactions'
            transactions = []
            params = {
                'address': address,
                'limit': limit_per_one_request,
                'archival': 1
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            transactions += response['result']
            while len(response['result']) == limit_per_one_request and len(transactions) < limit:
                params = {
                    'address': address,
                    'limit': limit_per_one_request,
                    'hash': transactions[-1]['transaction_id']['hash'],
                    'lt': transactions[-1]['transaction_id']['lt'],
                    'archival': 1
                }
                response = await session.get(url=url, params=params, headers=self.headers)
                response = await process_response(response)
                transactions += response['result'][1:]
            result = []
            for tr in transactions:
                temp = {
                    'utime': tr['utime'],
                    'fee': tr['fee'],
                    'data': tr['data'],
                    'hash': tr['transaction_id']['hash'],
                    'lt': tr['transaction_id']['lt'],
                    'in_msg': {
                        'created_lt': tr['in_msg']['created_lt'],
                        'source': self._process_address(tr['in_msg']['source']) if tr['in_msg']['source'] else '',
                        'destination': self._process_address(tr['in_msg']['destination']) if tr['in_msg']['destination'] else '',
                        'value': tr['in_msg']['value'],
                        'msg_data': tr['in_msg']['msg_data']['text'] if 'text' in tr['in_msg']['msg_data'] else tr['in_msg']['msg_data']['body']
                    },
                    'out_msgs': [
                        {
                            'created_lt': out_msg['created_lt'],
                            'source': self._process_address(out_msg['source']) if out_msg['source'] else '',
                            'destination': self._process_address(out_msg['destination']) if out_msg['destination'] else '',
                            'value': out_msg['value'],
                            'msg_data': out_msg['msg_data']['text'] if 'text' in out_msg['msg_data'] else out_msg['msg_data']['body']
                        }
                        for out_msg in tr['out_msgs']
                    ]
                }
                result.append(Transaction(temp))
            return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        data = await self.run_get_method(method='get_jetton_data', address=jetton_master_address, stack=[])
        result = process_jetton_data(data[3][1]['bytes']) if isinstance(process_jetton_data(data[3][1]['bytes']), dict) else await get(process_jetton_data(data[3][1]['bytes']))
        result['address'] = self._process_address(jetton_master_address)
        result['supply'] = int(data[0][1], 16)

        return Jetton(result, self)

    async def send_boc(self, boc):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'sendBoc'
            data = {
                'boc': boc
            }
            response = await session.post(url=url, json=data, headers=self.headers)
            return response.status

    async def get_wallet_seqno(self, address: str):
        data = await self.run_get_method(address=address, method='seqno', stack=[])
        return int(data[0][1], 16)

    async def get_balance(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'getAddressBalance'
            params = {
                'address': address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            return int(response['result'])

    async def get_state(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'getAddressState'
            params = {
                'address': address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            return response['result']

    async def get_jetton_wallet_address(self, jetton_master_address: str, owner_address: str):
        cell = Cell()
        cell.bits.write_address(Address(owner_address))
        data = await self.run_get_method(address=jetton_master_address, method='get_wallet_address', stack=[["tvm.Slice", bytes_to_b64str(cell.to_boc(False))]])
        jetton_wallet_address = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[0][1]['bytes']))).to_string())
        return jetton_wallet_address

    async def get_jetton_wallet(self, jetton_wallet_address: str):
        data = await self.run_get_method(address=jetton_wallet_address, method='get_wallet_data', stack=[])
        wallet = {
            'address': jetton_wallet_address,
            'balance': int(data[0][1], 16),
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[1][1]['bytes'])))),
            'jetton_master_address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2][1]['bytes'])))),
            'jetton_wallet_code': data[3][1]['bytes'],
        }
        return JettonWallet(wallet, self)
