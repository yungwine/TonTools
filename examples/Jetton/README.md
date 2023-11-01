# TonTools jetton examples

## [Jetton Master](./get_jetton_master_data.py)

In this example you can find out how to get data of Jetton Master Contract

To do that you can use method `get_jetton_data` of network provider instance and pass Jetton Master address to it.

Underhood, it send get method `get_jetton_data` to the contract, parse data from blockchain and return Jetton class object.

Jetton object have next fields:
- `supply`
- `address`
- `decimals`
- `symbol`
- `name`
- `description`
- `image`
- `token_supply`

## [Jetton Wallet](./get_jetton_wallet_data.py)

In this example you can find out how to get data of Jetton Wallet Contract

You can do that by using `get_jetton_wallet` of network provider with jetton wallet address. 

It use `get_wallet_data` method of contract and return JettonWallet class object that have next fields:
- `address`
- `balance`
- `owner`
- `jetton_master_address`

## [Jetton transfer](./transfer_jetton.py)

Example of sending jettons.

