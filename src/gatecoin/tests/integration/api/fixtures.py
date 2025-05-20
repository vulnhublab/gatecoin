from collections.abc import Generator

import pytest

from gatecoin.gatecoin_service import GatecoinService
from gatecoin.tests.integration.api.utils import prepare_api_server
from gatecoin.utils.typing import List


# TODO: Figure out why this fixture can't work as session scoped
#       What happens is that after one test is done, in the next one
#       the server is no longer running even though the teardown has not
#       been invoked.
@pytest.fixture
def api_server_test_instance(gatecoin_network: List[GatecoinService]) -> Generator:
    api_server = prepare_api_server(gatecoin_network[0])

    yield api_server


@pytest.fixture
def client(api_server_test_instance):
    with api_server_test_instance.flask_app.test_client() as client:
        yield client
