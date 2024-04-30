import logging
import typing
import asyncio
import random
from math import ceil
from pathlib import Path

import aiohttp
import base64
import requests
from tonsdk.boc import Cell
from ton.utils.cell import read_address
from tonsdk.utils import Address, bytes_to_b64str, b64str_to_bytes
from ton import TonlibClient

from ..Contracts.NFT import NftItem, NftCollection
from ..Contracts.Contract import Transaction
from ..Contracts.Wallet import Wallet
from ..Contracts.Jetton import Jetton, JettonWallet
from ..Enums.Address import AddressForm
from ..Enums.Exception import TVMExitCode
from .utils import markets_adresses, get, process_jetton_data


class LsClientError(BaseException):
    pass


class GetMethodError(LsClientError, TVMExitCode):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except Exception:
        raise LsClientError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise LsClientError(f'TonCenter failed with error: {response_dict["error"]}')
    else:
        return response_dict


class LsClient(TonlibClient):
    def __init__(self, ls_index: int = None,  # None for random
                 cdll_path: typing.Union[str, Path] = None,
                 config: typing.Union[str, dict] = 'https://ton.org/global-config.json',
                 keystore: typing.Union[str, Path] = None,
                 workchain_id: int = 0,
                 verbosity_level=0,
                 default_timeout=10,
                 addresses_form: str = AddressForm.USER_FRIENDLY
                 ):
        if not cdll_path:
            logging.warning('You should provide a path to the tonlibjson library (.dll|.so|.dylib).\n'
                            'It can be downloaded from https://github.com/ton-blockchain/ton/releases.\n'
                            'Embedded binaries may be outdated and unsafe. Use them only for testing purposes.')
        if isinstance(keystore, Path):
            keystore = str(keystore)
        if isinstance(cdll_path, Path):
            cdll_path = str(cdll_path)
        self.cdll_path = cdll_path
        self.form = addresses_form
        super().__init__(ls_index, config, keystore, workchain_id, verbosity_level, default_timeout)
        TonlibClient.enable_unaudited_binaries()

    async def init(self):
        if self.ls_index is None:
            if isinstance(self.config, str):
                # noinspection HttpUrlsUsage
                if self.config.find('http://') == 0 or self.config.find('https://') == 0:
                    self.config: dict = requests.get(self.config).json()
            self.ls_index = random.randrange(0, len(self.config['liteservers']))
        return await super().init_tonlib(self.cdll_path)

    def _process_address(self, address):
        if self.form == AddressForm.USER_FRIENDLY:
            return Address(address).to_string(True, True, True)
        elif self.form == AddressForm.RAW:
            return Address(address).to_string(is_user_friendly=False)

    async def run_get_method(self, method: str, address: str, stack: list):
        account = await self.find_account(address, preload_state=False)
        response = await account.run_get_method(method=method, stack=stack)

        if response.exit_code != 0:
            logging.error(f'Failed to run method {method} on {address}. Exit code: {response.exit_code}')
            raise GetMethodError(response.exit_code)
        return response.stack

    async def get_nft_owner(self, nft_address: str):
        sale = await self._get_nft_sale(nft_address)
        if not sale:
            data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])
            owner_address = read_address(Cell.one_from_boc(base64.b64decode(data[3].cell.bytes))).to_string()
        else:
            owner_address = sale['owner']
        return Wallet(self, self._process_address(owner_address))

    async def get_nft_items(self, nft_addresses: list):
        return await asyncio.gather(*[self._get_nft_item(nft_address) for nft_address in nft_addresses])

    async def _get_nft_item(self, nft_address: str):
        data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])

        result = {
            'address': self._process_address(nft_address),
            'index': int(data[1].number.number),
            'collection_address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2].cell.bytes)))),
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[3].cell.bytes)))),
            'collection': {
                'address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2].cell.bytes))))
            }
        }
        request_stack = [{
                "@type": "tvm.stackEntryNumber",
                "number": {
                    "@type": "tvm.numberDecimal",
                    "number": str(result['index'])
                }
            },
            {
                "@type": "tvm.stackEntryCell",
                "cell": {
                    "@type": "tvm.cell",
                    "bytes": data[4].cell.bytes
                }
            }]
        content_data = await self.run_get_method(method='get_nft_content', address=result['collection_address'], stack=request_stack)
        collection_content_url = Cell.one_from_boc(base64.b64decode(content_data[0].cell.bytes)).bits.get_top_upped_array().decode().split('\x01')[-1]
        nft_content_url = collection_content_url + Cell.one_from_boc(base64.b64decode(content_data[0].cell.bytes)).refs[0].bits.get_top_upped_array().decode()

        result['metadata'] = await get(nft_content_url)

        sale = await self._get_nft_sale(nft_address)
        if not sale:
            return NftItem(result, provider=self)
        else:
            result['sale'] = sale
            return NftItem(result, provider=self)

    async def _get_nft_sale(self, nft_address: str):
        data = await self.run_get_method(method='get_nft_data', address=nft_address, stack=[])
        owner_address = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[3].cell.bytes))).to_string())
        try:
            data = await self.run_get_method(method='get_sale_data', address=owner_address, stack=[])
        except GetMethodError as e:
            logging.info(f'Failed to get sale data for {owner_address}: {e.message}')
            return False
        if len(data) == 10:
            market_address = read_address(Cell.one_from_boc(base64.b64decode(data[3].cell.bytes))).to_string()
            market_name = markets_adresses.get(market_address, '')
            market_address = self._process_address(market_address)
            real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[5].cell.bytes))).to_string())
            price = int(data[6].number.number)
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
            market_address = read_address(Cell.one_from_boc(base64.b64decode(data[0].cell.bytes))).to_string()
            market_name = markets_adresses.get(market_address, '')
            market_address = self._process_address(market_address)
            real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2].cell.bytes))).to_string())
            price = int(data[3].number.number)
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
            market_address = read_address(Cell.one_from_boc(base64.b64decode(data[3].cell.bytes))).to_string()
            market_name = markets_adresses.get(market_address, '')
            market_address = self._process_address(market_address)
            real_owner = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[5].cell.bytes))).to_string())
            price = max(int(data[6].number.number), int(data[16].number.number)) if len(data) >= 16 else int(data[6].number.number)
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

    async def get_collection(self, collection_address):
        data = await self.run_get_method(method='get_collection_data', address=collection_address, stack=[])
        collection_content_url = Cell.one_from_boc(base64.b64decode(data[1].cell.bytes)).bits.get_top_upped_array().decode().split('\x01')[-1]
        # if '\x01' in collection_content_url:
        #     collection_content_url = collection_content_url.split('\x01')[1]
        collection_metadata = await get(collection_content_url)
        result = {
            'address': self._process_address(collection_address),
            'next_item_index': int(data[0].number.number),
            'metadata': collection_metadata,
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2].cell.bytes))))
        }
        return NftCollection(result, self)

    async def get_collection_items(self, collection: NftCollection, limit_per_one_request=0):
        if not collection.is_full():
            await collection.update()
        if not limit_per_one_request:
            items = await asyncio.gather(*[self.run_get_method(address=collection.address, method='get_nft_address_by_index', stack=[{"@type": "tvm.stackEntryNumber", "number": {"@type": "tvm.numberDecimal", "number": str(i)}}]) for i in range(collection.next_item_index)])
        else:
            items = []
            for p in range(ceil(collection.next_item_index / limit_per_one_request)):
                items += await asyncio.gather(*[self.run_get_method(address=collection.address, method='get_nft_address_by_index', stack=[{"@type": "tvm.stackEntryNumber", "number": {"@type": "tvm.numberDecimal", "number": str(i)}}]) for i in range(p * limit_per_one_request, min(collection.next_item_index, limit_per_one_request * (p + 1)))])

        result = []
        for data in items:
            result.append(NftItem(self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[0].cell.bytes)))), self))
        return result

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 100):
        account = await self.find_account(address)
        # ton lib method does all the work of getting the required tx amount in a loop
        transactions = map(lambda x: x.to_json(), await account.get_transactions(limit=limit))
        result = []
        for tr in transactions:
            tr['hash'] = tr['transaction_id']['hash']
            tr['lt'] = tr['transaction_id']['lt']
            tr['in_msg']['source'] = self._process_address(tr['in_msg']['source']['account_address']) if tr['in_msg']['source']['account_address'] else ''
            tr['in_msg']['destination'] = self._process_address(tr['in_msg']['destination']['account_address']) if tr['in_msg']['destination']['account_address'] else ''
            tr['in_msg']['msg_data'] = tr['in_msg']['msg_data']['text'] if 'text' in tr['in_msg']['msg_data'] else tr['in_msg']['msg_data']['body']
            out_msgs = tr['out_msgs']
            for out_msg in out_msgs:
                out_msg['source'] = self._process_address(out_msg['source']['account_address']) if out_msg['source']['account_address'] else ''
                out_msg['destination'] = self._process_address(out_msg['destination']['account_address']) if out_msg['destination']['account_address'] else ''
                out_msg['msg_data'] = out_msg['msg_data']['text'] if 'text' in out_msg['msg_data'] else out_msg['msg_data']['body']
            tr['out_msgs'] = out_msgs
            result.append(Transaction(tr))
        return result[:limit]

    async def get_jetton_data(self, jetton_master_address: str):
        data = await self.run_get_method(method='get_jetton_data', address=jetton_master_address, stack=[])
        processed = process_jetton_data(data[3].cell.bytes)
        result = processed if isinstance(processed, dict) else await get(processed)
        result['address'] = self._process_address(jetton_master_address)
        result['supply'] = int(data[0].number.number)

        return Jetton(result, self)

    async def send_boc(self, boc, **kwargs):
        response = await super().send_boc(b64str_to_bytes(boc))
        return response

    async def get_wallet_seqno(self, address: str):
        data = await self.run_get_method(address=address, method='seqno', stack=[])
        return int(data[0].number.number)

    async def get_balance(self, address: str):
        account = await self.find_account(address)
        balance = await account.get_balance()
        if balance == -1:
            return 0
        return int(balance)

    async def get_state(self, address: str):
        account = await self.find_account(address)
        state = await account.get_state()
        state = state.to_json()
        if state['frozen_hash']:
            return 'frozen'
        if not state['data']:
            return 'uninitialized'
        else:
            return 'active'

    async def get_jetton_wallet_address(self, jetton_master_address: str, owner_address: str):
        cell = Cell()
        cell.bits.write_address(Address(owner_address))
        request_stack = [
            {
                "@type": "tvm.stackEntrySlice",
                "slice": {
                    "@type": "tvm.slice",
                    "bytes": bytes_to_b64str(cell.to_boc(False))
                }
            }]
        data = await self.run_get_method(address=jetton_master_address, method='get_wallet_address', stack=request_stack)
        jetton_wallet_address = self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[0].slice.bytes))).to_string())
        return jetton_wallet_address

    async def get_jetton_wallet(self, jetton_wallet_address: str):
        data = await self.run_get_method(address=jetton_wallet_address, method='get_wallet_data', stack=[])
        wallet = {
            'address': jetton_wallet_address,
            'balance': int(data[0].number.number),
            'owner': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[1].slice.bytes)))),
            'jetton_master_address': self._process_address(read_address(Cell.one_from_boc(base64.b64decode(data[2].slice.bytes)))),
            'jetton_wallet_code': data[3].cell.bytes,
        }
        return JettonWallet(wallet, self)
