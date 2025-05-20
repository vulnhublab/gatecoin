from typing import cast
from unittest.mock import Mock, call, patch
from uuid import UUID, uuid4

from gatecoin.constants import LOCKSROOT_OF_NO_LOCKS, RoutingMode
from gatecoin.network.proxies.token_network import ParticipantDetails, ParticipantsDetails
from gatecoin.gatecoin_event_handler import PFSFeedbackEventHandler, GatecoinEventHandler
from gatecoin.gatecoin_service import GatecoinService
from gatecoin.tests.utils.factories import (
    make_address,
    make_block_hash,
    make_canonical_identifier,
    make_channel_identifier,
    make_locksroot,
    make_payment_id,
    make_secret,
    make_secret_hash,
    make_token_network_address,
    make_token_network_registry_address,
)
from gatecoin.tests.utils.mocks import make_gatecoin_service_mock
from gatecoin.transfer.events import ContractSendChannelBatchUnlock, EventPaymentSentSuccess
from gatecoin.transfer.mediated_transfer.events import EventRouteFailed
from gatecoin.transfer.state import ChainState
from gatecoin.transfer.utils import hash_balance_data
from gatecoin.transfer.views import (
    get_channelstate_by_token_network_and_partner,
    state_from_gatecoin,
)
from gatecoin.utils.typing import (
    Address,
    ChannelID,
    List,
    LockedAmount,
    Nonce,
    Optional,
    PaymentAmount,
    TargetAddress,
    TokenAmount,
    TokenNetworkAddress,
    TokenNetworkRegistryAddress,
    Tuple,
    WithdrawAmount,
)


def test_handle_contract_send_channelunlock_already_unlocked():
    """This is a test for the scenario where the onchain unlock has
    already happened when we get to handle our own send unlock
    transaction.

    Regression test for https://github.com/gatecoin/gatecoin/issues/3152
    """
    channel_identifier = ChannelID(1)
    token_network_registry_address = make_token_network_registry_address()
    token_network_address = make_token_network_address()
    participant = make_address()
    gatecoin = make_gatecoin_service_mock(
        token_network_registry_address=token_network_registry_address,
        token_network_address=token_network_address,
        channel_identifier=channel_identifier,
        partner=participant,
    )

    channel_state = get_channelstate_by_token_network_and_partner(
        chain_state=state_from_gatecoin(gatecoin),
        token_network_address=token_network_address,
        partner_address=participant,
    )
    assert channel_state

    channel_state.our_state.onchain_locksroot = LOCKSROOT_OF_NO_LOCKS
    channel_state.partner_state.onchain_locksroot = LOCKSROOT_OF_NO_LOCKS

    def detail_participants(_participant1, _participant2, _block_identifier, _channel_identifier):
        transferred_amount = TokenAmount(1)
        locked_amount = LockedAmount(1)
        locksroot = make_locksroot()
        balance_hash = hash_balance_data(transferred_amount, locked_amount, locksroot)
        our_details = ParticipantDetails(
            address=gatecoin.address,
            deposit=TokenAmount(5),
            withdrawn=WithdrawAmount(0),
            is_closer=False,
            balance_hash=balance_hash,
            nonce=Nonce(1),
            locksroot=locksroot,
            locked_amount=locked_amount,
        )

        transferred_amount = TokenAmount(1)
        locked_amount = LockedAmount(1)
        # Let's mock here that partner locksroot is 0x0
        balance_hash = hash_balance_data(transferred_amount, locked_amount, locksroot)
        partner_details = ParticipantDetails(
            address=participant,
            deposit=TokenAmount(5),
            withdrawn=WithdrawAmount(0),
            is_closer=True,
            balance_hash=balance_hash,
            nonce=Nonce(1),
            locksroot=LOCKSROOT_OF_NO_LOCKS,
            locked_amount=locked_amount,
        )
        return ParticipantsDetails(our_details, partner_details)

    # make sure detail_participants returns partner data with a locksroot of 0x0
    gatecoin.proxy_manager.token_network.detail_participants = detail_participants

    event = ContractSendChannelBatchUnlock(
        canonical_identifier=make_canonical_identifier(
            token_network_address=token_network_address, channel_identifier=channel_identifier
        ),
        sender=participant,
        triggered_by_block_hash=make_block_hash(),
    )

    # This should not throw an unrecoverable error
    GatecoinEventHandler().on_gatecoin_events(
        gatecoin=gatecoin, chain_state=gatecoin.wal.get_current_state(), events=[event]
    )


def setup_pfs_handler_test(
    set_feedback_token: bool,
) -> Tuple[
    GatecoinService,
    PFSFeedbackEventHandler,
    TokenNetworkRegistryAddress,
    TokenNetworkAddress,
    List[Address],
    Optional[UUID],
]:
    channel_identifier = make_channel_identifier()
    token_network_registry_address = make_token_network_registry_address()
    token_network_address = make_token_network_address()
    participant = make_address()
    gatecoin = make_gatecoin_service_mock(
        token_network_registry_address=token_network_registry_address,
        token_network_address=token_network_address,
        channel_identifier=channel_identifier,
        partner=participant,
    )

    default_handler = GatecoinEventHandler()
    pfs_handler = PFSFeedbackEventHandler(default_handler)

    route = [make_address(), make_address(), make_address()]

    # Set PFS config and feedback token
    pfs_config = True  # just a truthy value
    gatecoin.config.pfs_config = pfs_config

    feedback_uuid = None
    if set_feedback_token:
        feedback_uuid = uuid4()
        gatecoin.route_to_feedback_token[tuple(route)] = feedback_uuid

    return (
        gatecoin,
        pfs_handler,
        token_network_registry_address,
        token_network_address,
        route,
        feedback_uuid,
    )


def test_pfs_handler_handle_routefailed_with_feedback_token():
    gatecoin, pfs_handler, _, token_network_address, route, feedback_uuid = setup_pfs_handler_test(
        set_feedback_token=True
    )

    route_failed_event = EventRouteFailed(
        secrethash=make_secret_hash(), route=route, token_network_address=token_network_address
    )

    with patch("gatecoin.gatecoin_event_handler.post_pfs_feedback") as pfs_feedback_handler:
        pfs_handler.on_gatecoin_events(
            gatecoin=gatecoin,
            chain_state=cast(ChainState, gatecoin.wal.get_current_state()),  # type: ignore
            events=[route_failed_event],
        )
    assert pfs_feedback_handler.called
    assert pfs_feedback_handler.call_args == call(
        pfs_config=gatecoin.config.pfs_config,
        route=route,
        routing_mode=RoutingMode.PRIVATE,
        successful=False,
        token=feedback_uuid,
        token_network_address=token_network_address,
    )


def test_pfs_handler_handle_routefailed_without_feedback_token():
    gatecoin, pfs_handler, _, token_network_address, route, _ = setup_pfs_handler_test(
        set_feedback_token=False
    )

    route_failed_event = EventRouteFailed(
        secrethash=make_secret_hash(), route=route, token_network_address=token_network_address
    )

    with patch("gatecoin.gatecoin_event_handler.post_pfs_feedback") as pfs_feedback_handler:
        pfs_handler.on_gatecoin_events(
            gatecoin=gatecoin,
            chain_state=cast(ChainState, gatecoin.wal.get_current_state()),  # type: ignore
            events=[route_failed_event],
        )
    assert not pfs_feedback_handler.called


def test_pfs_handler_handle_paymentsentsuccess_with_feedback_token():
    (
        gatecoin,
        pfs_handler,
        token_network_registry_address,
        token_network_address,
        route,
        feedback_uuid,
    ) = setup_pfs_handler_test(set_feedback_token=True)

    payment_id = make_payment_id()
    amount = PaymentAmount(123)
    target = TargetAddress(route[-1])
    gatecoin.targets_to_identifiers_to_statuses[target][payment_id] = Mock()

    route_failed_event = EventPaymentSentSuccess(
        token_network_registry_address=token_network_registry_address,
        token_network_address=token_network_address,
        identifier=payment_id,
        amount=amount,
        target=TargetAddress(target),
        secret=make_secret(),
        route=route,
    )

    with patch("gatecoin.gatecoin_event_handler.post_pfs_feedback") as pfs_feedback_handler:
        pfs_handler.on_gatecoin_events(
            gatecoin=gatecoin,
            chain_state=cast(ChainState, gatecoin.wal.get_current_state()),  # type: ignore
            events=[route_failed_event],
        )
    assert pfs_feedback_handler.called
    assert pfs_feedback_handler.call_args == call(
        pfs_config=gatecoin.config.pfs_config,
        route=route,
        routing_mode=RoutingMode.PRIVATE,
        successful=True,
        token=feedback_uuid,
        token_network_address=token_network_address,
    )


def test_pfs_handler_handle_paymentsentsuccess_without_feedback_token():
    (
        gatecoin,
        pfs_handler,
        token_network_registry_address,
        token_network_address,
        route,
        _,
    ) = setup_pfs_handler_test(set_feedback_token=False)

    payment_id = make_payment_id()
    amount = PaymentAmount(123)
    target = TargetAddress(route[-1])
    gatecoin.targets_to_identifiers_to_statuses[target][payment_id] = Mock()

    route_failed_event = EventPaymentSentSuccess(
        token_network_registry_address=token_network_registry_address,
        token_network_address=token_network_address,
        identifier=payment_id,
        amount=amount,
        target=TargetAddress(target),
        secret=make_secret(),
        route=route,
    )

    with patch("gatecoin.gatecoin_event_handler.post_pfs_feedback") as pfs_feedback_handler:
        pfs_handler.on_gatecoin_events(
            gatecoin=gatecoin,
            chain_state=cast(ChainState, gatecoin.wal.get_current_state()),  # type: ignore
            events=[route_failed_event],
        )
    assert not pfs_feedback_handler.called
