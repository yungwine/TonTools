import asyncio
from pathlib import Path

from TonTools import LsClient, Wallet, Address


app_dir: Path = Path(__file__).parent.parent


async def main():
    # client = TonApiClient()

    # client = TonCenterClient(base_url='http://127.0.0.1:80/')

    client = LsClient(ls_index=1, cdll_path=app_dir / 'tonlibjson.dll')
    await client.init()

    my_wallet_mnemonics = []
    my_wallet = Wallet(provider=client, mnemonics=my_wallet_mnemonics, version='v4r2')
    my_wallet_nano_balance = await my_wallet.get_balance()

    if client.from_nano(my_wallet_nano_balance) >= 0.03:
        new_wallet = Wallet(provider=client)
        print(new_wallet.address, new_wallet.mnemonics, my_wallet_nano_balance)  # EQBcMK8CBrZKfSYdvT8FDVo1TxZV_d3Lz-xPyGp8c7mUacko ['federal', 'memory', 'scare', 'exact', 'extend', 'rain', 'private', 'ribbon', 'inspire', 'capital', 'arrow', 'glimpse', 'toy', 'double', 'man', 'speak', 'imitate', 'hint', 'dinner', 'oblige', 'rather', 'answer', 'unfold', 'small'] 496348289
        non_bounceable_new_wallet_address = Address(new_wallet.address).to_string(True, True, False)

        await my_wallet.transfer_ton(destination_address=non_bounceable_new_wallet_address, amount=0.02, message='i want to deploy new wallet')

        while True:
            new_wallet_balance = await new_wallet.get_balance()
            await asyncio.sleep(1)
            if new_wallet_balance != 0:
                print(new_wallet_balance)
                break
        await new_wallet.deploy()

        await asyncio.sleep(15)  # wait while transaction process

        print(await new_wallet.get_state())  # active

        return await new_wallet.get_state()


if __name__ == '__main__':
    asyncio.run(main())
