import unicodedata

import aiohttp
import base64
from tonsdk.utils import Address
from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Wallet import Wallet
from ..Contracts.Jetton import Jetton


class TonApiError(BaseException):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except:
        raise TonApiError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise TonApiError(f'TonApi failed with error: {response_dict}')
    else:
        return response_dict


class TonApiClient:
    def __init__(self, key: str = None, addresses_form='user_friendly'):  # adresses_form could be 'raw' or 'user_friendly'
        self.form = addresses_form
        self.base_url = 'https://tonapi.io/v1/'
        if key:
            self.headers = {
                'Authorization': 'Bearer ' + key
            }
        else:
            self.headers = {}

    def _process_address(self, address):
        if self.form == 'user_friendly':
            return Address(address).to_string(True, True, True)
        elif self.form == 'raw':
            return Address(address).to_string(is_user_friendly=False)

    async def get_nft_owner(self, nft_address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'nft/getItems'
            params = {
                'addresses': [nft_address]
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            item = response['nft_items'][0]
            if 'sale' in item:
                return self._process_address(item['sale']['owner']['address'])
            return Wallet(self, self._process_address(item['owner']['address']))

    async def get_nft_items(self, nft_addresses: list):
        result = []
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'nft/getItems'
            params = {
                'addresses': nft_addresses
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            for item in response['nft_items']:
                temp = {
                    'address': self._process_address(item['address']),
                    'collection': {
                        'address': self._process_address(item['collection']['address']),
                        'name': item['collection']['name'],
                    },
                    'collection_address': self._process_address(item['collection']['address']),
                    'index': item['index'],
                    'metadata': item['metadata'],
                    'owner': self._process_address(item['owner']['address'])
                }
                if 'sale' in item:
                    temp['sale'] = {
                        'address': self._process_address(item['sale']['address']),
                        'market': {
                            'address': self._process_address(item['sale']['market']['address']),
                            'name': item['sale']['market']['name']
                        },
                        'owner': self._process_address(item['sale']['owner']['address']),
                        'price': {
                            'token_name': item['sale']['price']['token_name'],
                            'value': item['sale']['price']['value'],
                        }
                    }
                result.append(NftItem(temp, self))
            return result

    async def get_collection(self, collection_address):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'nft/getCollection'
            params = {
                'account': collection_address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            result = {
                'address': self._process_address(response['address']),
                'metadata': response['metadata'],
                'next_item_index': response['next_item_index'],
                'owner': self._process_address(response['owner']['address'])
            }
            return NftCollection(result, self)

    async def get_collection_items(self, collection: NftCollection, limit_per_one_request=1000):
        async with aiohttp.ClientSession() as session:
            if not limit_per_one_request:
                limit_per_one_request = 1000
            url = self.base_url + 'nft/searchItems'
            i = 0
            items = []
            while True:
                params = {
                    'collection': collection.address,
                    'limit': limit_per_one_request,
                    'offset': i
                }
                response = await session.get(url=url, params=params, headers=self.headers)
                response = await process_response(response)
                items += [NftItem(self._process_address(item['address']), self) for item in response['nft_items']]
                if len(response['nft_items']) < limit_per_one_request:
                    break
                i += limit_per_one_request
            return items

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 100):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'blockchain/getTransactions'
            transactions = []
            params = {
                'account': address,
                'limit': limit_per_one_request,
                'minLt': 0
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            transactions += response['transactions']
            while len(response['transactions']) == limit_per_one_request and len(transactions) < limit:
                params = {
                    'account': address,
                    'limit': limit_per_one_request,
                    'maxLt': transactions[-1]['lt'],
                    'minLt': 0
                }
                response = await session.get(url=url, params=params, headers=self.headers)
                response = await process_response(response)
                transactions += response['transactions'][1:]
            result = []
            for tr in transactions:
                temp = {
                    'utime': tr['utime'],
                    'fee': tr['fee'],
                    'data': tr['data'],
                    'hash': base64.b64encode(s=bytearray.fromhex(tr['hash'])).decode(),
                    'lt': tr['lt'],
                    'in_msg': {
                        'created_lt': tr['in_msg']['created_lt'],
                        'source': self._process_address(tr['in_msg']['source']['address']) if 'source' in tr['in_msg'] else '',
                        'destination': self._process_address(tr['in_msg']['destination']['address']) if 'destination' in tr['in_msg'] else '',
                        'value': tr['in_msg']['value'],
                        'msg_data': tr['in_msg']['msg_data']
                    },
                    'out_msgs': [
                        {
                            'created_lt': out_msg['created_lt'],
                            'source': self._process_address(out_msg['source']['address']) if 'source' in out_msg else '',
                            'destination': self._process_address(out_msg['destination']['address']) if 'destination' in out_msg else '',
                            'value': out_msg['value'],
                            'msg_data': out_msg['msg_data']
                        }
                        for out_msg in tr['out_msgs']
                    ]
                }
                result.append(Transaction(temp))
            return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'jetton/getInfo'
            params = {
                'account': jetton_master_address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            result = response['metadata']
            result['description'] = unicodedata.normalize("NFKD", result['description'])
            result['address'] = self._process_address(result['address'])
            result['supply'] = response['total_supply']
            return Jetton(result, self)

    async def send_boc(self, boc):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'send/boc'
            data = {
                'boc': boc
            }
            response = await session.post(url=url, json=data, headers=self.headers)
            return response.status

    async def get_wallet_seqno(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'wallet/getSeqno'
            params = {
                'account': address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            seqno = response['seqno']
            return seqno

    async def get_balance(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'account/getInfo'
            params = {
                'account': address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            balance = response['balance']
            return int(balance)

    async def get_state(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + 'account/getInfo'
            params = {
                'account': address
            }
            response = await session.get(url=url, params=params, headers=self.headers)
            response = await process_response(response)
            state = response['status']
            if state == 'empty' or state == 'uninit':
                return 'uninitialized'
            else:
                return state
