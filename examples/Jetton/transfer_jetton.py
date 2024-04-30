import asyncio

from TonTools import *

# jetton address
JETTON_MASTER = 'EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI'

# YOUR wallet mnemonic
MNEMONICS = ['your', 'mnemonic', '...']


async def main():
    client = TonCenterClient(orbs_access=True)
    your_wallet = Wallet(provider=client, mnemonics=MNEMONICS, version='v4r2')

    await your_wallet.transfer_jetton(
        destination_address='', 
        jetton_master_address=JETTON_MASTER,
        jettons_amount=1
    )

    print('done')

if __name__ == '__main__':
    asyncio.run(main())
