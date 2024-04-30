import unicodedata

import aiohttp
import base64
from tonsdk.utils import Address
from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Wallet import Wallet
from ..Contracts.Jetton import Jetton
from ..Enums.Address import AddressForm


class TonApiError(BaseException):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except Exception:
        raise TonApiError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise TonApiError(f'TonApi failed with error: {response_dict}')
    else:
        return response_dict


class TonApiClient:
    def __init__(self,
                 key: str = None,  # api key from tonapi
                 addresses_form: str = AddressForm.USER_FRIENDLY,
                 testnet=False
                 ):
        self.form = addresses_form
        if testnet:
            self.testnet = True
            self.base_url = 'https://testnet.tonapi.io/v2'
        else:
            self.testnet = False
            self.base_url = 'https://tonapi.io/v2'
        if key:
            self.headers = {
                'Authorization': 'Bearer ' + key
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

    async def get_nft_owner(self, nft_address: str):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/nfts/{nft_address}'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            if 'sale' in response:
                return Wallet(self, self._process_address(response['sale']['owner']['address']))
            return Wallet(self, self._process_address(response['owner']['address']))

    async def get_nft_items(self, nft_addresses: list):
        result = []
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/nfts/_bulk'
            params = {
                'account_ids': nft_addresses
            }
            response = await session.post(url=url, json=params, headers=self.headers)
            response = await process_response(response)
            for item in response['nft_items']:
                item['address'] = self._process_address(item['address'])
                item['collection']['address'] = self._process_address(item['collection']['address'])
                item['owner']['address'] = self._process_address(item['owner']['address'])
                item['collection_address'] = item['collection']['address']
                if 'sale' in item:
                    item['sale']['address'] = self._process_address(item['sale']['address'])
                    item['sale']['market']['address'] = self._process_address(item['sale']['market']['address'])
                    item['sale']['owner'] = self._process_address(item['sale']['owner']['address'])
                result.append(NftItem(item, self))
            return result

    async def get_collection(self, collection_address):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/nfts/collections/{collection_address}'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            if 'owner' in response:
                response['owner'] = self._process_address(response['owner']['address'])
            return NftCollection(response, self)

    async def get_collection_items(self, collection: NftCollection, limit: int = 10**9, limit_per_one_request=1000):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/nfts/collections/{collection.address}/items'
            i = 0
            items = []
            while len(items) < limit:
                params = {
                    'limit': limit_per_one_request,
                    'offset': i
                }
                response = await session.get(url=url, params=params, headers=self.headers)
                response = await process_response(response)
                items += [NftItem(self._process_address(item['address']), self) for item in response['nft_items']]
                if len(response['nft_items']) < limit_per_one_request:
                    break
                i += limit_per_one_request
            return items[:limit]

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 100, before_lt: int = 0, after_lt: int = 0):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/blockchain/accounts/{address}/transactions'
            transactions = []
            while len(transactions) < limit:
                params = {
                    'limit': limit_per_one_request,
                    **({'before_lt': before_lt} if before_lt else {}),
                    **({'after_lt': after_lt} if after_lt else {})
                }
                response = await session.get(url=url, params=params, headers=self.headers)
                response = await process_response(response)
                transactions.extend(response['transactions'])
                if transactions:
                    before_lt = transactions[-1]['lt']
                if len(response['transactions']) < limit_per_one_request:
                    break
            result = []
            for tr in transactions:
                tr['data'] = None
                tr['status'] = tr['success']
                tr['fee'] = tr['total_fees']
                tr['hash'] = base64.b64encode(s=bytearray.fromhex(tr['hash'])).decode()
                tr['in_msg']['msg_data'] = tr['in_msg']['decoded_body'] if 'decoded_body' in tr['in_msg'] else None
                tr['in_msg']['msg_data_hex'] = tr['in_msg']['raw_body'] if 'raw_body' in tr['in_msg'] else None
                tr['in_msg']['source'] = self._process_address(tr['in_msg']['source']['address']) if 'source' in tr['in_msg'] else ''
                tr['in_msg']['destination'] = self._process_address(tr['in_msg']['destination']['address']) if 'destination' in tr['in_msg'] else ''
                tr['in_msg']['op_code'] = tr['in_msg']['op_code'].replace('0x', '') if 'op_code' in tr['in_msg'] else ''
                out_msgs = tr['out_msgs']
                for out_msg in out_msgs:
                    out_msg['source'] = self._process_address(out_msg['source']['address']) if 'source' in out_msg else ''
                    out_msg['destination'] = self._process_address(out_msg['destination']['address']) if 'destination' in out_msg else ''
                    out_msg['op_code'] = out_msg['op_code'].replace('0x', '') if 'op_code' in out_msg else ''
                tr['out_msgs'] = out_msgs
                result.append(Transaction(tr))
            return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/jettons/{jetton_master_address}'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            result = response['metadata']
            result['description'] = unicodedata.normalize("NFKD", result['description']) if 'description' in result else ''
            result['address'] = self._process_address(result['address'])
            result['supply'] = response['total_supply']
            return Jetton(result, self)

    async def send_boc(self, boc):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/blockchain/message'
            data = {
                'boc': boc
            }
            response = await session.post(url=url, json=data, headers=self.headers)
            return response.status

    async def get_wallet_seqno(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/wallet/{address}/seqno'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            seqno = response['seqno']
            return seqno

    async def get_balance(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/accounts/{address}'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            balance = response['balance']
            return int(balance)

    async def get_state(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/accounts/{address}'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            state = response['status']
            if state == 'empty' or state == 'uninit':
                return 'uninitialized'
            else:
                return state
