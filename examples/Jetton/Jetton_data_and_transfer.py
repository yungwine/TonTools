import asyncio

from TonTools import *


async def main():
    client = TonApiClient(key='')

    # client = TonCenterClient(base_url='http://127.0.0.1:80/')

    # client = LsClient(ls_index=2, default_timeout=30)
    # await client.init_tonlib()

    jetton = Jetton('EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI', provider=client)
    print(jetton)  # Jetton({"address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI"})

    await jetton.update()
    print(jetton)  # Jetton({"supply": 4600000000000000000, "address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI", "decimals": 9, "symbol": "LAVE", "name": "Lavandos", "description": "This is a universal token for use in all areas of the decentralized Internet in the TON blockchain, web3, Telegram bots, TON sites. Issue of 4.6 billion coins. Telegram channels: Englishversion: @lave_eng \u0420\u0443\u0441\u0441\u043a\u043e\u044f\u0437\u044b\u0447\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f: @lavet", "image": "https://i.ibb.co/Bj5KqK4/IMG-20221213-115545-207.png", "token_supply": 4600000000.0})

    my_wallet_mnemonics = []
    my_wallet = Wallet(provider=client, mnemonics=my_wallet_mnemonics, version='v4r2')

    if not isinstance(client, TonApiClient):
        jetton_wallet = await jetton.get_jetton_wallet('EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG')
        print(jetton_wallet)  # JettonWallet({"address": "EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-"})

        await jetton_wallet.update()
        print(jetton_wallet)  # JettonWallet({"address": "EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-", "balance": 10000000000000, "owner": "EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG", "jetton_master_address": "EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI"})

        transactions = await jetton_wallet.get_transactions(limit=3)
        print(' '.join([str(tr) for tr in transactions]))  # Transaction({"type": "out", "utime": 1677657080, "hash": "rFxuMWykmLO2q9ohOVxetMdsZDc8lmDR+oFIsWx1D7k=", "value": [1e-09, 0.58981592], "from": "EQDgCBnCncRp4jOi3CMeLn-b71gymAX3W28YZT3Dn0a2dKj-", "to": ["EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG", "EQB339RmvmNdTn4ttwZPRHd1xI8BVaEgZTtWa0li1G01ey76"], "comment": ["", ""]})

        await my_wallet.transfer_jetton(destination_address='address', jetton_master_address=jetton.address, jettons_amount=1000, fee=0.15)  # for TonCenterClient and LsClient
    else:
        await my_wallet.transfer_jetton_by_jetton_wallet(destination_address='address', jetton_wallet='your jetton wallet address', jettons_amount=1000, fee=0.1)  # for all clients


if __name__ == '__main__':
    asyncio.run(main())
