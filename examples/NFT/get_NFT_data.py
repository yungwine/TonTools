import asyncio

from TonTools import *

NFT = 'EQD6ufFjSIUJSkbVuV7w00ORT8UvoMLQ9RDZ1lJ8sYh3cOIx'


async def main():
    client = TonCenterClient(orbs_access=True)

    data = await client.get_nft_items(nft_addresses=[NFT])

    print(data[0])


if __name__ == '__main__':
    asyncio.run(main())
