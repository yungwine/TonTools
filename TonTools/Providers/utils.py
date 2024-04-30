import typing
import unicodedata
from base64 import b64decode
import aiohttp

from tonsdk.boc import Cell


def is_hex(s: str):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def _get_refs(callback, default: typing.Any = ''):
    try:
        return callback()
    except IndexError:
        return default


def process_jetton_data(data):
    if not len(Cell.one_from_boc(b64decode(data)).refs):
        url = Cell.one_from_boc(b64decode(data)).bits.get_top_upped_array().decode().split('\x01')[-1]
        return url
    else:
        symbol = _get_refs(lambda: Cell.one_from_boc(b64decode(data)).refs[0].refs[1].refs[0].refs[1].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1])
        desc1 = _get_refs(lambda: unicodedata.normalize("NFKD", Cell.one_from_boc(b64decode(data)).refs[0].refs[1].refs[1].refs[0].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1]))
        desc2 = _get_refs(lambda: unicodedata.normalize("NFKD", Cell.one_from_boc(b64decode(data)).refs[0].refs[1].refs[1].refs[0].refs[0].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1]))
        decimals = _get_refs(lambda: Cell.one_from_boc(b64decode(data)).refs[0].refs[1].refs[1].refs[1].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1], 0)
        name = _get_refs(lambda: Cell.one_from_boc(b64decode(data)).refs[0].refs[1].refs[0].refs[0].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1])
        image = _get_refs(lambda: Cell.one_from_boc(b64decode(data)).refs[0].refs[0].refs[0].bits.get_top_upped_array().decode().split('\x00')[-1])
        return {
            'name': name,
            'description': desc1 + desc2,
            'image': image,
            'symbol': symbol,
            'decimals': int(decimals)
        }


async def get(url: str):
    if 'ipfs' in url:
        url = 'https://ipfs.io/ipfs/' + url.split('ipfs://')[-1]
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json(content_type=None)

markets_adresses = {
    '0:584ee61b2dff0837116d0fcb5078d93964bcbe9c05fd6a141b1bfca5d6a43e18': 'Getgems Sales',
    '0:a3935861f79daf59a13d6d182e1640210c02f98e3df18fda74b8f5ab141abf18': 'Getgems Sales',
    '0:eb2eaf97ea32993470127208218748758a88374ad2bbd739fc75c9ab3a3f233d': 'Disintar Marketplace',
    '0:1ecdb7672d5b0b4aaf2d9d5573687c7190aa6849804d9e7d7aef71975ac03e2e': 'TON Diamonds'
}
