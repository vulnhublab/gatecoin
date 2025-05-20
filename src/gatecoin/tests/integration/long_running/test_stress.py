import time
from http import HTTPStatus
from itertools import count
from typing import Sequence

import gevent
import grequests
import pytest
import structlog
from eth_utils import to_canonical_address
from flask import url_for

from gatecoin.api.python import GatecoinAPI
from gatecoin.api.rest import APIServer, RestAPI
from gatecoin.constants import RoutingMode
from gatecoin.message_handler import MessageHandler
from gatecoin.network.transport import MatrixTransport
from gatecoin.gatecoin_event_handler import GatecoinEventHandler
from gatecoin.gatecoin_service import GatecoinService
from gatecoin.settings import RestApiConfig
from gatecoin.tests.integration.api.utils import wait_for_listening_port
from gatecoin.tests.integration.fixtures.gatecoin_network import RestartNode
from gatecoin.tests.utils.detect_failure import raise_on_failure
from gatecoin.tests.utils.protocol import HoldGatecoinEventHandler
from gatecoin.tests.utils.transfer import (
    assert_synced_channel_state,
    wait_assert,
    watch_for_unlock_failures,
)
from gatecoin.transfer import views
from gatecoin.ui.startup import GatecoinBundle
from gatecoin.utils.formatting import to_checksum_address
from gatecoin.utils.typing import (
    Address,
    BlockNumber,
    Host,
    Iterator,
    List,
    Port,
    TokenAddress,
    TokenAmount,
    TokenNetworkAddress,
    Tuple,
)

log = structlog.get_logger(__name__)


def iwait_and_get(items: Sequence[gevent.Greenlet]) -> None:
    """Iteratively wait and get on passed greenlets.

    This ensures exceptions in the greenlets are re-raised as soon as possible.
    """
    for item in gevent.iwait(items):
        item.get()


def _url_for(apiserver: APIServer, endpoint: str, **kwargs) -> str:
    # url_for() expects binary address so we have to convert here
    for key, val in kwargs.items():
        if isinstance(val, str) and val.startswith("0x"):
            kwargs[key] = to_canonical_address(val)

    with apiserver.flask_app.app_context():
        return url_for(f"v1_resources.{endpoint}", **kwargs)


def start_apiserver(gatecoin_app: GatecoinService, rest_api_port_number: Port) -> APIServer:
    gatecoin_api = GatecoinAPI(gatecoin_app)
    rest_api = RestAPI(gatecoin_api)
    api_server = APIServer(
        rest_api, config=RestApiConfig(host=Host("localhost"), port=rest_api_port_number)
    )

    # required for url_for
    api_server.flask_app.config["SERVER_NAME"] = f"localhost:{rest_api_port_number}"

    api_server.start()

    wait_for_listening_port(rest_api_port_number)

    return api_server


def start_apiserver_for_network(
    gatecoin_network: List[GatecoinService], port_generator: Iterator[Port]
) -> List[APIServer]:
    return [start_apiserver(app, next(port_generator)) for app in gatecoin_network]


def restart_app(app: GatecoinService, restart_node: RestartNode) -> GatecoinService:
    new_transport = MatrixTransport(
        config=app.config.transport, environment=app.config.environment_type
    )
    gatecoin_event_handler = GatecoinEventHandler()
    hold_handler = HoldGatecoinEventHandler(gatecoin_event_handler)

    app = GatecoinService(
        config=app.config,
        rpc_client=app.rpc_client,
        proxy_manager=app.proxy_manager,
        query_start_block=BlockNumber(0),
        gatecoin_bundle=GatecoinBundle(
            app.default_registry,
            app.default_secret_registry,
        ),
        services_bundle=app.default_services_bundle,
        transport=new_transport,
        gatecoin_event_handler=hold_handler,
        message_handler=MessageHandler(),
        routing_mode=RoutingMode.PRIVATE,
    )

    restart_node(app)

    return app


def restart_network(
    gatecoin_network: List[GatecoinService], restart_node: RestartNode
) -> List[GatecoinService]:
    for app in gatecoin_network:
        app.stop()

    wait_network = (gevent.spawn(restart_app, app, restart_node) for app in gatecoin_network)

    gevent.joinall(set(wait_network), raise_error=True)

    new_network = [greenlet.get() for greenlet in wait_network]

    return new_network


def restart_network_and_apiservers(
    gatecoin_network: List[GatecoinService],
    restart_node: RestartNode,
    api_servers: List[APIServer],
    port_generator: Iterator[Port],
) -> Tuple[List[GatecoinService], List[APIServer]]:
    """Stop an app and start it back"""
    for rest_api in api_servers:
        rest_api.stop()

    new_network = restart_network(gatecoin_network, restart_node)
    new_servers = start_apiserver_for_network(new_network, port_generator)

    return (new_network, new_servers)


def address_from_apiserver(apiserver: APIServer) -> Address:
    return apiserver.rest_api.gatecoin_api.address


def transfer_and_assert(
    server_from: APIServer,
    server_to: APIServer,
    token_address: TokenAddress,
    identifier: int,
    amount: TokenAmount,
) -> None:
    url = _url_for(
        server_from,
        "token_target_paymentresource",
        token_address=to_checksum_address(token_address),
        target_address=to_checksum_address(address_from_apiserver(server_to)),
    )
    json = {"amount": amount, "identifier": identifier}

    log.debug("PAYMENT REQUEST", url=url, json=json)

    request = grequests.post(url, json=json)

    start = time.monotonic()
    response = request.send().response
    duration = time.monotonic() - start

    log.debug("PAYMENT RESPONSE", url=url, json=json, response=response, duration=duration)

    assert getattr(request, "exception", None) is None
    assert response is not None
    assert response.status_code == HTTPStatus.OK, f"Payment failed, reason: {response.content}"
    assert response.headers["Content-Type"] == "application/json"


def sequential_transfers(
    server_from: APIServer,
    server_to: APIServer,
    number_of_transfers: int,
    token_address: TokenAddress,
    identifier_generator: Iterator[int],
) -> None:
    for _ in range(number_of_transfers):
        transfer_and_assert(
            server_from=server_from,
            server_to=server_to,
            token_address=token_address,
            identifier=next(identifier_generator),
            amount=TokenAmount(1),
        )


def stress_send_serial_transfers(
    rest_apis: List[APIServer],
    token_address: TokenAddress,
    identifier_generator: Iterator[int],
    deposit: TokenAmount,
) -> None:
    """Send `deposit` transfers of value `1` one at a time, without changing
    the initial capacity.
    """
    pairs = list(zip(rest_apis, rest_apis[1:] + [rest_apis[0]]))

    # deplete the channels in one direction
    for server_from, server_to in pairs:
        sequential_transfers(
            server_from=server_from,
            server_to=server_to,
            number_of_transfers=deposit,
            token_address=token_address,
            identifier_generator=identifier_generator,
        )

    # deplete the channels in the backwards direction
    for server_to, server_from in pairs:
        sequential_transfers(
            server_from=server_from,
            server_to=server_to,
            number_of_transfers=deposit * 2,
            token_address=token_address,
            identifier_generator=identifier_generator,
        )

    # reset the balances balances by sending the "extra" deposit forward
    for server_from, server_to in pairs:
        sequential_transfers(
            server_from=server_from,
            server_to=server_to,
            number_of_transfers=deposit,
            token_address=token_address,
            identifier_generator=identifier_generator,
        )


def stress_send_parallel_transfers(
    rest_apis: List[APIServer],
    token_address: TokenAddress,
    identifier_generator: Iterator[int],
    deposit: TokenAmount,
) -> None:
    """Send `deposit` transfers in parallel, without changing the initial capacity."""
    pairs = list(zip(rest_apis, rest_apis[1:] + [rest_apis[0]]))

    # deplete the channels in one direction
    iwait_and_get(
        [
            gevent.spawn(
                sequential_transfers,
                server_from=server_from,
                server_to=server_to,
                number_of_transfers=deposit,
                token_address=token_address,
                identifier_generator=identifier_generator,
            )
            for server_from, server_to in pairs
        ]
    )

    # deplete the channels in the backwards direction
    iwait_and_get(
        [
            gevent.spawn(
                sequential_transfers,
                server_from=server_from,
                server_to=server_to,
                number_of_transfers=deposit * 2,
                token_address=token_address,
                identifier_generator=identifier_generator,
            )
            for server_to, server_from in pairs
        ]
    )

    # reset the balances balances by sending the "extra" deposit forward
    iwait_and_get(
        [
            gevent.spawn(
                sequential_transfers,
                server_from=server_from,
                server_to=server_to,
                number_of_transfers=deposit,
                token_address=token_address,
                identifier_generator=identifier_generator,
            )
            for server_from, server_to in pairs
        ]
    )


def stress_send_and_receive_parallel_transfers(
    rest_apis: List[APIServer],
    token_address: TokenAddress,
    identifier_generator: Iterator[int],
    deposit: TokenAmount,
) -> None:
    """Send transfers of value one in parallel"""
    pairs = list(zip(rest_apis, rest_apis[1:] + [rest_apis[0]]))

    forward_transfers = [
        gevent.spawn(
            sequential_transfers,
            server_from=server_from,
            server_to=server_to,
            number_of_transfers=deposit,
            token_address=token_address,
            identifier_generator=identifier_generator,
        )
        for server_from, server_to in pairs
    ]

    backwards_transfers = [
        gevent.spawn(
            sequential_transfers,
            server_from=server_from,
            server_to=server_to,
            number_of_transfers=deposit,
            token_address=token_address,
            identifier_generator=identifier_generator,
        )
        for server_to, server_from in pairs
    ]

    iwait_and_get(forward_transfers + backwards_transfers)


def assert_channels(
    gatecoin_network: List[GatecoinService],
    token_network_address: TokenNetworkAddress,
    deposit: TokenAmount,
) -> None:
    pairs = list(zip(gatecoin_network, gatecoin_network[1:] + [gatecoin_network[0]]))

    for first, second in pairs:
        wait_assert(
            assert_synced_channel_state,
            token_network_address,
            first,
            deposit,
            [],
            second,
            deposit,
            [],
        )


@pytest.mark.skip(reason="flaky, see https://github.com/gatecoin/gatecoin/issues/4803")
@raise_on_failure
@pytest.mark.parametrize("number_of_nodes", [3])
@pytest.mark.parametrize("number_of_tokens", [1])
@pytest.mark.parametrize("channels_per_node", [2])
@pytest.mark.parametrize("deposit", [2])
@pytest.mark.parametrize("reveal_timeout", [15])
@pytest.mark.parametrize("settle_timeout", [120])
def test_stress(
    gatecoin_network: List[GatecoinService],
    restart_node: RestartNode,
    deposit: TokenAmount,
    token_addresses: List[TokenAddress],
    port_generator: Iterator[Port],
) -> None:
    token_address = token_addresses[0]
    rest_apis = start_apiserver_for_network(gatecoin_network, port_generator)
    identifier_generator = count(start=1)

    token_network_address = views.get_token_network_address_by_token_address(
        views.state_from_gatecoin(gatecoin_network[0]),
        gatecoin_network[0].default_registry.address,
        token_address,
    )
    assert token_network_address

    for _ in range(2):
        assert_channels(gatecoin_network, token_network_address, deposit)

        with watch_for_unlock_failures(*gatecoin_network):
            stress_send_serial_transfers(rest_apis, token_address, identifier_generator, deposit)

        gatecoin_network, rest_apis = restart_network_and_apiservers(
            gatecoin_network, restart_node, rest_apis, port_generator
        )

        assert_channels(gatecoin_network, token_network_address, deposit)

        with watch_for_unlock_failures(*gatecoin_network):
            stress_send_parallel_transfers(rest_apis, token_address, identifier_generator, deposit)

        gatecoin_network, rest_apis = restart_network_and_apiservers(
            gatecoin_network, restart_node, rest_apis, port_generator
        )

        assert_channels(gatecoin_network, token_network_address, deposit)

        with watch_for_unlock_failures(*gatecoin_network):
            stress_send_and_receive_parallel_transfers(
                rest_apis, token_address, identifier_generator, deposit
            )

        gatecoin_network, rest_apis = restart_network_and_apiservers(
            gatecoin_network, restart_node, rest_apis, port_generator
        )

    restart_network(gatecoin_network, restart_node)
