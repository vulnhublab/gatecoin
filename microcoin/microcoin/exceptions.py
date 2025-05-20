class MicroCoinException(Exception):
    """Base exception for uGatecoin"""
    pass


class InvalidBalanceAmount(MicroCoinException):
    """Raised if the payment contains lesser balance than the previous one."""
    pass


class InvalidBalanceProof(MicroCoinException):
    """Balance proof data do not make sense."""
    pass


class NoOpenChannel(MicroCoinException):
    """Attempt to use nonexisting channel."""
    pass


class InsufficientConfirmations(MicroCoinException):
    """uGatecoin channel doesn't have enough confirmations."""
    pass


class NoBalanceProofReceived(MicroCoinException):
    """Attempt to close channel with no registered payments."""
    pass


class InvalidContractVersion(MicroCoinException):
    """Library is not compatible with the deployed contract version"""
    pass


class StateFileException(MicroCoinException):
    """Base exception class for state file (database) operations"""
    pass


class StateContractAddrMismatch(StateFileException):
    """Stored state contract address doesn't match."""
    pass


class StateReceiverAddrMismatch(StateFileException):
    """Stored state receiver address doesn't match."""
    pass


class StateFileLocked(StateFileException):
    """Another process is already using the database"""
    pass


class InsecureStateFile(StateFileException):
    """Permissions of the state file do not match (0600 is expected)."""
    pass


class NetworkIdMismatch(StateFileException):
    """RPC endpoint and database have different network id."""
    pass
