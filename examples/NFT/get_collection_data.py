import asyncio

from TonTools import *

COLLECTION = 'EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT'


async def main():
    client = TonCenterClient(orbs_access=True)

    data = await client.get_collection(collection_address=COLLECTION)
    items = await client.get_collection_items(collection=data, limit_per_one_request=20)

    for item in items:
        print(item)
        
    print(data)


if __name__ == '__main__':
    asyncio.run(main())
