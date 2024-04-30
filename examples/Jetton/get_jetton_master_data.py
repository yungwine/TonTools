import asyncio

from TonTools import *

app_dir: Path = Path(__file__).parent.parent.parent


async def main():
    fallback_client = TonApiClient('your_key')
    client = SafeLsClient(fallback_client, cdll_path=app_dir / 'tonlibjson.dll', addresses_form=AddressForm.USER_FRIENDLY)

    await client.init()

    jetton_master_data = await client.get_jetton_data(JettonMasterAddress.GRAM)
    # or
    # jetton_master_data = await client.get_jetton_data(getattr(JettonMasterAddress, '@BTC25'))
    # or
    # jetton_master_data = await client.get_jetton_data('custom_jetton_master_address')

    # jetton_master = Jetton(JettonMasterAddress.usdt, client)
    # await jetton_master.update()
    # jetton_master_data = jetton_master

    print(jetton_master_data)

if __name__ == '__main__':
    asyncio.run(main())
