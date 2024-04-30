import logging
import typing
import inspect
import random
from pathlib import Path

import requests

from .DtonClient import DtonClient
from .LsClient import LsClient
from .TonApiClient import TonApiClient
from .TonCenterClient import TonCenterClient
from ..Contracts.NFT import NftCollection
from ..Enums.Address import AddressForm


class SafeLsClient:
    ls_client: LsClient

    def __init__(self,
                 fallback_client: typing.Union[DtonClient, TonApiClient, TonCenterClient],
                 ls_index: int = None,  # None for random
                 cdll_path: typing.Union[str, Path] = None,
                 config: typing.Union[str, dict] = 'https://ton.org/global-config.json',
                 keystore: typing.Union[str, Path] = None,
                 workchain_id: int = 0,
                 verbosity_level=0,
                 default_timeout=10,
                 addresses_form: str = AddressForm.USER_FRIENDLY,
                 ):
        self.fallback = fallback_client
        self.ls_index = ls_index
        self.cdll_path = cdll_path
        self.config = config
        self.keystore = keystore
        self.workchain_id = workchain_id
        self.verbosity_level = verbosity_level
        self.default_timeout = default_timeout
        self.addresses_form = addresses_form
        self._next_ls = False

    async def init(self):
        if isinstance(self.config, str):
            # noinspection HttpUrlsUsage
            if self.config.find('http://') == 0 or self.config.find('https://') == 0:
                self.config = requests.get(self.config).json()
        self.ls_index = random.randrange(0, len(self.config['liteservers'])) if self.ls_index is None else self.ls_index

        self.ls_client = LsClient(self.ls_index, self.cdll_path, self.config, self.keystore, self.workchain_id,
                                  self.verbosity_level, self.default_timeout, self.addresses_form)
        await self.ls_client.init()

    async def next_ls(self):
        self.ls_index = (self.ls_index + 1) % len(self.config['liteservers'])
        self.ls_client.ls_index = self.ls_index
        await self.ls_client.init()

    async def _run_method(self, client, method, args, kwargs):
        method = getattr(client, method)
        params = inspect.signature(method).parameters
        args = args[:len(params)]
        kwargs = {k: v for k, v in kwargs.items() if k in params}
        return await method(*args, **kwargs)

    async def _execute(self, _method: str, *args, **kwargs):
        try:
            if self._next_ls:
                self._next_ls = False
                await self.next_ls()
            return await self._run_method(self.ls_client, _method, args, kwargs)
        except Exception as e:
            logging.warning(f'Error in {_method}: {e}\nTrying the fallback client and switching to another LS for the next request')
            self._next_ls = True
            return await self._run_method(self.fallback, _method, args, kwargs)

    def _process_address(self, address):
        return self.ls_client._process_address(address)

    async def run_get_method(self, method: str, address: str, stack: list):
        return await self._execute(self.run_get_method.__name__, method=method, address=address, stack=stack)

    async def get_nft_owner(self, nft_address: str):
        return await self._execute(self.get_nft_owner.__name__, nft_address)

    async def get_nft_items(self, nft_addresses: list):
        return await self._execute(self.get_nft_items.__name__, nft_addresses)

    async def get_collection(self, collection_address):
        return await self._execute(self.get_collection.__name__, collection_address)

    async def get_collection_items(self, collection: NftCollection, limit_per_one_request=0):
        return await self._execute(self.get_collection_items.__name__, collection, limit_per_one_request)

    async def get_transactions(self, address: str, limit: int = 10**9, limit_per_one_request: int = 100):
        return await self._execute(self.get_transactions.__name__, address, limit, limit_per_one_request)

    async def get_jetton_data(self, jetton_master_address: str):
        return await self._execute(self.get_jetton_data.__name__, jetton_master_address)

    async def send_boc(self, boc):
        return await self._execute(self.send_boc.__name__, boc)

    async def get_wallet_seqno(self, address: str):
        return await self._execute(self.get_wallet_seqno.__name__, address)

    async def get_balance(self, address: str):
        return await self._execute(self.get_balance.__name__, address)

    async def get_state(self, address: str):
        return await self._execute(self.get_state.__name__, address)

    async def get_jetton_wallet_address(self, jetton_master_address: str, owner_address: str):
        return await self._execute(self.get_jetton_wallet_address.__name__, jetton_master_address, owner_address)

    async def get_jetton_wallet(self, jetton_wallet_address: str):
        return await self._execute(self.get_jetton_wallet.__name__, jetton_wallet_address)
