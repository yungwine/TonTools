# TonTools

__TonTools__ is a _high-level_ OOP library for Python, which can be used to interact with [TON Blockchain](https://ton.org).

If you have any questions join Python - TON [developers chat](https://t.me/pythonnton).

[comment]: <> ([![PyPI version]&#40;https://badge.fury.io/py/tontools.svg&#41;]&#40;https://badge.fury.io/py/tontools&#41;)

[![PyPI version](https://badge.fury.io/py/tontools.svg)](https://badge.fury.io/py/tontools) ![](https://pepy.tech/badge/tontools) [![Downloads](https://static.pepy.tech/badge/tontools/month)](https://pepy.tech/project/tontools) [![](https://img.shields.io/badge/%F0%9F%92%8E-TON-grey)](https://ton.org)
## How to install:

```bash
pip install tontools
```
## Possibilities
With __TonTools__ you can:
* Scan custom Contracts and run get methods
* Create, deploy and scan wallets
* Scan NFT Collections, Items, Sale contracts
* Scan Jettons, Jetton Wallets
* Transfer Tons, Jettons, NFTs
* Scan Transactions in raw or User-Friendly forms
* And so much more...
## Examples
You can find them in `examples/` directory.

## Donations
__TON__ - EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG

## Providers

__TonTools__ gets data from blockchain using Providers: [TonCenterClient](https://toncenter.com/api/v2/), [LsClient](https://ton.org/docs/participate/nodes/node-types),
[DtonClient](https://docs.dton.io/dton/) and [TonApiClient](https://tonapi.io/swagger-ui) 

Most provider methods are the same, but there are some differences.

### TonCenterClient

[TonCenter](https://toncenter.com/api/v2/) is an Api which uses [lite servers](https://ton.org/docs/participate/nodes/node-types)

To initialize TonCenterClient: 
```python
client = TonCenterClient(base_url='http://127.0.0.1:80/')
or
client = TonCenterClient(api_key)
```
Notice that TonCenter has Limit 10 RPS with Api Key, so It's highly recommend to use [Local TonCenter](https://github.com/toncenter/ton-http-api) 
and specify your host in `base_url` parameter or use the [Orbs Ton Access](https://www.orbs.com/ton-access/): 

```python
client = TonCenterClient(orbs_access=True,
                         testnet=True)

contract = Contract('EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG', client)
print((await contract.get_transactions(limit=10))[-1].out_msgs[0].destination)  # kQCdaMggjCXoW867yRXilPw2bu8Av9dSBlGGCdDPIGNLKM8N
```

### LsClient

**LsClient** gets data from blockhain using [lite servers](https://ton.org/docs/participate/nodes/node-types) (based on [pytonlib](https://github.com/psylopunk/pytonlib))

To initialize LsClient: 
```python
client = LsClient(ls_index=2, default_timeout=30, addresses_form=AddressForm.USER_FRIENDLY)
await client.init()
```
**LsClient** is some more advanced, for e.g. you may need to compile binaries to use it.

### DtonClient
[Dton](https://docs.dton.io/dton) is a high level indexing GraphQL Api. 

To initialize DtonClient:
```python
client = DtonClient(
    key: str = None,  # dton api key
    addresses_form=AddressForm.USER_FRIENDLY,  # addresses_form could be RAW or USER_FRIENDLY
    testnet=False,  # if testnet, all addresses will be in testnet form and base url will start with https://testnet.dton.io/
    private_graphql=False  # you can use private_graphql if you have an api key
)
```
**_Note:_** Dton currently doesn't support sending messages to blockchain, so you can't, for example, transfer toncoins using this provider


### TonApiClient v2

[TonApi](https://tonapi.io/api-v2) is a high level indexing Api. 

To initialize TonApiClient: 
```python
client = TonApiClient(api_key, addresses_form)
```
`TonApiClient` hasn't `run_get_method` method, but it fast (cause of indexator), so 
you should use it if you want to scan a lot of _transactions_ and _contracts_  


### SafeLsClient

**SafeLsClient** is a wrapper for **LsClient** which accepts a fallback client.
Lite servers can be unstable, so if **LsClient** fails to get data, **SafeLsClient** 
will try to get data from the fallback client and change the `ls_index` to the next one for future requests.
```python
fallback_client = TonApiClient(api_key)
client = SafeLsClient(fallback_client, cdll_path=app_dir / 'tonlibjson.dll')
await client.init()
```
**_Note:_** Provide a fallback client that has methods you need to use.


## Contracts
All _Contracts_ are inherited from the base class **Contract**, which has 
`.get_transactions(), .run_get_method(), .get_balance(), .get_state()` methods.
So you can use them with any type of **Contract**:
```python
client = TonCenterClient(base_url='http://127.0.0.1:80/')

item = NftItem('EQDzyRLwjasHwP-y5c9rtoVi2iqriu-sbL3080FlCc-XyUG4', provider=client)
await item.update()

owner = Wallet(provider=client, address=item.sale.owner)
transactions = await owner.get_transactions(limit=2)

print(transactions[0], transactions[1])
# Transaction({"type": "out", "utime": 1677531709, "hash": "h+lVX0qK4T76QtRqC0FWWGhLptgPLM4MjSEbgKODcFc=", "value": 2500.0, "from": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "to": "EQBfAN7LfaUYgXZNw5Wc7GBgkEX2yhuJ5ka95J1JJwXXf4a8", "comment": "6017835"}) Transaction({"type": "in", "utime": 1677413260, "hash": "erk0nLWW9W3m9boFM+/9v0YSeRz1jJvpyiRQYEgN5AE=", "value": 1e-09, "from": "EQCPGzW1dJURRybL41Q3KYfzX4fZdQUeY8-7-TKyeR7f-7cU", "to": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "comment": ""})

print(await item.sale.get_balance()) # 75730000

```
You can init object of some Contract just specifying `address` and `provider`,
but to get full data of this object you should call `await object.update()`

### NFT Contracts

There are `NftItem, NftCollection and NftItemSale` classes.
```python
item = NftItem('EQDzyRLwjasHwP-y5c9rtoVi2iqriu-sbL3080FlCc-XyUG4', provider=client)
await item.update()

collection = item.collection
await collection.update()

print(collection.metadata) #  {"name": "Whales Club", "description": "Collection limited to 10000 utility-enabled NFTs, where the token is your membership to the Whales Club. Join the club and participate in weekly Ambra token giveaways, have access to the most profitable Ton Whales decentralized staking pools and many other useful club privileges.", "external_link": "https://tonwhales.com/club", "external_url": "https://tonwhales.com/club", "image": "ipfs://QmZc5PwuyVKSV4urDTArqfDbkGVjkKs6q4dBk8kpPt1bqD/logo.gif", "social_links": ["https://t.me/tonwhalesnft", "https://t.me/tonwhalesnften", "https://twitter.com/whalescorp"], "cover_image": "ipfs://QmZc5PwuyVKSV4urDTArqfDbkGVjkKs6q4dBk8kpPt1bqD/cover.gif"}
items = await collection.get_collection_items()
print(len(items), items[0])  # 1621 NftItem({"address": "EQD6ufFjSIUJSkbVuV7w00ORT8UvoMLQ9RDZ1lJ8sYh3cOIx"})

sale = item.sale
print(sale.price_value, sale.owner) #  200000000000 EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv
```

### Jetton Contracts
There are `Jetton and JettonWallet` classes.
```python
client = LsClient(ls_index=2, default_timeout=30)
await client.init()

jetton = Jetton('EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI', provider=client)
print(jetton)  # Jetton({"address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI"})

await jetton.update()
print(jetton)  # Jetton({"supply": 4600000000000000000, "address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI", "decimals": 9, "symbol": "LAVE", "name": "Lavandos", "description": "This is a universal token for use in all areas of the decentralized Internet in the TON blockchain, web3, Telegram bots, TON sites. Issue of 4.6 billion coins. Telegram channels: Englishversion: @lave_eng \u0420\u0443\u0441\u0441\u043a\u043e\u044f\u0437\u044b\u0447\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f: @lavet", "image": "https://i.ibb.co/Bj5KqK4/IMG-20221213-115545-207.png", "token_supply": 4600000000.0})

jetton_wallet = await jetton.get_jetton_wallet('EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG')  # for TonCenterClient and LsClient
print(jetton_wallet)  # JettonWallet({"address": "EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-"})

await jetton_wallet.update()
print(jetton_wallet)  # JettonWallet({"address": "EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-", "balance": 10000000000000, "owner": "EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG", "jetton_master_address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI"})

my_wallet_mnemonics = []
my_wallet = Wallet(provider=client, mnemonics=my_wallet_mnemonics, version='v4r2')
await my_wallet.transfer_jetton(destination_address='address', jetton_master_address=jetton.address, jettons_amount=1000, fee=0.15)  # for TonCenterClient and LsClient
await my_wallet.transfer_jetton_by_jetton_wallet(destination_address='address', jetton_wallet='your jetton wallet address', jettons_amount=1000, fee=0.1)  # for all clients
```


### Wallet contracts
Currently there is only `Wallet` class (will add HighLoadWallet and MultiSigWallet in future versions).

You can create new wallet just calling `Wallet(provider, wallet_version)`, check existing wallet `Wallet(provider, address)` or enter wallet `Wallet(provider, mnemonics, wallet_version)`
```python
client = LsClient(ls_index=2, default_timeout=20)
await client.init()

my_wallet_mnemonics = []
my_wallet = Wallet(provider=client, mnemonics=my_wallet_mnemonics, version='v4r2')
my_wallet_nano_balance = await my_wallet.get_balance()

new_wallet = Wallet(provider=client)
print(new_wallet.address, new_wallet.mnemonics, my_wallet_nano_balance)  # EQBcMK8CBrZKfSYdvT8FDVo1TxZV_d3Lz-xPyGp8c7mUacko ['federal', 'memory', 'scare', 'exact', 'extend', 'rain', 'private', 'ribbon', 'inspire', 'capital', 'arrow', 'glimpse', 'toy', 'double', 'man', 'speak', 'imitate', 'hint', 'dinner', 'oblige', 'rather', 'answer', 'unfold', 'small'] 496348289

non_bounceable_new_wallet_address = Address(new_wallet.address).to_string(True, True, False)
await my_wallet.transfer_ton(destination_address=non_bounceable_new_wallet_address, amount=0.02, message='just random comment')
await new_wallet.deploy()

print(await new_wallet.get_state())  # active
```

### Transactions
Class `Transaction` has `.to_dict()` and `.to_dict_user_friendly()` methods.
The first one returns full data of transaction, and the second one only user-friendly data of transaction

*status* - True if computation and action phases have returned zero code.
```python
client = TonApiClient()
wallet = Wallet(provider=client, address='EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG')
trs = await wallet.get_transactions(limit=1) 
print(trs[0].to_dict())  # {'utime': 1677658702, 'fee': 7384081, 'data': 'a lot of bytes :)', 'hash': 'skqFysIHksJDkH8Sy4UAKmQSuW95WGS6V/XD/QaJCdE=', 'in_msg': {'created_lt': 35690250000001, 'source': '', 'destination': 'EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG', 'value': 0, 'msg_data': 'a lot of bytes :'}, 'out_msgs': [{'created_lt': 35690250000002, 'source': 'EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG', 'destination': 'EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-', 'value': 100000000, 'msg_data': 'te6ccgEBAQEAVwAAqg+KfqUAAAAAAAAAAF6NSlEACADvv6jNfMa6nPxbbgyeiO7riR4Cq0JAynas1pLFqNpq9wAd9/UZr5jXU5+LbcGT0R3dcSPAVWhIGU7VmtJYtRtNXsA='}]}
print(trs[0].to_dict_user_friendly())  # {'type': 'out', 'utime': 1677658702, 'status': True, 'hash': 'skqFysIHksJDkH8Sy4UAKmQSuW95WGS6V/XD/QaJCdE=', 'value': 0.1, 'from': 'EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG', 'to': 'EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-', 'comment': ''}
```
_Note:_ `.to_dict_user_friendly()` works good with many recipients in one transaction
#### Messages
You can check the type of message using `.try_detect_type()` method.
```python
client = TonCenterClient()

contract = Contract('EQB5DER03H1uhKGX6BJh_IWa_zV9MzvH2lcy6t30tZ9k4RSL', client)
print((await contract.get_transactions())[-1].in_msg.try_detect_type())  # JettonTransferNotificationMessage

contract = Contract('EQB5QP6tAVlWBXKhMN9TynyusIR8_oTuN10NozaOfpFzAXDj', client)
print((await contract.get_transactions())[-1].in_msg.try_detect_type())  # JettonInternalTransferMessage
```
