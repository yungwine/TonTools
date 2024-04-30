import asyncio

from TonTools import *


async def main():
    client = TonCenterClient(orbs_access=True)

    jetton_wallet_data = await client.get_jetton_wallet('Jetton wallet contract address')

    # jetton_wallet = await Jetton(JettonMasterAddress.GRAM, client).get_jetton_wallet(owner_address='EQAc75QKQd4BY4tlBoGJgGbw-z1yIp9Sz9tvJ8yDRIpGc5bE')
    # await jetton_wallet.update()
    # jetton_wallet_data = jetton_wallet

    print(jetton_wallet_data)

if __name__ == '__main__':
    asyncio.run(main())
