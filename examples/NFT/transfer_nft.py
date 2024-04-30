import asyncio

from TonTools import *


async def main():
    client = TonCenterClient(orbs_access=True)

    my_wallet_mnemonics = []
    my_wallet = Wallet(provider=client, mnemonics=my_wallet_mnemonics, version='v4r2')

    resp = await my_wallet.transfer_nft(destination_address='EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c', nft_address='EQABEmkuk9B91i0CudxiV7jBeCzvF5UHJdAYHOCETLtx3DGX')
    print(resp)  # 200

if __name__ == '__main__':
    asyncio.run(main())
