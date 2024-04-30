import asyncio

from TonTools import *


async def main():
    client = TonApiClient(key='')

    # client = TonCenterClient(base_url='http://127.0.0.1:80/')

    # client = LsClient(ls_index=2, default_timeout=30)
    # await client.init_tonlib()

    nft_collection = NftCollection('EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT', provider=client)
    print(nft_collection)  # NftCollection({"address": "EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT"})
    await nft_collection.update()
    print(nft_collection)  # NftCollection({"address": "EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT", "owner": "EQBNdc9rYiIQPY-lSYMRInogrkJob5fio5_SihG2uEUL9AcL", "next_item_index": 1621, "metadata": {"name": "Whales Club", "description": "Collection limited to 10000 utility-enabled NFTs, where the token is your membership to the Whales Club. Join the club and participate in weekly Ambra token giveaways, have access to the most profitable Ton Whales decentralized staking pools and many other useful club privileges.", "external_link": "https://tonwhales.com/club", "external_url": "https://tonwhales.com/club", "image": "ipfs://QmZc5PwuyVKSV4urDTArqfDbkGVjkKs6q4dBk8kpPt1bqD/logo.gif", "social_links": ["https://t.me/tonwhalesnft", "https://t.me/tonwhalesnften", "https://twitter.com/whalescorp"], "cover_image": "ipfs://QmZc5PwuyVKSV4urDTArqfDbkGVjkKs6q4dBk8kpPt1bqD/cover.gif"}})

    items = await nft_collection.get_collection_items(limit_per_one_request=100)  # for TonCenterClient and LsClient its better to use limit_per_one_request especially if collection has a lot of items
    print(items[0])  # NftItem({"address": "EQD6ufFjSIUJSkbVuV7w00ORT8UvoMLQ9RDZ1lJ8sYh3cOIx"})

    index = 121

    if isinstance(client, TonCenterClient):
        data = await nft_collection.run_get_method(method='get_nft_address_by_index', stack=[['num', index]])  # TonCenterClient
        item = NftItem(read_address(Cell.one_from_boc(b64str_to_bytes(data[0][1]['bytes']))).to_string(True, True, True), provider=client)  # TonCenterClient
        await item.update()
    if isinstance(client, LsClient):
        data = await nft_collection.run_get_method(method='get_nft_address_by_index', stack=[{"@type": "tvm.stackEntryNumber", "number": {"@type": "tvm.numberDecimal", "number": str(index)}}])  # LsClient
        item = NftItem(read_address(Cell.one_from_boc(b64str_to_bytes(data[0].cell.bytes))).to_string(True, True, True), provider=client)  # LsClient
        await item.update()
    if isinstance(client, TonApiClient):
        items = await nft_collection.get_collection_items(limit_per_one_request=100)  # for TonCenterClient and LsClient its better to use limit_per_one_request especially if collection has a lot of items
        for i in items:
            print(1)
            await i.update()
            if i.index == index:
                item = i
                break

    print(item)  # NftItem({"address": "EQDzyRLwjasHwP-y5c9rtoVi2iqriu-sbL3080FlCc-XyUG4", "collection": {"address": {"address": "EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT"}}, "collection_address": "EQDvRFMYLdxmvY3Tk-cfWMLqDnXF_EclO2Fp4wwj33WhlNFT", "index": 121, "metadata": {"name": "Whale #8986", "image": "https://whales.infura-ipfs.io/ipfs/QmQ5QiuLBEmDdQmdWcEEh2rsW53KWahc63xmPVBUSp4teG/8986.png", "attributes": [{"trait_type": "Tier", "value": "common"}, {"trait_type": "Sex", "value": "male"}, {"trait_type": "Background", "value": "violent"}, {"trait_type": "Belly", "value": "blue"}, {"trait_type": "Back", "value": "green"}, {"trait_type": "Eye", "value": "angry"}, {"trait_type": "Tooth", "value": "white"}]}, "owner": "EQAosLqCBCsm98UGpUNj19ifwNBjEntiECDZgslrvXAH_-Mp", "sale": {"address": "EQAosLqCBCsm98UGpUNj19ifwNBjEntiECDZgslrvXAH_-Mp", "market": {"address": "EQBYTuYbLf8INxFtD8tQeNk5ZLy-nAX9ahQbG_yl1qQ-GEMS", "name": "Getgems Sales"}, "owner": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "price": {"value": 200000000000, "token_name": "TON"}}})
    print(item.sale)  # NftItemSale({"address": "EQAosLqCBCsm98UGpUNj19ifwNBjEntiECDZgslrvXAH_-Mp", "market": {"address": "EQBYTuYbLf8INxFtD8tQeNk5ZLy-nAX9ahQbG_yl1qQ-GEMS", "name": "Getgems Sales"}, "owner": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "price": {"value": 200000000000, "token_name": "TON"}})
    print(item.sale.to_dict()['price'])  # {"value": 200000000000, "token_name": "TON"}
    owner = Wallet(provider=client, address=item.sale.owner)
    print(await owner.get_balance())  # 7611223873069
    transactions = await owner.get_transactions(limit=3)
    print(' '.join([str(tr) for tr in transactions]))  # Transaction({"type": "out", "utime": 1677531709, "hash": "h+lVX0qK4T76QtRqC0FWWGhLptgPLM4MjSEbgKODcFc=", "value": 2500.0, "from": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "to": "EQBfAN7LfaUYgXZNw5Wc7GBgkEX2yhuJ5ka95J1JJwXXf4a8", "comment": "6017835"}) Transaction({"type": "in", "utime": 1677413260, "hash": "erk0nLWW9W3m9boFM+/9v0YSeRz1jJvpyiRQYEgN5AE=", "value": 1e-09, "from": "EQCPGzW1dJURRybL41Q3KYfzX4fZdQUeY8-7-TKyeR7f-7cU", "to": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "comment": ""}) Transaction({"type": "in", "utime": 1677302980, "hash": "FNlzXOtraIjp9iAj6zPdTqrMI++NNgFRpGoxSJ0ez/k=", "value": 10000.098804, "from": "EQCOj4wEjXUR59Kq0KeXUJouY5iAcujkmwJGsYX7qPnITEAM", "to": "EQBZVBXBpirFPOQ5Wmgi5Es2hDCRAfiT3i5JRy_gVsJOlpZv", "comment": ""})


if __name__ == '__main__':
    asyncio.run(main())
