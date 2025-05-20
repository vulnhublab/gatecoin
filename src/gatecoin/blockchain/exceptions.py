from gatecoin.exceptions import GatecoinRecoverableError, GatecoinUnrecoverableError


class UnknownGatecoinEventType(GatecoinUnrecoverableError):
    """Raised if decoding an event from a Gatecoin smart contract failed.

    Deserializing an event from one of the Gatecoin smart contracts fails may
    happen for a few reasons:

    - The address is not a Gatecoin smart contract.
    - The address is for a newer version of the Gatecoin's smart contracts with
      an unknown event.

    Either case, it means the node will not be properly synchronized with the
    on-chain state, and this cannot be recovered from.
    """


class EthGetLogsTimeout(GatecoinRecoverableError):
    """Raised when an eth.get_logs RPC call caused a ReadTimeout exception.

    It is used to automatically tune the block batching size.
    """


class BlockBatchSizeTooSmall(GatecoinUnrecoverableError):
    """Raised when the block batch size would have to be reduced below the minimum allowed value.

    This is an unrecoverable error since it indicates that either the connected Eth-node or the
    network connection is not capable of supporting minimum performance requirements for the
    eth.get_logs call.
    """
