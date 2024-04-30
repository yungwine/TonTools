import json

from TonTools.Contracts.Contract import Contract


class NftCollectionError(BaseException):
    pass


class NftItemSaleError(BaseException):
    pass


class NftItemError(BaseException):
    pass


class NftItem(Contract):
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
            self.collection = NftCollection(data['collection'], self.provider)
            self.collection_address = data['collection_address']
            self.index = data['index']
            self.metadata = data['metadata']
            self.owner = data['owner']
            if 'sale' in data:
                self.sale = NftItemSale(data['sale'], self.provider)
            else:
                self.sale = None

    def is_full(self):
        return self.full_data

    async def update(self):
        self.full_data = True
        item = await self.provider.get_nft_items([self.address])
        item = item[0]
        self.address = item.address
        self.collection = item.collection
        self.collection_address = item.collection_address
        self.index = item.index
        self.metadata = item.metadata
        self.owner = item.owner
        self.sale = item.sale

    async def get_owner(self):
        owner = await self.provider.get_nft_owner(self.address)
        return owner

    def to_dict(self):
        if self.is_full():
            result = {
                'address': self.address,
                'collection': self.collection.to_dict(),
                'collection_address': self.collection_address,
                'index': int(self.index),
                'metadata': self.metadata,
                'owner': self.owner,
            }
            if self.sale:
                result['sale'] = self.sale.to_dict()
            return result
        else:
            return {
                'address': self.address
            }

    def __str__(self):
        return 'NftItem(' + json.dumps(self.to_dict()) + ')'


class NftCollection(Contract):
    def __init__(self, data, provider):
        self.provider = provider
        if isinstance(data, str):
            super().__init__(data, provider)
            self.address = data
            self.full_data = False
        elif isinstance(data, dict):
            if 'owner' in data and 'metadata' in data and 'next_item_index' in data:
                super().__init__(data['address'], provider)
                self.full_data = True
                self.address = data['address']
                self.next_item_index = data['next_item_index']
                self.metadata = data['metadata']
                self.owner = data['owner']
            else:
                super().__init__(data['address'], provider)
                self.full_data = False

    def is_full(self):
        return self.full_data

    async def update(self):
        self.full_data = True
        collection = await self.provider.get_collection(self.address)
        self.address = collection.address
        self.next_item_index = collection.next_item_index
        self.metadata = collection.metadata
        self.owner = collection.owner

    async def get_collection_items(self, limit_per_one_request=0):
        return await self.provider.get_collection_items(self, limit_per_one_request)

    def to_dict(self):
        if self.is_full():
            return {
                'address': self.address,
                'owner': self.owner,
                'next_item_index': self.next_item_index,
                'metadata': self.metadata,
            }
        else:
            return {
                'address': self.address
            }

    def __str__(self):
        return 'NftCollection(' + json.dumps(self.to_dict()) + ')'


class NftItemSale(Contract):
    def __init__(self, data, provider):
        self.provider = provider
        if isinstance(data, str):
            super().__init__(data, provider)
            self.full_data = False
            self.address = data
        elif isinstance(data, dict):
            self.full_data = True
            self.address = data['address']
            super().__init__(data['address'], provider)
            self.market = Market(data['market'])
            self.owner = data['owner']
            self.price_value = data['price']['value']
            self.price_token = data['price']['token_name']

    def is_full(self):
        return self.full_data

    def to_dict(self):
        if self.is_full():
            return {
                'address': self.address,
                'market': self.market.to_dict(),
                'owner': self.owner,
                'price': {
                    'value': self.price_value,
                    'token_name': self.price_token
                }
            }
        else:
            return {
                'address': self.address
            }

    def __str__(self):
        return 'NftItemSale(' + json.dumps(self.to_dict()) + ')'


class Market:
    def __init__(self, data: dict):
        self.address = data['address']
        self.name = data.get('name', None)

    def to_dict(self):
        return {
            'address': self.address,
            'name': self.name
        }

    def __str__(self):
        return 'Market(' + json.dumps(self.to_dict()) + ')'
