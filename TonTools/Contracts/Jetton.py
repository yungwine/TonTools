import json

from .Contract import Contract


class JettonError(BaseException):
    pass


class Jetton(Contract):
    def __init__(self, data, provider):
        self.provider = provider
        if isinstance(data, str):
            super().__init__(data, provider)
            self.address = data
            self.full_data = False
        elif isinstance(data, dict):
            self.full_data = True
            self.supply = int(data['supply'])
            self.address = data['address']
            super().__init__(data['address'], provider)
            self.decimals = int(data.get('decimals', 9))
            self.symbol = data['symbol']
            self.name = data['name']
            self.description = data['description']
            self.image = data['image'] if 'image' in data else data.get('image_data')
            self.token_supply = self.supply / 10 ** self.decimals

    def is_full(self):
        return self.full_data

    async def update(self):
        self.full_data = True
        jetton = await self.provider.get_jetton_data(self.address)
        self.supply = jetton.supply
        self.address = jetton.address
        self.decimals = jetton.decimals
        self.symbol = jetton.symbol
        self.name = jetton.name
        self.description = jetton.description
        self.image = jetton.image
        self.token_supply = jetton.token_supply

    async def get_jetton_wallet(self, owner_address: str):  # TonCenterClient or LsClient required
        jetton_wallet_address = await self.provider.get_jetton_wallet_address(self.address, owner_address)
        return JettonWallet(jetton_wallet_address, self.provider)

    def to_dict(self):
        if self.is_full():
            return {
                'supply': self.supply,
                'address': self.address,
                'decimals': self.decimals,
                'symbol': self.symbol,
                'name': self.name,
                'description': self.description,
                'image': self.image,
                'token_supply': self.token_supply
            }
        else:
            return {
                'address': self.address
            }

    def __str__(self):
        return 'Jetton(' + json.dumps(self.to_dict()) + ')'


class JettonWalletError(BaseException):
    pass


class JettonWallet(Contract):
    def __init__(self, data, provider):
        self.provider = provider
        if isinstance(data, str):
            super().__init__(data, provider)
            self.address = data
            self.full_data = False
        elif isinstance(data, dict):
            self.full_data = True
            self.address = data['address']
            super().__init__(data['address'], provider)
            self.jetton_master_address = data['jetton_master_address']
            self.jetton_master_wallet = Jetton(self.jetton_master_address, self.provider)
            self.balance = data['balance']
            self.jetton_wallet_code = data.get('jetton_wallet_code')
            self.owner = data['owner']

    def is_full(self):
        return self.full_data

    async def update(self):
        self.full_data = True
        wallet = await self.provider.get_jetton_wallet(self.address)
        self.address = wallet.address
        self.jetton_master_address = wallet.jetton_master_address
        self.jetton_wallet_code = wallet.jetton_wallet_code
        self.owner = wallet.owner
        self.balance = wallet.balance

    def to_dict(self):
        if self.is_full():
            return {
                'address': self.address,
                'balance': self.balance,  # in nano
                'owner': self.owner,
                'jetton_master_address': self.jetton_master_address,
            }
        else:
            return {
                'address': self.address,
            }

    def __str__(self):
        return 'JettonWallet(' + json.dumps(self.to_dict()) + ')'
