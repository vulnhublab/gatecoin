from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from eth_utils import to_canonical_address

from gatecoin.constants import Environment, RoutingMode
from gatecoin.exceptions import GatecoinError
from gatecoin.network import pathfinding
from gatecoin.network.pathfinding import PFSInfo
from gatecoin.settings import GatecoinConfig, ServiceConfig
from gatecoin.tasks import check_chain_id
from gatecoin.tests.utils.factories import make_address
from gatecoin.tests.utils.mocks import MockProxyManager, MockWeb3
from gatecoin.ui.checks import check_ethereum_chain_id
from gatecoin.ui.startup import (
    load_deployed_contracts_data,
    load_deployment_addresses_from_contracts,
    gatecoin_bundle_from_contracts_deployment,
    services_bundle_from_contracts_deployment,
)
from gatecoin.utils.typing import (
    Address,
    BlockNumber,
    BlockTimeout,
    TokenAmount,
    TokenNetworkRegistryAddress,
)
from gatecoin_contracts.constants import (
    CONTRACT_SECRET_REGISTRY,
    CONTRACT_SERVICE_REGISTRY,
    CONTRACT_TOKEN_NETWORK_REGISTRY,
    CONTRACT_USER_DEPOSIT,
)
from gatecoin_contracts.utils.type_aliases import ChainID

token_network_registry_address_test_default = TokenNetworkRegistryAddress(
    to_canonical_address("0xB9633dd9a9a71F22C933bF121d7a22008f66B908")
)
user_deposit_address_test_default = Address(
    to_canonical_address("0x8888888888888888888888888888888888888888")
)

pfs_payment_address_default = to_canonical_address("0xB9633dd9a9a71F22C933bF121d7a22008f66B907")

PFS_INFO = PFSInfo(
    url="my-pfs",
    price=TokenAmount(12),
    chain_id=ChainID(5),
    token_network_registry_address=token_network_registry_address_test_default,
    user_deposit_address=user_deposit_address_test_default,
    payment_address=pfs_payment_address_default,
    confirmed_block_number=BlockNumber(1),
    message="This is your favorite pathfinding service",
    operator="John Doe",
    version="0.0.3",
    matrix_server="http://matrix.example.com",
)


def test_check_chain_id_raises_with_mismatching_ids():
    check_ethereum_chain_id(ChainID(68), MockWeb3(68))

    with pytest.raises(GatecoinError):
        check_ethereum_chain_id(ChainID(61), MockWeb3(68))


def test_check_chain_id_raises_with_connection_error():
    mock_web3 = MockWeb3(61)
    mock_web3.eth.chain_id = MagicMock(side_effect=ConnectionError)
    with pytest.raises(RuntimeError):
        check_chain_id(ChainID(61), mock_web3)


@pytest.mark.parametrize("netid", [1, 3, 4, 5, 627])
def test_setup_does_not_raise_with_matching_ids(netid):
    """Test that network setup works for the known network ids"""
    check_ethereum_chain_id(netid, MockWeb3(netid))


def gatecoin_contracts_in_data(contracts: Dict[str, Any]) -> bool:
    return CONTRACT_SECRET_REGISTRY in contracts and CONTRACT_TOKEN_NETWORK_REGISTRY in contracts


def service_contracts_in_data(contracts: Dict[str, Any]) -> bool:
    return CONTRACT_SERVICE_REGISTRY in contracts and CONTRACT_USER_DEPOSIT in contracts


def test_setup_contracts():
    # Mainnet production: contracts are not deployed
    config = GatecoinConfig(chain_id=1, environment_type=Environment.PRODUCTION)
    contracts = load_deployed_contracts_data(config, 1)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Mainnet development -- NOT allowed
    config = GatecoinConfig(chain_id=1, environment_type=Environment.DEVELOPMENT)
    with pytest.raises(GatecoinError):
        contracts = load_deployed_contracts_data(config, 1)

    # Ropsten production
    config = GatecoinConfig(chain_id=3, environment_type=Environment.PRODUCTION)
    contracts = load_deployed_contracts_data(config, 3)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Ropsten development
    config = GatecoinConfig(chain_id=3, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, 3)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Rinkeby production
    config = GatecoinConfig(chain_id=4, environment_type=Environment.PRODUCTION)
    contracts = load_deployed_contracts_data(config, 4)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Rinkeby development
    config = GatecoinConfig(chain_id=4, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, 4)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Goerli production
    config = GatecoinConfig(chain_id=5, environment_type=Environment.PRODUCTION)
    contracts = load_deployed_contracts_data(config, 5)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # Goerli development
    config = GatecoinConfig(chain_id=5, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, 5)
    assert config.contracts_path is not None
    assert gatecoin_contracts_in_data(contracts)
    assert service_contracts_in_data(contracts)

    # random private network production
    config = GatecoinConfig(chain_id=5257, environment_type=Environment.PRODUCTION)
    contracts = load_deployed_contracts_data(config, 5257)
    assert config.contracts_path is not None
    assert not gatecoin_contracts_in_data(contracts)
    assert not service_contracts_in_data(contracts)

    # random private network development
    config = GatecoinConfig(chain_id=5257, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, 5257)
    assert config.contracts_path is not None
    assert not gatecoin_contracts_in_data(contracts)
    assert not service_contracts_in_data(contracts)


def test_setup_proxies_gatecoin_addresses_are_given():
    """
    Test that startup for proxies works fine if only gatecoin addresses are given
    """
    chain_id = ChainID(5)
    config = GatecoinConfig(chain_id=chain_id, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, chain_id)
    proxy_manager = MockProxyManager(node_address=make_address())

    deployed_addresses = load_deployment_addresses_from_contracts(contracts)
    gatecoin_bundle = gatecoin_bundle_from_contracts_deployment(
        proxy_manager=proxy_manager,
        token_network_registry_address=deployed_addresses.token_network_registry_address,
        secret_registry_address=deployed_addresses.secret_registry_address,
    )
    services_bundle = services_bundle_from_contracts_deployment(
        config=config,
        proxy_manager=proxy_manager,
        deployed_addresses=deployed_addresses,
        routing_mode=RoutingMode.PRIVATE,
        pathfinding_service_address=None,
        enable_monitoring=False,
    )
    assert gatecoin_bundle
    assert services_bundle
    assert gatecoin_bundle.token_network_registry
    assert gatecoin_bundle.secret_registry
    assert services_bundle.user_deposit
    assert not services_bundle.service_registry


def test_setup_proxies_all_addresses_are_given():
    """
    Test that startup for proxies works fine if all addresses are given and routing is private
    """
    chain_id = ChainID(5)
    config = GatecoinConfig(chain_id=chain_id, environment_type=Environment.DEVELOPMENT)
    contracts = load_deployed_contracts_data(config, chain_id)
    proxy_manager = MockProxyManager(node_address=make_address())

    deployed_addresses = load_deployment_addresses_from_contracts(contracts)
    with patch.object(pathfinding, "get_pfs_info", return_value=PFS_INFO):
        gatecoin_bundle = gatecoin_bundle_from_contracts_deployment(
            proxy_manager=proxy_manager,
            token_network_registry_address=deployed_addresses.token_network_registry_address,
            secret_registry_address=deployed_addresses.secret_registry_address,
        )
        services_bundle = services_bundle_from_contracts_deployment(
            config=config,
            proxy_manager=proxy_manager,
            deployed_addresses=deployed_addresses,
            routing_mode=RoutingMode.PRIVATE,
            pathfinding_service_address="my-pfs",
            enable_monitoring=True,
        )
    assert gatecoin_bundle
    assert services_bundle
    assert gatecoin_bundle.token_network_registry
    assert gatecoin_bundle.secret_registry
    assert services_bundle.user_deposit
    assert not services_bundle.service_registry


def test_setup_proxies_all_addresses_are_known():
    """
    Test that startup for proxies works fine if all addresses are given and routing is basic
    """
    chain_id = ChainID(5)
    config = GatecoinConfig(chain_id=chain_id, environment_type=Environment.DEVELOPMENT)
    config.transport.available_servers = ["http://matrix.example.com"]
    contracts = load_deployed_contracts_data(config, chain_id)
    proxy_manager = MockProxyManager(node_address=make_address())
    PFS_INFO = PFSInfo(
        url="my-pfs",
        price=TokenAmount(12),
        chain_id=ChainID(5),
        token_network_registry_address=to_canonical_address(
            contracts[CONTRACT_TOKEN_NETWORK_REGISTRY]["address"]
        ),
        user_deposit_address=user_deposit_address_test_default,
        payment_address=pfs_payment_address_default,
        confirmed_block_number=BlockNumber(1),
        message="This is your favorite pathfinding service",
        operator="John Doe",
        version="0.0.3",
        matrix_server="http://matrix.example.com",
    )
    deployed_addresses = load_deployment_addresses_from_contracts(contracts)
    with patch.object(pathfinding, "get_pfs_info", return_value=PFS_INFO):
        gatecoin_bundle = gatecoin_bundle_from_contracts_deployment(
            proxy_manager=proxy_manager,
            token_network_registry_address=deployed_addresses.token_network_registry_address,
            secret_registry_address=deployed_addresses.secret_registry_address,
        )
        services_bundle = services_bundle_from_contracts_deployment(
            config=config,
            proxy_manager=proxy_manager,
            deployed_addresses=deployed_addresses,
            routing_mode=RoutingMode.PFS,
            pathfinding_service_address="my-pfs",
            enable_monitoring=False,
        )
    assert gatecoin_bundle
    assert services_bundle
    assert gatecoin_bundle.token_network_registry
    assert gatecoin_bundle.secret_registry
    assert services_bundle.user_deposit
    assert services_bundle.service_registry


def test_setup_proxies_no_service_registry_but_pfs() -> None:
    """
    Test that if no service registry is provided but a manual pfs address is given then startup
    still works

    Regression test for https://github.com/gatecoin/gatecoin/issues/3740
    """
    chain_id = ChainID(5)
    config = GatecoinConfig(
        chain_id=chain_id,
        environment_type=Environment.DEVELOPMENT,
        services=ServiceConfig(
            pathfinding_max_fee=TokenAmount(100),
            pathfinding_iou_timeout=BlockTimeout(500),
            pathfinding_max_paths=5,
        ),
    )
    config.transport.available_servers = ["http://matrix.example.com"]
    contracts = load_deployed_contracts_data(config, chain_id)
    proxy_manager = MockProxyManager(node_address=make_address())

    PFS_INFO = PFSInfo(
        url="my-pfs",
        price=TokenAmount(12),
        chain_id=ChainID(5),
        token_network_registry_address=TokenNetworkRegistryAddress(
            to_canonical_address(contracts[CONTRACT_TOKEN_NETWORK_REGISTRY]["address"])
        ),
        user_deposit_address=user_deposit_address_test_default,
        confirmed_block_number=BlockNumber(1),
        payment_address=pfs_payment_address_default,
        message="This is your favorite pathfinding service",
        operator="John Doe",
        version="0.0.3",
        matrix_server="http://matrix.example.com",
    )
    deployed_addresses = load_deployment_addresses_from_contracts(contracts)
    with patch.object(pathfinding, "get_pfs_info", return_value=PFS_INFO):
        services_bundle = services_bundle_from_contracts_deployment(
            config=config,
            proxy_manager=proxy_manager,  # type: ignore
            deployed_addresses=deployed_addresses,
            routing_mode=RoutingMode.PFS,
            pathfinding_service_address="my-pfs",
            enable_monitoring=True,
        )
    assert services_bundle


@pytest.mark.parametrize("environment_type", [Environment.DEVELOPMENT, Environment.PRODUCTION])
def test_setup_proxies_no_service_registry_and_no_pfs_address_but_requesting_pfs(environment_type):
    """
    Test that if pfs routing mode is requested and no address or service registry is given
    then the client exits with an error message
    """

    chain_id = ChainID(5)
    config = GatecoinConfig(
        chain_id=chain_id,
        environment_type=environment_type,
        services=ServiceConfig(
            pathfinding_max_fee=100, pathfinding_iou_timeout=500, pathfinding_max_paths=5
        ),
    )
    contracts = load_deployed_contracts_data(config, chain_id)
    proxy_manager = MockProxyManager(node_address=make_address())

    with pytest.raises(GatecoinError):
        deployed_addresses = load_deployment_addresses_from_contracts(contracts)
        with patch.object(pathfinding, "get_pfs_info", return_value=PFS_INFO):
            services_bundle_from_contracts_deployment(
                config=config,
                proxy_manager=proxy_manager,
                deployed_addresses=deployed_addresses,
                routing_mode=RoutingMode.PFS,
                pathfinding_service_address=None,
                enable_monitoring=False,
            )
