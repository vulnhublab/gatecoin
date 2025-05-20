from unittest.mock import Mock, patch

import gevent
import pytest

from gatecoin import waiting
from gatecoin.constants import RoutingMode
from gatecoin.exceptions import InvalidSecret
from gatecoin.message_handler import MessageHandler
from gatecoin.network.transport import MatrixTransport
from gatecoin.gatecoin_event_handler import GatecoinEventHandler
from gatecoin.gatecoin_service import GatecoinService
from gatecoin.tests.integration.fixtures.gatecoin_network import RestartNode
from gatecoin.tests.utils.detect_failure import raise_on_failure
from gatecoin.tests.utils.events import gatecoin_events_search_for_item
from gatecoin.tests.utils.factories import make_secret
from gatecoin.tests.utils.network import CHAIN, SimplePFSProxy
from gatecoin.tests.utils.protocol import HoldGatecoinEventHandler
from gatecoin.tests.utils.transfer import (
    assert_synced_channel_state,
    block_offset_timeout,
    create_route_state_for_route,
    watch_for_unlock_failures,
)
from gatecoin.transfer import views
from gatecoin.transfer.events import EventPaymentSentSuccess
from gatecoin.transfer.mediated_transfer.events import SendLockedTransfer, SendSecretReveal
from gatecoin.ui.startup import GatecoinBundle
from gatecoin.utils.secrethash import sha256_secrethash
from gatecoin.utils.transfers import create_default_identifier
from gatecoin.utils.typing import (
    Address,
    Balance,
    BlockNumber,
    List,
    PaymentAmount,
    PaymentID,
    TargetAddress,
    TokenAddress,
    TokenAmount,
)


@raise_on_failure
@pytest.mark.parametrize("deposit", [10])
@pytest.mark.parametrize("channels_per_node", [CHAIN])
@pytest.mark.parametrize("number_of_nodes", [2])
def test_send_queued_messages_after_restart(  # pylint: disable=unused-argument
    gatecoin_network: List[GatecoinService],
    restart_node: RestartNode,
    deposit: TokenAmount,
    token_addresses: List[TokenAddress],
    network_wait: float,
):
    """Test re-sending of undelivered messages on node restart"""
    app0, app1 = gatecoin_network
    token_address = token_addresses[0]
    chain_state = views.state_from_gatecoin(app0)
    token_network_registry_address = app0.default_registry.address
    token_network_address = views.get_token_network_address_by_token_address(
        chain_state, token_network_registry_address, token_address
    )
    assert token_network_address

    number_of_transfers = 7
    amount_per_transfer = PaymentAmount(1)
    total_transferred_amount = TokenAmount(amount_per_transfer * number_of_transfers)

    # Make sure none of the transfers will be sent before the restart
    transfers = []
    for secret_seed in range(number_of_transfers):
        secret = make_secret(secret_seed)
        secrethash = sha256_secrethash(secret)
        transfers.append((create_default_identifier(), amount_per_transfer, secret, secrethash))

        assert isinstance(app0.gatecoin_event_handler, HoldGatecoinEventHandler)  # for mypy
        app0.gatecoin_event_handler.hold(
            SendLockedTransfer, {"transfer": {"lock": {"secrethash": secrethash}}}
        )

    for identifier, amount, secret, _ in transfers:
        app0.mediated_transfer_async(
            token_network_address=token_network_address,
            amount=amount,
            target=TargetAddress(app1.address),
            identifier=identifier,
            secret=secret,
            route_states=[create_route_state_for_route([app0, app1], token_address)],
        )

    app0.stop()

    # Restart the app. The pending transfers must be processed.
    new_transport = MatrixTransport(
        config=app0.config.transport, environment=app0.config.environment_type
    )
    gatecoin_event_handler = GatecoinEventHandler()
    message_handler = MessageHandler()
    services = [app1]
    app0_restart = GatecoinService(
        config=app0.config,
        rpc_client=app0.rpc_client,
        proxy_manager=app0.proxy_manager,
        query_start_block=BlockNumber(0),
        gatecoin_bundle=GatecoinBundle(
            app0.default_registry,
            app0.default_secret_registry,
        ),
        services_bundle=app0.default_services_bundle,
        transport=new_transport,
        gatecoin_event_handler=gatecoin_event_handler,
        message_handler=message_handler,
        routing_mode=RoutingMode.PFS,
        pfs_proxy=SimplePFSProxy(services),
    )
    services.append(app0_restart)
    assert app0.address == app0_restart.address

    del app0
    restart_node(app0_restart)

    # XXX: There is no synchronization among the app and the test, so it is
    # possible between `start` and the check below that some of the transfers
    # have completed, making it flaky.
    #
    # Make sure the transfers are in the queue and fail otherwise.
    chain_state = views.state_from_gatecoin(app0_restart)
    for _, _, _, secrethash in transfers:
        msg = "The secrethashes of the pending transfers must be in the queue after a restart."
        assert secrethash in chain_state.payment_mapping.secrethashes_to_task, msg

    timeout = block_offset_timeout(app1, "Timeout waiting for balance update of app0")
    with watch_for_unlock_failures(*gatecoin_network), timeout:
        waiting.wait_for_payment_balance(
            gatecoin=app0_restart,
            token_network_registry_address=token_network_registry_address,
            token_address=token_address,
            partner_address=app1.address,
            target_address=app1.address,
            target_balance=total_transferred_amount,
            retry_timeout=network_wait,
        )
        timeout.exception_to_throw = ValueError("Timeout waiting for balance update of app1")
        waiting.wait_for_payment_balance(
            gatecoin=app1,
            token_network_registry_address=token_network_registry_address,
            token_address=token_address,
            partner_address=app0_restart.address,
            target_address=app1.address,
            target_balance=total_transferred_amount,
            retry_timeout=network_wait,
        )

    assert_synced_channel_state(
        token_network_address,
        app0_restart,
        Balance(deposit - total_transferred_amount),
        [],
        app1,
        Balance(deposit + total_transferred_amount),
        [],
    )
    new_transport.stop()


@raise_on_failure
@pytest.mark.parametrize("number_of_nodes", [2])
@pytest.mark.parametrize("channels_per_node", [1])
@pytest.mark.parametrize("number_of_tokens", [1])
@patch("gatecoin.message_handler.decrypt_secret", side_effect=InvalidSecret)
def test_payment_statuses_are_restored(  # pylint: disable=unused-argument
    decrypt_patch: Mock,
    gatecoin_network: List[GatecoinService],
    restart_node: RestartNode,
    token_addresses: List[TokenAddress],
    network_wait: float,
):
    """Test that when the Gatecoin is restarted, the dictionary of
    `targets_to_identifiers_to_statuses` is populated before the transport
    is started.
    This should happen because if a client gets restarted during a transfer
    cycle, once restarted, the client will proceed with the cycle
    until the transfer is successfully sent. However, the dictionary
    `targets_to_identifiers_to_statuses` will not contain the payment
    identifiers that were originally registered when the previous client
    started the transfers.
    Related issue: https://github.com/gatecoin/gatecoin/issues/3432
    """
    app0, app1 = gatecoin_network

    token_address = token_addresses[0]
    chain_state = views.state_from_gatecoin(app0)
    token_network_registry_address = app0.default_registry.address
    token_network_address = views.get_token_network_address_by_token_address(
        chain_state, token_network_registry_address, token_address
    )
    assert token_network_address

    target_address = TargetAddress(app1.address)

    # make a few transfers from app0 to app1
    amount = PaymentAmount(1)
    spent_amount = TokenAmount(7)

    for identifier in range(spent_amount):
        # Make sure the transfer is not completed
        secret = make_secret(identifier)

        assert isinstance(app0.gatecoin_event_handler, HoldGatecoinEventHandler)  # for mypy
        app0.gatecoin_event_handler.hold(SendSecretReveal, {"secret": secret})

        identifier = identifier + 1
        payment_status = app0.mediated_transfer_async(
            token_network_address=token_network_address,
            amount=amount,
            target=target_address,
            identifier=PaymentID(identifier),
            secret=secret,
            route_states=[create_route_state_for_route([app0, app1], token_address)],
        )
        assert payment_status.payment_identifier == identifier

    services = [app1]
    app0_restart = GatecoinService(
        config=app0.config,
        rpc_client=app0.rpc_client,
        proxy_manager=app0.proxy_manager,
        query_start_block=BlockNumber(0),
        gatecoin_bundle=GatecoinBundle(
            app0.default_registry,
            app0.default_secret_registry,
        ),
        services_bundle=app0.default_services_bundle,
        transport=MatrixTransport(
            config=app0.config.transport, environment=app0.config.environment_type
        ),
        gatecoin_event_handler=GatecoinEventHandler(),
        message_handler=MessageHandler(),
        routing_mode=RoutingMode.PFS,
        pfs_proxy=SimplePFSProxy(services),
    )
    services.append(app0_restart)
    app0.stop()
    del app0  # from here on the app0_restart should be used
    # stop app1 to make sure that we don't complete the transfers before our checks
    app1.stop()
    restart_node(app0_restart)

    # Check that the payment statuses were restored properly after restart
    for identifier in range(spent_amount):
        identifier = PaymentID(identifier + 1)
        mapping = app0_restart.targets_to_identifiers_to_statuses
        status = mapping[target_address][identifier]
        assert status.amount == 1
        assert status.payment_identifier == identifier
        assert status.token_network_address == token_network_address

    restart_node(app1)  # now that our checks are done start app1 again

    with watch_for_unlock_failures(*gatecoin_network):
        with gevent.Timeout(60):
            waiting.wait_for_payment_balance(
                gatecoin=app1,
                token_network_registry_address=token_network_registry_address,
                token_address=token_address,
                partner_address=app0_restart.address,
                target_address=Address(target_address),
                target_balance=spent_amount,
                retry_timeout=network_wait,
            )

    # Check that payments are completed after both nodes come online after restart
    for identifier in range(spent_amount):
        assert gatecoin_events_search_for_item(
            app0_restart,
            EventPaymentSentSuccess,
            {"identifier": identifier + 1, "amount": 1},
        )
