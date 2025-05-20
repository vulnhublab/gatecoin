from typing import List

import pytest

from gatecoin import waiting
from gatecoin.api.python import GatecoinAPI
from gatecoin.gatecoin_service import GatecoinService
from gatecoin.tests.utils.detect_failure import raise_on_failure
from gatecoin.tests.utils.network import CHAIN
from gatecoin.tests.utils.transfer import block_offset_timeout
from gatecoin.transfer import views
from gatecoin.utils.typing import BlockTimeout


@raise_on_failure
@pytest.mark.parametrize("channels_per_node", [CHAIN])
@pytest.mark.parametrize("number_of_nodes", [3])
def test_leave_token_network(gatecoin_network: List[GatecoinService], token_addresses):
    registry_address = gatecoin_network[0].default_registry.address
    token_address = token_addresses[0]
    _, app1, _ = gatecoin_network

    channels = views.list_channelstate_for_tokennetwork(
        chain_state=views.state_from_gatecoin(app1),
        token_network_registry_address=registry_address,
        token_address=token_address,
    )

    timeout = block_offset_timeout(
        app1, "Channels not settled in time", BlockTimeout(channels[0].settle_timeout * 10)
    )
    with timeout:
        GatecoinAPI(app1).token_network_leave(registry_address, token_address)
        waiting.wait_for_settle(
            gatecoin=app1,
            token_network_registry_address=registry_address,
            token_address=token_address,
            channel_ids=[channel.identifier for channel in channels],
            retry_timeout=0.1,
        )
