from gatecoin.exceptions import GatecoinRecoverableError


class MintFailed(GatecoinRecoverableError):
    """Raised if calling the mint function failed."""

    pass
