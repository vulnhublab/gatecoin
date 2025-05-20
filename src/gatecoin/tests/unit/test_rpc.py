from gatecoin.constants import EthClient
from gatecoin.network.rpc.client import ClientErrorInspectResult, inspect_client_error


def test_inspect_client_error():
    """Regression test for issue https://github.com/gatecoin/gatecoin/issues/3005"""
    errorstr = (
        "{'code': -32015, 'message': 'Transaction execution error.', 'data': "
        "'Internal(\"Requires higher than upper limit of 80000000\")'}"
    )
    exception = ValueError(errorstr)

    result = inspect_client_error(exception, EthClient.PARITY)
    assert result == ClientErrorInspectResult.ALWAYS_FAIL
