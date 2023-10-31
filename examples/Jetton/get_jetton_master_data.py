import asyncio

from TonTools import *

# jetton address
JETTON_MASTER = 'EQBl3gg6AAdjgjO2ZoNU5Q5EzUIl8XMNZrix8Z5dJmkHUfxI'

async def main():
    client = TonCenterClient(orbs_access=True)

    jetton_master_data = await client.get_jetton_data(JETTON_MASTER)

    # jetton_master = Jetton(JETTON_MASTER, client)
    # await jetton_master.update()
    # jetton_master_data = jetton_master

    print(jetton_master_data)

if __name__ == '__main__':
    asyncio.run(main())