import pytest

from gatecoin.constants import Environment
from gatecoin.settings import GATECOIN_CONTRACT_VERSION
from gatecoin.tests.integration.cli.util import (
    expect_cli_normal_startup,
    expect_cli_successful_connected,
    expect_cli_until_account_selection,
)

pytestmark = [
    pytest.mark.parametrize(
        "cli_tests_contracts_version", [GATECOIN_CONTRACT_VERSION], scope="module"
    ),
    pytest.mark.parametrize("environment_type", [Environment.DEVELOPMENT], scope="module"),
]


def test_cli_full_init_dev(cli_args, gatecoin_spawner):
    child = gatecoin_spawner(cli_args)
    expect_cli_normal_startup(child, Environment.DEVELOPMENT.value)


@pytest.mark.parametrize("removed_args", [["address"]])
def test_cli_manual_account_selection(cli_args, gatecoin_spawner):
    child = gatecoin_spawner(cli_args)
    expect_cli_until_account_selection(child)
    expect_cli_successful_connected(child, Environment.DEVELOPMENT.value)
