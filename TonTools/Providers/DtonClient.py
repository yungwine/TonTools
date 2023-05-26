import asyncio
from datetime import datetime
from math import ceil

import aiohttp
import base64

import requests
from tonsdk.boc import Cell
from tonsdk.utils import Address, b64str_to_bytes, bytes_to_b64str

from .utils import get, markets_adresses
from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Jetton import Jetton, JettonWallet


class DtonError(BaseException):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except:
        raise DtonError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise DtonError(f'dton failed with error: {response_dict}')
    else:
        return response_dict


class DtonClient:
    def __init__(self,
                 key: str = None,  # dton api key
                 addresses_form='user_friendly',  # addresses_form could be 'raw' or 'user_friendly'
                 testnet=False,
                 private_graphql=False
                 ):
        self.form = addresses_form
        if testnet:
            self.testnet = True
            self.base_url = 'https://testnet.dton.io/'
        else:
            self.testnet = False
            self.base_url = 'https://dton.io/'
        if private_graphql:
            self.base_url += 'graphql_private/'
        else:
            self.base_url += 'graphql/'
        if key:
            response = requests.get(url=self.base_url + f'login?token={key}')
            if not response.json()['success']:
                raise DtonError('invalid api token')
            self.cookies = response.cookies.get_dict()  # get cookies for login
        else:
            self.cookies = {}

    def _process_address(self, address):
        if self.form == 'raw':
            return Address(address).to_string(is_user_friendly=False)
        elif self.form == 'user_friendly':
            if self.testnet:
                return Address(address).to_string(True, True, True, True)
            else:
                return Address(address).to_string(True, True, True)

    @staticmethod
    def get_friendly(address: str):
        return Address(address).to_string(True, True, True)

    def get_addr_from_wc_hex(self, wc: int, hex: str):
        return self._process_address(
            Address(str(wc) + ':' + hex).to_string()
        )

    async def send_query(self, graphql_query: str, variables=None):
        if variables is None:
            variables = {}
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            response = await session.post(url=self.base_url, json={'query': graphql_query, 'variables': variables})
            response = await process_response(response)
            return response['data']

    async def run_get_method(self, address: str, method: str, stack: list):
        query = '''
            mutation get_method ($address: String, $method: String, $stack: [StackEntryInput]) {
                run_method (
                    account_search_by_address: {address_friendly: $address}
                    method_name: $method
                    stack: $stack
                )	{
                    exit_code
                    gas_used
                    vm_steps
                    success
                    stack {
                      value_type
                      value
                    }
                }
            }
        '''

        var = {
            "address": self.get_friendly(address),
            "method": method,
            "stack": stack
        }

        data = (await self.send_query(query, var))['run_method']

        if not data['success']:
            raise DtonError(f'get method {method} for address {self._process_address(address)} exit code is {data["exit_code"]}')

        return data['stack']

    async def get_nft_owner(self, nft_address: str):
        query = '''
            query get_nft_owner($address_hex: String, $address_wc: Int) {
                account_states(address: $address_hex, workchain: $address_wc) {
                    parsed_nft_owner_address_address
                    parsed_nft_owner_address_workchain
                    parsed_owner_is_seller
                    parsed_seller_nft_prev_owner_address_address
                    parsed_seller_nft_prev_owner_address_workchain
                }
            }
        '''
        var = {
            'address_hex': Address(nft_address).hash_part.hex().upper(),
            'address_wc': 0
        }
        result = await self.send_query(query, variables=var)
        if result['account_states'][0]['parsed_owner_is_seller']:
            var = {
                'address_hex': result['account_states'][0]['parsed_nft_owner_address_address'],
                'address_wc': result['account_states'][0]['parsed_nft_owner_address_workchain']
            }
            result = await self.send_query(query, variables=var)
            owner = Address(str(result['account_states'][0]['parsed_seller_nft_prev_owner_address_workchain']) + ':' + result['account_states'][0]['parsed_seller_nft_prev_owner_address_address'])
        else:
            owner = Address(str(result['account_states'][0]['parsed_nft_owner_address_workchain']) + ':' + result['account_states'][0]['parsed_nft_owner_address_address'])
        return self._process_address(owner.to_string())

    async def get_nft_items(self, nft_addresses: list):
        # in future will be replaced for searchNFTs
        return await asyncio.gather(*[self.get_nft_item(nft_address) for nft_address in nft_addresses])

    async def get_nft_item(self, nft_address: str):
        query = '''
            query get_nft_items ($address: String) {
                transactions (
                    account: {address_friendly: $address}
                    page_size: 1
                )   {
                index: parsed_nft_index
                
                collection_wc: parsed_nft_collection_address_workchain
                collection_hex: parsed_nft_collection_address_address
                
                owner_wc: parsed_nft_owner_address_workchain
                owner_hex: parsed_nft_owner_address_address
                
                is_on_sale: parsed_owner_is_seller
                
                content_url: parsed_nft_content_offchain_url
              }
            }
        '''

        var = {
            'address': self.get_friendly(nft_address),
        }

        data = (await self.send_query(query, var))['transactions'][0]

        result = {
            'address': self._process_address(nft_address),
            'index': int(data['index']),
            'collection_address': self.get_addr_from_wc_hex(data['collection_wc'], data['collection_hex']),

            'owner': self.get_addr_from_wc_hex(data['owner_wc'], data['owner_hex']),
            'collection': {
                'address': self.get_addr_from_wc_hex(data['collection_wc'], data['collection_hex'])
            },
            'metadata': await get(data['content_url'])
        }

        if data['is_on_sale']:
            sale = await self._get_nft_sale(result['owner'])
            result['sale'] = sale

        return NftItem(result, provider=self)

    async def _get_nft_sale(self, owner_address: str):
        query = '''
            query get_sale ($address: String) {
                transactions (
                    account: {address_friendly: $address}
                    page_size: 1
                )   {
                owner_wc: parsed_seller_nft_prev_owner_address_workchain
                owner_hex: parsed_seller_nft_prev_owner_address_address
                
                market_wc: parsed_seller_market_address_workchain
                market_hex: parsed_seller_market_address_address
                
                price: parsed_seller_nft_price
                min_bid: parsed_seller_min_bid
                }
            }
        '''

        var = {
            'address': self.get_friendly(owner_address),
        }

        data = (await self.send_query(query, var))['transactions'][0]

        market_address = self.get_addr_from_wc_hex(data['market_wc'], data['market_hex'])

        market_name = markets_adresses.get(Address(market_address).to_string(False), '')

        real_owner = self.get_addr_from_wc_hex(data['owner_wc'], data['owner_hex'])

        data['price'] = int(data['price'])
        data['min_bid'] = int(data['min_bid'])
        if not data['price']:
            price = data['min_bid']
        else:
            price = data['price']

        return {
            'address': self._process_address(owner_address),
            'market': {
                'address': self.get_addr_from_wc_hex(data['market_wc'], data['market_hex']),
                'name': market_name
            },
            'owner': real_owner,
            'price': {
                'token_name': 'TON',
                'value': price,
            }
        }

    async def get_collection(self, collection_address: str):
        query = '''
            query get_collection ($address: String) {
                transactions (
                    account: {address_friendly: $address}
                    page_size: 1
                )   {
                    next_item_index: parsed_collection_items_count
                    content_url: parsed_collection_content_offchain_url
                    owner_wc: parsed_collection_owner_address_workchain
                    owner_hex: parsed_collection_owner_address_address
                    # parsed_collection_content_onchain_value - currently onchain metadata for NFTs is not supported 
              }
            }
        '''

        var = {
            'address': self.get_friendly(collection_address),
        }

        data = (await self.send_query(query, var))['transactions'][0]

        collection_metadata = await get(data['content_url'])

        owner_address = self.get_addr_from_wc_hex(data['owner_wc'], data['owner_hex'])

        result = {
            'address': self._process_address(collection_address),
            'next_item_index': int(data['next_item_index']),
            'metadata': collection_metadata,
            'owner': owner_address
        }

        return NftCollection(result, self)

    async def get_collection_items(self, collection: NftCollection, limit_per_one_request: int = 0):
        if not collection.is_full():
            await collection.update()
        rps = int(limit_per_one_request / 150)

        query = '''
            query get_collection_items($address_hex: String, $address_wc: Int, $page: Int) {
                account_states(
                    parsed_nft_collection_address_workchain: $address_wc
                    parsed_nft_collection_address_address: $address_hex
                    parsed_nft_true_nft_in_collection: 1
                    page_size: 150
                    page: $page
                    order_by: "parsed_nft_index"
              ) {
                address
              }
            }
        '''

        requests_amount = ceil(collection.next_item_index / 150)

        tasks = []
        for i in range(requests_amount + 1):
            var = {
                "address_wc": Address(collection.address).wc,
                "address_hex": Address(collection.address).hash_part.hex().upper(),
                "page": i
            }
            tasks.append(self.send_query(query, var))
        items = []
        if not rps:
            for i in [i['account_states'] for i in await asyncio.gather(*tasks)]:
                items += i
        else:
            items = []
            for i in range(0, requests_amount + 1, rps):
                for j in [p['account_states'] for p in await asyncio.gather(*tasks[i:i + rps])]:
                    items += j
                await asyncio.sleep(1)
        result = []
        for item in items:
            result.append(NftItem(self._process_address(self.get_addr_from_wc_hex(Address(collection.address).wc, item['address'])), self))
        return result

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 150):
        query = '''
            query get_transactions ($address: String, $limit: Int, $page: Int) {
                transactions (
                    address_friendly: $address
                    page_size: $limit
                    page: $page
                )   {
                    # general info
        
                    utime: gen_utime
                    fee: total_fees_grams
                    hash
                    lt
                    compute_ph_success
                    action_ph_success
                    
                    # in msg
                    
                    in_msg_created_lt
                    # sourse
                    in_src_wc: in_msg_src_addr_workchain_id
                    in_src_hex: in_msg_src_addr_address_hex
                    # destination
                    in_dest_wc: in_msg_dest_addr_workchain_id
                    in_dest_hex: in_msg_dest_addr_address_hex
                    # value
                    in_msg_value_grams
                    # msg_data
                    in_msg_body
                    # op code
                    in_msg_op_code
                    
                    
                    # out msgs
                    outmsg_cnt
                    # lt
                    out_msg_created_lt
                    # sourse - skip
                    # destination
                    out_dest_wc: out_msg_dest_addr_workchain_id
                    out_dest_hex: out_msg_dest_addr_address_hex
                    # value
                    out_msg_value_grams
                    # msg_data
                    out_msg_body
                    # op code
                    out_msg_op_code
                }
            }
        '''

        i = 0

        var = {
            'address': self.get_friendly(address),
            'limit': limit_per_one_request,
            'page': i
        }

        temp = (await self.send_query(query, var))['transactions']
        transactions = temp
        while len(temp) != 0 and len(transactions) < limit:
            i += 1
            var = {
                'address': self.get_friendly(address),
                'limit': limit_per_one_request,
                'page': i
            }

            temp = (await self.send_query(query, var))['transactions']
            transactions += temp

        result = []
        for tr in transactions:
            # dton cuts first 32 bits in msg body if there is an op code,
            # so we create new cell with them in the beginning

            if tr['in_msg_op_code'] is not None and tr['in_msg_body']:
                if 1023 - len(Cell.one_from_boc(b64str_to_bytes(tr['in_msg_body'])).begin_parse()) >= 32:
                    cell = Cell()
                    cell.bits.write_uint(int(tr['in_msg_op_code']), 32)
                    cell.write_cell(Cell.one_from_boc(b64str_to_bytes(tr['in_msg_body'])))
                    tr['in_msg_body'] = bytes_to_b64str(cell.to_boc())
            for i in range(tr['outmsg_cnt']):
                if tr['out_msg_op_code'][i] is not None and tr['out_msg_body'][i]:
                    if 1023 - len(Cell.one_from_boc(b64str_to_bytes(tr['out_msg_body'][i])).begin_parse()) >= 32:
                        cell = Cell()
                        cell.bits.write_uint(int(tr['out_msg_op_code'][i]), 32)
                        cell.write_cell(Cell.one_from_boc(b64str_to_bytes(tr['out_msg_body'][i])))
                        tr['out_msg_body'][i] = bytes_to_b64str(cell.to_boc())

            temp = {
                'utime': int(datetime.fromisoformat(tr['utime'] + '+03:00').timestamp()),
                'fee': tr['fee'],
                'data': None,
                'hash': base64.b64encode(s=bytearray.fromhex(tr['hash'])).decode(),
                'lt': int(tr['lt']),
                'status': tr['compute_ph_success'] and tr['action_ph_success'],
                'in_msg': {
                    'created_lt': tr['in_msg_created_lt'],
                    'source': self.get_addr_from_wc_hex(tr['in_src_wc'], tr['in_src_hex']) if tr['in_src_wc'] is not None else '',
                    'destination': self.get_addr_from_wc_hex(tr['in_dest_wc'], tr['in_dest_hex']) if tr['in_dest_wc'] is not None else '',
                    'value': tr['in_msg_value_grams'],
                    'msg_data': tr['in_msg_body'],
                    'op_code': hex(int(tr['in_msg_op_code'])).replace('0x', '') if tr['in_msg_op_code'] is not None else ''
                },
                'out_msgs': [
                    {
                        'created_lt': tr['out_msg_created_lt'][i],
                        'source': self._process_address(address),
                        'destination': self.get_addr_from_wc_hex(tr['out_dest_wc'][i], tr['out_dest_hex'][i]) if tr['out_dest_wc'][i] is not None else '',
                        'value': tr['out_msg_value_grams'][i],
                        'msg_data': tr['out_msg_body'][i],
                        'op_code': hex(int(tr['out_msg_op_code'][i])).replace('0x', '') if tr['out_msg_op_code'][i] is not None else ''
                    }
                    for i in range(tr['outmsg_cnt'])
                ]
            }
            result.append(Transaction(temp))
        return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        query = '''
            query get_jetton ($address: String) {
                transactions (
                    account: {address_friendly: $address}
                    page_size: 1
                )   {
                    # supply
                    supply: parsed_jetton_total_supply
                    
                    # offchain
                    
                    # url
                    offchain_url: parsed_jetton_content_offchain_url
                    
                    # onchain
                    
                    # name
                    name: parsed_jetton_content_name_value
                    # description
                    description: parsed_jetton_content_description_value
                    # image
                    image: parsed_jetton_content_image_value
                    image_data: parsed_jetton_content_image_data_value
                
                    # symbol
                    symbol: parsed_jetton_content_symbol_value
                    # decimals
                    decimals: parsed_jetton_content_decimals_value
                }
            }
        '''

        var = {
            'address': self.get_friendly(jetton_master_address),
        }

        data = (await self.send_query(query, var))['transactions'][0]

        if data['offchain_url'] is not None:
            result = await get(data['offchain_url'])
        else:
            result = {
                'name': data['name'],
                'description': data['description'],
                'image': data['image'],
                'image_data': data['image_data'],
                'symbol': data['symbol'],
                'decimals': int(data['decimals'])
            }
        result['address'] = self._process_address(jetton_master_address)
        result['supply'] = int(data['supply'])

        return Jetton(result, self)

    async def send_boc(self, boc):
        raise DtonError('currently you can\'t send boc via dton.io :( use other provider')

    async def get_wallet_seqno(self, address: str):
        data = await self.run_get_method(address=address, method='seqno', stack=[])
        return int(data[0]['value'])

    async def get_balance(self, address: str):
        query = '''
            query balance ($address: String) {
                transactions (
                    address_friendly: $address
                    page_size: 1
                )   {
                    balance: account_storage_balance_grams
                }
            }
        '''

        var = {
            "address": self.get_friendly(address)
        }

        data = (await self.send_query(query, var))['transactions'][0]

        return data['balance']

    async def get_state(self, address: str):
        query = '''
            query balance ($address: String) {
                transactions (
                    address_friendly: $address
                    page_size: 1
                )   {
                    state: account_state_type
                }
            }
        '''

        var = {
            "address": self.get_friendly(address)
        }

        data = (await self.send_query(query, var))['transactions'][0]

        return data['state']

    async def get_jetton_wallet_address(self, jetton_master_address: str, owner_address: str):
        query = '''
                    query get_jetton_wallet_address ($minter: String, $user: String) {
                        getJettonWalletAddress (
                            minter_address: $minter
                            user_address: $user
                        ) 
                    }
                '''
        var = {
            "minter": self.get_friendly(jetton_master_address),
            "user": self.get_friendly(owner_address)
        }

        return self._process_address((await self.send_query(query, var))['getJettonWalletAddress'])

    async def get_jetton_wallet(self, jetton_wallet_address: str):
        query = '''
            query get_jetton_wallet($address_hex: String, $address_wc: Int) {
                account_states(address: $address_hex, workchain: $address_wc) {
                    balance: parsed_jetton_wallet_balance
                    
                    owner_wc: parsed_jetton_wallet_owner_address_workchain
                    owner_hex: parsed_jetton_wallet_owner_address_address
                    
                    master_wc: parsed_jetton_wallet_jetton_address_workchain
                    master_hex: parsed_jetton_wallet_jetton_address_address
                    
                    
                    jetton_wallet_code: account_state_state_init_code
                }
            }
        '''

        var = {
            "address_wc": Address(jetton_wallet_address).wc,
            "address_hex": Address(jetton_wallet_address).hash_part.hex().upper(),
        }

        data = (await self.send_query(query, var))['account_states'][0]

        wallet = {
            'address': self._process_address(jetton_wallet_address),
            'balance': int(data['balance']),
            'owner': self.get_addr_from_wc_hex(data['owner_wc'], data['owner_hex']),
            'jetton_master_address': self.get_addr_from_wc_hex(data['master_wc'], data['master_hex']),
            'jetton_wallet_code': data['jetton_wallet_code'],
        }
        return JettonWallet(wallet, self)
