import json
import sys
import time
import base64
import asyncio
from math import ceil
from typing import List

from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.boc import Cell
from tonsdk.utils import Address, bytes_to_b64str, b64str_to_bytes, to_nano

from ton import TonlibClient
import ton.tonlibjson

from .utils import *


async def _get_client(ls: int, timeout: int):
    TonlibClient.enable_unaudited_binaries()
    client = TonlibClient(ls_index=ls, default_timeout=timeout)
    await client.init_tonlib()
    return client


def get_client(ls: int = 0, timeout: int = 30) -> TonlibClient:
    client = asyncio.get_event_loop().run_until_complete(_get_client(ls, timeout))
    return client


def close_client(client: TonlibClient):
    try:
        asyncio.get_event_loop().run_until_complete(client.tonlib_wrapper.close())
        return True
    except:
        return False


def get_nft_owner(addr: str, client: TonlibClient = None):
    if not client:
        client = get_client(2)
    return asyncio.get_event_loop().run_until_complete(_get_nft_owner(client, addr))


async def _get_nft_owner(client: TonlibClient, addr: str):
    account = await client.find_account(addr)
    x = await account.get_nft_data()
    owner_address = x['owner_address'].to_string()
    sale_data = await get_nft_sale(client, owner_address)
    if sale_data:
        owner_address = sale_data['owner']['address']
    return owner_address


def get_items(addresses: list, client: TonlibClient = None, max_requests: int = 1000, ls: int = 0):
    items = {}

    nft_items = []

    for i in range(ceil(len(addresses) / max_requests)):
        if not client or not client.tonlib_wrapper._is_working:
            close_client(client)
            client = get_client(ls)
        tasks = []
        for addr in addresses[i * max_requests:min(len(addresses), max_requests * (i + 1))]:
            tasks.append(get_item(client, addr, nft_items))
        # asyncio.set_event_loop(asyncio.SelectorEventLoop())
        try:
            asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        except:
            close_client(client)
            raise ton.tonlibjson.TonlibException
        else:
            close_client(client)
    if len(nft_items) < len(addresses):
        raise Exception('SCANNED NOT ALL ITEMS')
    return nft_items


async def get_item(client: TonlibClient, addr: str, nft_items: list):
    account = await client.find_account(addr, preload_state=False)
    x = await account.get_nft_data()
    collection_address = x['collection_address'].to_string()
    owner_address = x['owner_address'].to_string()
    nft_address = Address(addr).to_string(is_user_friendly=False)
    content_url = await get_nft_content_url(client, x['content'], collection_address)

    content = await get(content_url)

    collection_content = await get_collection_content(client, x['collection_address'].to_string())
    result = {
        'address': nft_address,
        'collection': {
            'address': collection_address,
            'name': collection_content.get('name'),
            'description': collection_content.get('description'),
            'image': collection_content.get('image')
        },
        'collection_address': collection_address,
        'index': x['index'],
        'content_url': content_url,
        'metadata': content,
        'owner': {
            'address': x['owner_address'].to_string()
        }
    }

    sale_data = await get_nft_sale(client, owner_address)

    if sale_data:
        result['sale'] = sale_data

    nft_items.append(result)


def get_collection(addr: str, client: TonlibClient = None):
    if not client:
        client = get_client()
    return asyncio.get_event_loop().run_until_complete(_get_collection(client, addr))


async def _get_collection(client: TonlibClient, addr: str):
    account = await client.find_account(addr)
    try:
        collection_data = await account.get_collection_data()
    except:
        raise Exception('wallet is not nft collection')
    collection_content = await get_collection_content(client, addr)
    result = {
        'address': Address(addr).to_string(is_user_friendly=False),
        'metadata': collection_content,
        'next_item_index': collection_data['next_item_index'],
        'owner': {
            'address': collection_data['owner_address'].to_string() if isinstance(collection_data['owner_address'], Address) else None
        }
    }
    await client.tonlib_wrapper.close()
    return result


def get_all_wallet_transactions_raw(addr: str, limit: int = 10**9, client: TonlibClient = None):
    """
    highly recommend to use with client which ls index = 2, for e.g. client = get_client(ls=2)
    """
    if not client:
        client = get_client(2)
    return asyncio.get_event_loop().run_until_complete(_get_all_wallet_transactions_raw(client, addr, limit))


def get_all_wallet_transactions(addr: str, limit: int = 10**9, client: TonlibClient = None):
    """
    ! dont use with highload wallets !

    highly recommend to use with client which ls index = 2, for e.g. client = get_client(ls=2)
    """
    if not client:
        client = get_client(2)
    return asyncio.get_event_loop().run_until_complete(_get_all_wallet_transactions(client, addr, limit))


async def _get_all_wallet_transactions(client: TonlibClient, addr: str, limit: int = 10**9):
    all_transactions = await _get_all_wallet_transactions_raw(client, addr, limit)
    result = []
    for tr in all_transactions:
        tr_result = {
            'type': '',  # in or out
            'from': '',  # address in raw format
            'to': '',  # address in raw format
            'value': '',  # value in nanoTon, divide by 10**9 to get Ton
            'message': '',  # comment
            'fee': tr['fee'],
            # 'status': '',  # OK or ERROR TODO
            'timestamp': tr['utime'],  # unix timestamp of transaction
            'hash': tr['transaction_id']['hash']
        }
        if len(tr['out_msgs']):
            tr_result['type'] = 'out'
            tr_result['from'] = Address(addr).to_string(True, True, True)
            tr_result['to'] = Address(tr['out_msgs'][0]['destination']['account_address']).to_string(True, True, True)
            tr_result['value'] = int(tr['out_msgs'][0]['value'])
            tr_result['message'] = base64.b64decode(tr['out_msgs'][0]['msg_data']['text']).decode('utf-8') if tr['out_msgs'][0]['msg_data']['@type'] == 'msg.dataText' else ''
        else:
            tr_result['type'] = 'in'
            tr_result['from'] = Address(tr['in_msg']['source']['account_address']).to_string(True, True, True)
            tr_result['to'] = Address(addr).to_string(is_user_friendly=True)
            tr_result['value'] = int(tr['in_msg']['value'])
            tr_result['message'] = base64.b64decode(tr['in_msg']['msg_data']['text']).decode('utf-8') if tr['in_msg']['msg_data']['@type'] == 'msg.dataText' else ''
        result.append(tr_result)
    await client.tonlib_wrapper.close()
    return result


async def _get_all_wallet_transactions_raw(client: TonlibClient, addr: str, limit: int = 10**9):
    account = await client.find_account(addr)
    all_transactions = []
    lim = 30  # must be more than 1
    trs = await account.get_transactions(limit=lim)
    for tr in trs:
        all_transactions.append(tr.to_json())
    while len(trs) == lim and len(all_transactions) < limit:
        trs = await account.get_transactions(from_transaction_lt=trs[-1].to_json()['transaction_id']['lt'],
                                             from_transaction_hash=trs[-1].to_json()['transaction_id']['hash'],
                                             limit=lim)
        for tr in trs[1:]:
            all_transactions.append(tr.to_json())
    return all_transactions[:limit]


def get_nft_items_by_owner_address(addr: str, client: TonlibClient = None):
    """
    ! shows only nft items were bought by user or were transferred to user's wallet !

    highly recommend to use with client which ls index = 2, for e.g. client = get_client(ls=2)
    """
    if not client:
        client = get_client(2)
    return asyncio.get_event_loop().run_until_complete(_get_nft_items_by_owner_address(client, addr))


async def _get_nft_items_by_owner_address(client: TonlibClient, addr: str):
    result = set()
    all_transactions = await _get_all_wallet_transactions(client, addr)
    await client.tonlib_wrapper.close()
    client = await _get_client(client.ls_index, timeout=15)

    async def proc_tr(tr):
        if tr['type'] == 'in':
            account = await client.find_account(tr['from'])
            try:
                nft_data = await account.get_nft_data()
                owner = nft_data['owner_address'].to_string()
                sale = await get_nft_sale(client, owner)
                if sale:
                    owner = sale['owner']['address']
                if owner == Address(addr).to_string(is_user_friendly=False):
                    result.add(tr['from'])
            except:
                return

    await asyncio.gather(*[proc_tr(tr) for tr in all_transactions])
    await client.tonlib_wrapper.close()
    return list(result)


def get_collection_items(addr: str, client: TonlibClient = None):
    if not client:
        client = get_client()
    return asyncio.get_event_loop().run_until_complete(_get_collection_items(client, addr))


async def _get_collection_items(client: TonlibClient, addr: str):
    account = await client.find_account(addr)
    items_amount = await account.get_collection_data()
    items_amount = items_amount['next_item_index']

    async def get_item_addr(index, result):
        item = await account.get_nft_address_by_index(index=index)
        # result.append(item['address'].to_string(True, True, True)) # human-readable bounceable form
        result.append(item['address'].to_string(is_user_friendly=False)) # raw form

    result = []

    for p in range(ceil(items_amount / 10000)):
        await asyncio.gather(*[get_item_addr(i, result) for i in range(p * 10000, min(items_amount, 10000 * (p + 1)))])
    await client.tonlib_wrapper.close()
    if len(result) < items_amount:
        raise Exception(f'GOT NOT ALL ITEMS.')
    return result


def transfer_ton(mnemonic: list, address: str, value: float, comment: str = '', wallet_version: str = 'v4r2', client: TonlibClient = None):
    """
    :param mnemonic: seed phrase of owner wallet
    :param address: address to send Tons
    :param value: value of Tons (e.g value=0.1 means that 0.1 Ton will be sent)
    :param comment: comment of transaction
    :param wallet_version: owner wallet version, default v4r2
    :return:
    """
    if not client:
        client = get_client(2)

    return asyncio.get_event_loop().run_until_complete(_transfer_ton(client, mnemonic, address, value, comment, wallet_version))


async def _transfer_ton(client: TonlibClient, mnemonic: list, address: str, value: float, comment: str, wallet_version: str):
    mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(mnemonic, WalletVersionEnum(wallet_version), 0)
    account = await client.find_account(wallet.address.to_string())
    seqno = await account.seqno()
    query = wallet.create_transfer_message(to_addr=address,
                                          amount=to_nano(value, 'ton'),
                                          seqno=seqno, payload=comment)
    boc = query["message"].to_boc(False)
    resp = await client.send_boc(boc)
    await client.tonlib_wrapper.close()
    return resp