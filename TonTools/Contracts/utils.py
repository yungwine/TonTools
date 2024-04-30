from tvm_valuetypes import deserialize_boc
from pytonlib.utils.tlb import Transaction as PytonlibTransaction, Slice as PytonlibSlice
from tonsdk.utils import b64str_to_bytes


def transaction_status(tr_data: str):
    """
    return True if transaction was successful, False otherwise
    """
    if is_hex(tr_data):
        cell = deserialize_boc(bytes.fromhex(tr_data))
    else:
        cell = deserialize_boc(b64str_to_bytes(tr_data))
    tr = PytonlibTransaction(PytonlibSlice(cell))
    if not (tr.description.action and tr.description.action.result_code) and \
            not (tr.description.compute_ph.type == 'tr_phase_compute_vm' and tr.description.compute_ph.exit_code):
        return True
    return False


def is_hex(string: str):
    try:
        int(string, 16)
    except ValueError:
        return False
    return True


known_prefixes = {
    '00000000': 'TextCommentMessage',
    '5fcc3d14': 'NftTransferMessage',
    'd53276db': 'ExcessesMessage',
    '05138d91': 'NftOwnershipAssignedMessage',
    '2fcb26a2': 'NftGetStaticDataMessage',
    '8b771735': 'NftReportStaticDataMessage',
    '0f8a7ea5': 'JettonTransferMessage',
    '7362d09c': 'JettonTransferNotificationMessage',
    '595f07bc': 'JettonBurnMessage',
    '178d4519': 'JettonInternalTransferMessage',
    '7bdd97de': 'JettonBurnNotificationMessage'
}
