from typing import List

import pytest

from gatecoin.gatecoin_service import GatecoinService
from gatecoin.tests.utils.detect_failure import raise_on_failure
from gatecoin.tests.utils.network import CHAIN
from gatecoin.tests.utils.transfer import (
    assert_succeeding_transfer_invariants,
    block_timeout_for_transfer_by_secrethash,
    transfer,
    wait_assert,
)
from gatecoin.transfer import views
from gatecoin.utils.typing import PaymentAmount, PaymentID


@raise_on_failure
@pytest.mark.parametrize("channels_per_node", [CHAIN])
@pytest.mark.parametrize("number_of_nodes", [3, 4, 5])
def test_mediated_transfer(
    gatecoin_network: List[GatecoinService],
    number_of_nodes,
    deposit,
    token_addresses,
    network_wait,
    bench,
):
    apps = gatecoin_network
    token_address = token_addresses[0]
    chain_state = views.state_from_gatecoin(apps[0])
    token_network_registry_address = apps[0].default_registry.address
    token_network_address = views.get_token_network_address_by_token_address(
        chain_state, token_network_registry_address, token_address
    )

    with bench():
        amount = PaymentAmount(10)
        with bench("transfer"):
            secrethash = transfer(
                initiator_app=apps[0],
                target_app=apps[-1],
                token_address=token_address,
                amount=amount,
                identifier=PaymentID(1),
                timeout=network_wait * number_of_nodes,
                routes=[apps],
            )

        while len(apps) > 1:
            app1 = apps.pop(0)
            app2 = apps[0]
            with block_timeout_for_transfer_by_secrethash(app2, secrethash):
                wait_assert(
                    assert_succeeding_transfer_invariants,
                    token_network_address,
                    app1,
                    deposit - amount,
                    [],
                    app2,
                    deposit + amount,
                    [],
                )
