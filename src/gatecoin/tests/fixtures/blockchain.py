from pathlib import Path

import pytest

from gatecoin.settings import GATECOIN_CONTRACT_VERSION
from gatecoin_contracts.contract_manager import ContractManager, contracts_precompiled_path

__all__ = ("contracts_path", "contract_manager")


@pytest.fixture
def contracts_path() -> Path:
    version = GATECOIN_CONTRACT_VERSION
    return contracts_precompiled_path(version)


@pytest.fixture
def contract_manager(contracts_path):
    return ContractManager(contracts_path)
