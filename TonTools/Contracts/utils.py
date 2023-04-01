from tvm_valuetypes import deserialize_boc
from pytonlib.utils.tlb import Transaction, Slice
from tonsdk.utils import b64str_to_bytes


def transaction_status(tr_data: str):
    """
    return True if transaction was successful, False otherwise
    """
    if is_hex(tr_data):
        cell = deserialize_boc(bytes.fromhex(tr_data))
    else:
        cell = deserialize_boc(b64str_to_bytes(tr_data))
    tr = Transaction(Slice(cell))
    if not(tr.description.action and tr.description.action.result_code) and \
            not(tr.description.compute_ph.type == 'tr_phase_compute_vm' and tr.description.compute_ph.exit_code):
        return True
    return False


def is_hex(string: str):
    try:
        int(string, 16)
    except ValueError:
        return False
    return True
