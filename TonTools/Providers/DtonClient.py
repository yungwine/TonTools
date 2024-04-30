import asyncio
from datetime import datetime
import base64
import aiohttp
import requests
from graphql_query import Argument, Field, Operation, Query

from tonsdk.utils import Address

from .utils import get, markets_adresses, is_hex
from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Jetton import Jetton, JettonWallet
from ..Enums.Address import AddressForm


class DtonError(BaseException):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except Exception:
        raise DtonError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise DtonError(f'dton failed with error: {response_dict}')
    else:
        return response_dict


class DtonClient:
    def __init__(self,
                 key: str = None,  # dton api key
                 addresses_form: str = AddressForm.USER_FRIENDLY,
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
        if self.form == AddressForm.RAW:
            return Address(address).to_string(is_user_friendly=False)
        elif self.form == AddressForm.USER_FRIENDLY:
            if self.testnet:
                return Address(address).to_string(True, True, True, True)
            else:
                return Address(address).to_string(True, True, True)

    @staticmethod
    def get_friendly(address: str):
        return Address(address).to_string(True, True, True)

    def get_addr_from_wc_hex(self, wc: int, hex_: str):
        return self._process_address(
            Address(str(wc) + ':' + hex_).to_string()
        )

    async def send_query(self, graphql_query: str, variables=None):
        if variables is None:
            variables = {}
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            response = await session.post(url=self.base_url, json={'query': graphql_query, 'variables': variables})
            response = await process_response(response)
            return response['data']

    """
    low level part
    """

    def process_fields(self, fields: list):
        result = []
        for field in fields:
            if isinstance(field, str):
                result.append(field)
            if isinstance(field, dict):
                # dicts they should contain exactly one key, e.g:
                # ["updated_at", {'data': ["nft_index", "sale_type", {"seller": ["nft_price"]}]}]
                temp = self.process_fields(list(field.values())[0])
                result.append(
                    Field(
                        name=list(field.keys())[0],
                        fields=temp
                    )
                )
        return result

    def process_args(self, args: dict):
        result = []
        for k, v in args.items():
            if isinstance(v, str):
                v = f'"{v}"'
            if isinstance(v, bool):
                v = 'true' if v else 'false'
            if isinstance(v, list):
                temp = []
                for i in v:
                    temp.append(self.process_args(i))
                v = temp
            if isinstance(v, dict):
                v = self.process_args(v)
            result.append(Argument(name=k, value=v))
        return result

    async def raw_send_query(self, table_name: str, fields: list, type='query', **kwargs):
        result_args = self.process_args(kwargs)
        result_fields = self.process_fields(fields)

        sub_query = Query(
            name=table_name,
            arguments=result_args,
            fields=result_fields
        )

        query = Operation(
            type=type,
            queries=[sub_query]
        ).render()

        result = await self.send_query(query)
        return result[table_name]

    async def page_generator(self, table_name: str, fields: list, **kwargs):
        kwargs['page'] = 0
        while True:
            yield self.raw_send_query(table_name, fields, **kwargs)
            kwargs['page'] += 1

    async def query_with_pagination(self, table_name: str, fields: list, **kwargs):
        if 'limit' not in kwargs:
            kwargs['limit'] = -1
        if 'page_size' not in kwargs:
            kwargs['page_size'] = 150
        limit = kwargs.pop('limit')
        if 'page' not in kwargs:
            result = []
            async for i in self.page_generator(table_name, fields, **kwargs):
                resp = await i
                if isinstance(resp, dict) and 'data' in resp:
                    resp = resp['data']
                result += resp
                if len(result) >= limit != -1:
                    return result[:limit]
                if len(resp) < kwargs['page_size']:
                    return result
        else:
            result = await self.raw_send_query(table_name, fields, **kwargs)
            if limit == -1:
                return result
            else:
                return result[:limit]

    async def raw_get_transactions(self, fields: list, **kwargs):
        if 'address' in kwargs and not is_hex(kwargs['address']):
            # you can specify address kwarg both in hashpart-hex and user-friendly form
            kwargs['address_friendly'] = kwargs['address']
            kwargs.pop('address')
        return await self.query_with_pagination('transactions', fields, **kwargs)

    async def raw_get_account_states(self, fields: list, **kwargs):
        if 'address' in kwargs and not is_hex(kwargs['address']):
            # you can specify address kwarg both in hashpart-hex and user-friendly form
            hashpart, wc = Address(kwargs['address']).hash_part.hex().upper(), Address(kwargs['address']).wc
            kwargs['address'] = hashpart
            kwargs['workchain'] = wc
        if 'order_by' not in kwargs:
            kwargs['order_by'] = 'gen_utime'  # it's better to specify order_by for your purposes
        return await self.query_with_pagination('account_states', fields, **kwargs)

    async def raw_get_last_transaction_count_segments(self, fields: list, **kwargs):
        return await self.query_with_pagination('lastTransactionCountSegments', fields, **kwargs)

    async def raw_get_blocks(self, fields: list, **kwargs):
        return await self.query_with_pagination('blocks', fields, **kwargs)

    async def search_nfts(self, fields: list, **kwargs):
        return await self.query_with_pagination('searchNFTs', fields, **kwargs)

    async def search_nft_collections(self, fields: list, **kwargs):
        return await self.query_with_pagination('searchNFTCollections', fields, **kwargs)

    async def raw_run_method(self, fields: list, **kwargs):
        return await self.raw_send_query('run_method', fields, 'mutation', **kwargs)

    async def run_get_method(self, address: str, method: str, stack: list):
        data = await self.raw_run_method(
            fields=['exit_code', 'gas_used', 'vm_steps', 'success', {'stack': ['value_type', 'value']}],
            account_search_by_address={'address_friendly': self.get_friendly(address)}, method_name=method, stack=stack
        )

        if not data['success']:
            raise DtonError(
                f'get method {method} for address {self._process_address(address)} exit code is {data["exit_code"]}')

        return data['stack']

    async def get_nft_items(self, nft_addresses: list):
        # in future will be replaced for searchNFTs
        return await asyncio.gather(*[self.get_nft_item(nft_address) for nft_address in nft_addresses])

    async def get_nft_item(self, nft_address: str):
        data = (await self.raw_get_transactions(["parsed_nft_index",
                                                 'parsed_nft_collection_address_workchain',
                                                 'parsed_nft_collection_address_address',
                                                 'parsed_nft_owner_address_workchain',
                                                 'parsed_nft_owner_address_address',
                                                 'parsed_owner_is_seller',
                                                 'parsed_nft_content_offchain_url'],
                                                account={'address_friendly': self.get_friendly(nft_address)}, limit=1))[0]

        col_addr = self.get_addr_from_wc_hex(data['parsed_nft_collection_address_workchain'], data['parsed_nft_collection_address_address'])
        result = {
            'address': self._process_address(nft_address),
            'index': int(data['parsed_nft_index']),
            'collection_address': col_addr,
            'owner': self.get_addr_from_wc_hex(data['parsed_nft_owner_address_workchain'], data['parsed_nft_owner_address_address']),
            'collection': {
                'address': col_addr
            },
            'metadata': await get(data['parsed_nft_content_offchain_url']) if data['parsed_nft_content_offchain_url'] else {}
        }

        if data['parsed_owner_is_seller']:
            sale = await self._get_nft_sale(result['owner'])
            result['sale'] = sale

        return NftItem(result, provider=self)

    async def _get_nft_sale(self, owner_address: str):

        data = (await self.raw_get_transactions(["parsed_seller_nft_prev_owner_address_workchain",
                                                 "parsed_seller_nft_prev_owner_address_address",
                                                 "parsed_seller_market_address_workchain",
                                                 "parsed_seller_market_address_address",
                                                 "parsed_seller_nft_price",
                                                 "parsed_seller_min_bid"],
                                                account={'address_friendly': self.get_friendly(owner_address)}, limit=1))[0]

        market_address = self.get_addr_from_wc_hex(data['parsed_seller_market_address_workchain'], data['parsed_seller_market_address_address'])

        market_name = markets_adresses.get(Address(market_address).to_string(False), '')

        real_owner = self.get_addr_from_wc_hex(data['parsed_seller_nft_prev_owner_address_workchain'], data['parsed_seller_nft_prev_owner_address_address'])

        data['price'] = int(data['parsed_seller_nft_price'])
        data['min_bid'] = int(data['parsed_seller_min_bid'])
        if not data['price']:
            price = data['min_bid']
        else:
            price = data['price']

        return {
            'address': self._process_address(owner_address),
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

    async def get_collection(self, collection_address: str):
        data = (await self.raw_get_transactions(["parsed_collection_items_count",
                                                 "parsed_collection_content_offchain_url",
                                                 "parsed_collection_owner_address_workchain",
                                                 "parsed_collection_owner_address_address"],
                                                account={'address_friendly': self.get_friendly(collection_address)}, limit=1))[0]

        collection_metadata = await get(data['parsed_collection_content_offchain_url']) if data['parsed_collection_content_offchain_url'] else {}

        owner_address = self.get_addr_from_wc_hex(data['parsed_collection_owner_address_workchain'], data['parsed_collection_owner_address_address'])

        result = {
            'address': self._process_address(collection_address),
            'next_item_index': int(data['parsed_collection_items_count']),
            'metadata': collection_metadata,
            'owner': owner_address
        }

        return NftCollection(result, self)

    async def get_collection_items(self, collection: NftCollection):
        if not collection.is_full():
            await collection.update()

        data = await self.raw_get_account_states(
            ['address', 'workchain'], parsed_nft_collection_address_workchain=Address(collection.address).wc,
            parsed_nft_collection_address_address=Address(collection.address).hash_part.hex().upper(),
            parsed_nft_true_nft_in_collection=1, order_by="parsed_nft_index"
        )
        result = []
        for item in data:
            result.append(NftItem(self._process_address(self.get_addr_from_wc_hex(item['workchain'], item['address'])), self))
        return result

    async def get_transactions(self, address: str, limit: int = -1):
        transactions = await self.raw_get_transactions(
            fields=[
                'gen_utime', 'total_fees_grams', 'hash', 'lt', 'compute_ph_success',
                'action_ph_success', 'in_msg_created_lt', 'in_msg_src_addr_workchain_id',
                'in_msg_src_addr_address_hex', 'in_msg_dest_addr_workchain_id', 'in_msg_dest_addr_address_hex',
                'in_msg_value_grams', 'in_msg_body', 'in_msg_op_code', 'outmsg_cnt', 'out_msg_created_lt', 'out_msg_dest_addr_workchain_id',
                'out_msg_dest_addr_address_hex', 'out_msg_value_grams', 'out_msg_body', 'out_msg_op_code'
            ], account={'address_friendly': self.get_friendly(address)}
        )
        result = []
        for tr in transactions:
            temp = {
                'utime': int(datetime.fromisoformat(tr['gen_utime'] + '+03:00').timestamp()),
                'fee': tr['total_fees_grams'],
                'data': None,
                'hash': base64.b64encode(s=bytearray.fromhex(tr['hash'])).decode(),
                'lt': int(tr['lt']),
                'status': tr['compute_ph_success'] and tr['action_ph_success'],
                'in_msg': {
                    'created_lt': tr['in_msg_created_lt'],
                    'source': self.get_addr_from_wc_hex(tr['in_msg_src_addr_workchain_id'], tr['in_msg_src_addr_address_hex']) if tr[
                                                                                                  'in_msg_src_addr_workchain_id'] is not None else '',
                    'destination': self.get_addr_from_wc_hex(tr['in_msg_dest_addr_workchain_id'], tr['in_msg_dest_addr_address_hex']) if tr['in_msg_dest_addr_workchain_id'] is not None else '',
                    'value': tr['in_msg_value_grams'],
                    'msg_data': tr['in_msg_body'],
                    'op_code': hex(int(tr['in_msg_op_code'])).replace('0x', '') if tr['in_msg_op_code'] is not None else ''
                },
                'out_msgs': [
                    {
                        'created_lt': tr['out_msg_created_lt'][i],
                        'source': self._process_address(address),
                        'destination': self.get_addr_from_wc_hex(tr['out_msg_dest_addr_workchain_id'][i], tr['out_msg_dest_addr_address_hex'][i]) if
                        tr['out_msg_dest_addr_workchain_id'][i] is not None else '',
                        'value': tr['out_msg_value_grams'][i],
                        'msg_data': tr['out_msg_body'][i],
                        'op_code': hex(int(tr['out_msg_op_code'][i])).replace('0x', '') if tr['out_msg_op_code'][i] is not None else ''
                    }
                    for i in range(tr['outmsg_cnt'])
                ]
            }
            result.append(Transaction(temp))
        if limit == -1:
            return result
        return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        data = (await self.raw_get_transactions(
            fields=[
                'parsed_jetton_total_supply', 'parsed_jetton_content_offchain_url',
                'parsed_jetton_content_name_value', 'parsed_jetton_content_description_value',
                'parsed_jetton_content_image_value', 'parsed_jetton_content_image_data_value',
                'parsed_jetton_content_symbol_value', 'parsed_jetton_content_decimals_value',
            ], account={'address_friendly': self.get_friendly(jetton_master_address)}, limit=1
        ))[0]

        if data['parsed_jetton_content_offchain_url'] is not None:
            result = await get(data['parsed_jetton_content_offchain_url'])
        else:
            result = {
                'name': data['parsed_jetton_content_name_value'],
                'description': data['parsed_jetton_content_description_value'],
                'image': data['parsed_jetton_content_image_value'],
                'image_data': data['parsed_jetton_content_image_data_value'],
                'symbol': data['parsed_jetton_content_symbol_value'],
                'decimals': int(data['parsed_jetton_content_decimals_value'])
            }
        result['address'] = self._process_address(jetton_master_address)
        result['supply'] = int(data['parsed_jetton_total_supply'])

        return Jetton(result, self)

    async def send_boc(self, boc):
        raise DtonError('currently you can\'t send boc via dton.io :( use other provider')

    async def get_wallet_seqno(self, address: str):
        data = await self.run_get_method(address=address, method='seqno', stack=[])
        return int(data[0]['value'])

    async def get_balance(self, address: str):
        data = (await self.raw_get_account_states(['account_storage_balance_grams'],
                                                  address=Address(address).hash_part.hex().upper(),
                                                  workchain=Address(address).wc))[0]

        return int(data['account_storage_balance_grams'])

    async def get_state(self, address: str):
        data = (await self.raw_get_account_states(['account_state_type'],
                                                  address=Address(address).hash_part.hex().upper(),
                                                  workchain=Address(address).wc))[0]

        return data['account_state_type']

    async def get_all_jetton_wallets_by_owner(self, owner_address: str):
        data = await self.raw_get_account_states(
            fields=['workchain', 'address', 'parsed_jetton_wallet_balance',
                    'parsed_jetton_wallet_jetton_address_workchain', 'parsed_jetton_wallet_jetton_address_address'],
            parsed_jetton_wallet_owner_address_address=Address(owner_address).hash_part.hex().upper(),
            parsed_jetton_wallet_owner_address_workchain=Address(owner_address).wc
        )
        result = []
        for wallet in data:
            result.append({
                'jetton_master_address': self.get_addr_from_wc_hex(wallet['parsed_jetton_wallet_jetton_address_workchain'], wallet['parsed_jetton_wallet_jetton_address_address']),
                'address': self.get_addr_from_wc_hex(wallet['workchain'], wallet['address']),
                'balance': int(wallet['parsed_jetton_wallet_balance'])
            })
        return result

    async def get_jetton_wallet_address(self, jetton_master_address: str, owner_address: str):

        addr = await self.raw_send_query('getJettonWalletAddress', [], minter_address=jetton_master_address, user_address=owner_address)

        return self._process_address(addr)

    async def get_jetton_wallet(self, jetton_wallet_address: str):
        data = (await self.raw_get_account_states([
                            'parsed_jetton_wallet_balance', 'parsed_jetton_wallet_owner_address_workchain',
                            'parsed_jetton_wallet_owner_address_address', 'parsed_jetton_wallet_jetton_address_workchain',
                            'parsed_jetton_wallet_jetton_address_address', 'account_state_state_init_code'],
                            address=Address(jetton_wallet_address).hash_part.hex().upper(),
                            workchain=Address(jetton_wallet_address).wc))[0]

        wallet = {
            'address': self._process_address(jetton_wallet_address),
            'balance': int(data['parsed_jetton_wallet_balance']),
            'owner': self.get_addr_from_wc_hex(data['parsed_jetton_wallet_owner_address_workchain'], data['parsed_jetton_wallet_owner_address_address']),
            'jetton_master_address': self.get_addr_from_wc_hex(data['parsed_jetton_wallet_jetton_address_workchain'], data['parsed_jetton_wallet_jetton_address_address']),
            'jetton_wallet_code': data['account_state_state_init_code'],
        }
        return JettonWallet(wallet, self)
