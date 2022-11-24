# TonTools

__TonTools__ is a _high-level_ library for Python, which can be used to interacrt with [TON Blockchain](https://ton.org).

[![PyPI version](https://badge.fury.io/py/tontools.svg)](https://badge.fury.io/py/tontools)

## How to install:

```bash
pip install tontools
```

## Basics

__TonTools__ gets data from blockhain using [lite clients](https://ton.org/docs/participate/nodes/node-types) (based on [psylopunk's pytonlib](https://github.com/psylopunk/pytonlib)). So you can use __get_client()__ function which returns a TonLibClient instance

In most functions the _client_ parameter is optional, so you can pass it to function or not. It useful when you would like to work with a specific liteserver,
for e.g. 
```python
from TonTools import get_collection, get_client

client = get_client(ls=2)

get_collection(addr='EQCg2iAv486UTCHN9PCwjpRKrUoFvJDs28bcQGCbtCgQIIFd', client=client)
```

## NFT Functions

```python
from TonTools import *

get_collection('EQCg2iAv486UTCHN9PCwjpRKrUoFvJDs28bcQGCbtCgQIIFd') -> " dict of collection data, e.g. "

{'address': '0:a0da202fe3ce944c21cdf4f0b08e944aad4a05bc90ecdbc6dc40609bb4281020',
  'metadata': {
    'name': 'TON GUYS',
#    .......
    'cover_image': 'https://s.getgems.io/nft/b/c/6369646868bb4790d07bb156/edit/images/63698303c5e149dff20c1dec.png'
  },
  'next_item_index': 13986,
  'owner': {'address': '0:1239440bdcfa24d1fb941ef73f774958e0aed9f559c613f54ba2ddc601e48d55'}
}

get_nft_items_by_owner_address('EQC2QQD8mjxgKEAv-ZeCiOsii21vWR5BZtLO_LQGFB33gJSt')  -> " list of nft items addresses ! shows nft items were bought by user or were transferred to user's wallet ! "

get_collection_items() -> " list of nft items addresses related to collection wallet "

get_nft_owner() -> " returns address of owner's wallet (if nft on sale or auction it returns nft actual owner, not sale smart contract's address) "

get_items() -> " list of dicts with nfts data. e.g. "

get_items(['EQCX3LvmFxVqz52ByQd1bNjnJ_ZutkTVfWty3RGy3LX0-x2P', 'EQDsz_jnLXePSCZCuzjwH2O3q_fk_rDdkKQXbbTPa_lV3ILJ'])

[{'address': '0:97dcbbe617156acf9d81c907756cd8e727f66eb644d57d6b72dd11b2dcb5f4fb', 'collection': {'address': '0:a0da202fe3ce944c21cdf4f0b08e944aad4a05bc90ecdbc6dc40609bb4281020', 'name': 'TON GUYS', 'description': 'Here we are! Cat and Ufo are the characters in the new, next generation, and customizable NFT collection in the TON ecosystem.', 'image': 'https://s.getgems.io/nft/b/c/6369646868bb4790d07bb156/edit/images/6372fccbe9da2522009914c0.jpg'}, 'collection_address': '0:a0da202fe3ce944c21cdf4f0b08e944aad4a05bc90ecdbc6dc40609bb4281020', 'index': 6464, 'content_url': 'https://server.tonguys.org/nfts/items/6464.json', 'metadata': {'name': 'Netting Shirt', 'description': 'Pretty Sexy-Urbanistic-Fashionable T For Self-Confident Person ', 'image': 'https://boxes.tonguys.org/c_shirt4_5.png', 'model_id': '4', 'color_id': '5', 'id': '27724', 'group_id': '2635', 'image_transparent_url': 'https://server.tonguys.org/nfts/items/cat/shirt4_5.png', 'attributes': [{'trait_type': 'Rarity', 'value': 'Silver'}, {'trait_type': 'Color', 'value': 'Green'}, {'trait_type': 'Class', 'value': 'Shirt'}, {'trait_type': 'Type', 'value': 'Item'}]}, 'owner': {'address': '0:ef4c1974ee4acee7471c9957cd26d9f7333f5bef22b6ef808ad960b097b8a9cd'}, 'sale': {'address': '0:ef4c1974ee4acee7471c9957cd26d9f7333f5bef22b6ef808ad960b097b8a9cd', 'market': {'address': '0:584ee61b2dff0837116d0fcb5078d93964bcbe9c05fd6a141b1bfca5d6a43e18', 'name': 'Getgems Sales'}, 'owner': {'address': '0:8eb8c40e537b664d79fc638874916ee63ed63198c4c836766ed5f6c350d209dc'}, 'price': {'value': '12000000000'}}}, {'address': '0:eccff8e72d778f482642bb38f01f63b7abf7e4feb0dd90a4176db4cf6bf955dc', 'collection': {'address': '0:a0da202fe3ce944c21cdf4f0b08e944aad4a05bc90ecdbc6dc40609bb4281020', 'name': 'TON GUYS', 'description': 'Here we are! Cat and Ufo are the characters in the new, next generation, and customizable NFT collection in the TON ecosystem.', 'image': 'https://s.getgems.io/nft/b/c/6369646868bb4790d07bb156/edit/images/6372fccbe9da2522009914c0.jpg'}, 'collection_address': '0:a0da202fe3ce944c21cdf4f0b08e944aad4a05bc90ecdbc6dc40609bb4281020', 'index': 455, 'content_url': 'https://server.tonguys.org/nfts/items/455.json', 'metadata': {'name': 'UFO #5433', 'description': 'There are rumors that he stole Katnipp from Catopolis -- Reminder! All our garments can fit both Ufo and Katnipp', 'image': 'https://server.tonguys.org/nfts/items/ufo/skin_2308.png', 'combined_items_data': {'eye': [13, 1], 'background': [17, 1], 'body': [5, 1], 'skin': [6, 1]}, 'attributes': [{'trait_type': 'Rarity', 'value': 'Epic'}, {'trait_type': 'Class', 'value': 'Ufo'}, {'trait_type': 'Color', 'value': '5'}, {'trait_type': 'Emotion', 'value': 'Disgusting'}, {'trait_type': 'Background', 'value': 'Colored waterfall'}, {'trait_type': 'Type', 'value': 'Body'}], 'image_background_url': 'https://server.tonguys.org/nfts/items/ufo/background17_1.png'}, 'owner': {'address': '0:952683e5388093d280fa90ec0e501c50e191816db61e2ab1e8319044ff34b448'}, 'sale': {'address': '0:952683e5388093d280fa90ec0e501c50e191816db61e2ab1e8319044ff34b448', 'market': {'address': '0:584ee61b2dff0837116d0fcb5078d93964bcbe9c05fd6a141b1bfca5d6a43e18', 'name': 'Getgems Sales'}, 'owner': {'address': '0:77dfd466be635d4e7e2db7064f447775c48f0155a120653b566b4962d46d357b'}, 'price': {'value': '19500000000'}}}]

"btw this function checks if nft is on sale (GG auction)"

```

## Other Functions

```python
get_all_wallet_transactions_raw() -> " list of transactions in raw format "

get_all_wallet_transactions() -> " list of transactions in human-readble format, e.g. "

get_all_wallet_transactions(addr='EQCtiv7PrMJImWiF2L5oJCgPnzp-VML2CAt5cbn1VsKAxLiE', limit=2)
[{'type': 'out', 'from': 'EQCtiv7PrMJImWiF2L5oJCgPnzp-VML2CAt5cbn1VsKAxLiE', 'to': 'EQDdGjo6KNmYy1TKJIgAitzLM-oMDDgDpngljPhzo1w3-0DB', 'value': 88445575221, 'message': '5P8VUG7tQldpGwRbZk8tMDedLeSfBez3k', 'fee': '5737002', 'timestamp': 1669213512, 'hash': 'x1+vjYIpmnmzmwWMK3PuPaiCnzvSA5MF76lgS9t3+pY='}, {'type': 'out', 'from': 'EQCtiv7PrMJImWiF2L5oJCgPnzp-VML2CAt5cbn1VsKAxLiE', 'to': 'EQBc7sxuLW7WA0S1O5Ga0Y19yyj-N7HVn38-_x57DMZ5h9Xi', 'value': 950000000, 'message': 'q4c93IkldxfdzsbBkRzZno0XliRBQgHj2', 'fee': '5729001', 'timestamp': 1669213486, 'hash': 'sks1oNLhbTMl3OXdo9k3bxHGfMNlF+zBaYJQ7J0kvzA='}]

transfer_ton() -> " transfers any amount of ton coins to destination wallet "
```
