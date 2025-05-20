import pytest
from ethereum import tester
from tests.constants import (
    CHALLENGE_PERIOD_MIN,
    FAKE_ADDRESS,
    EMPTY_ADDRESS,
    UGATECOIN_EVENTS,
)
from tests.utils import (
    checkTrustedEvent,
)


def test_trusted_contracts_constructor(
        owner,
        get_accounts,
        get_ugatecoin_contract,
        ugatecoin_contract,
        token_instance,
        delegate_contract,
        contract_params,
):
    trusted_contract = delegate_contract()
    trusted_contract2 = delegate_contract()
    other_contract = delegate_contract()
    simple_account = get_accounts(1)[0]
    ugatecoin = ugatecoin_contract(token_instance, [trusted_contract.address])

    assert ugatecoin.call().trusted_contracts(trusted_contract.address)
    assert not ugatecoin.call().trusted_contracts(other_contract.address)

    with pytest.raises(TypeError):
        get_ugatecoin_contract([token_instance.address, CHALLENGE_PERIOD_MIN])
    with pytest.raises(TypeError):
        get_ugatecoin_contract([token_instance.address, CHALLENGE_PERIOD_MIN, [FAKE_ADDRESS]])

    ugatecoin2 = get_ugatecoin_contract([
        token_instance.address,
        CHALLENGE_PERIOD_MIN,
        [trusted_contract2.address, EMPTY_ADDRESS, simple_account]
    ])
    assert ugatecoin2.call().trusted_contracts(trusted_contract2.address)
    assert not ugatecoin2.call().trusted_contracts(EMPTY_ADDRESS)
    assert not ugatecoin2.call().trusted_contracts(simple_account)


def test_add_trusted_contracts_call(owner, get_accounts, ugatecoin_instance, delegate_contract):
    (A, B) = get_accounts(2)

    with pytest.raises(TypeError):
        ugatecoin_instance.transact({'from': owner}).addTrustedContracts([FAKE_ADDRESS])

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([])
    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([EMPTY_ADDRESS])


def test_add_trusted_contracts_only_owner(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract
):
    (A, B) = get_accounts(2)
    trusted_contract = delegate_contract()

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({'from': A}).addTrustedContracts([trusted_contract.address])

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([trusted_contract.address])
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract.address)


def test_add_trusted_contracts_state(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract,
        print_gas
):
    (A, B) = get_accounts(2)
    trusted_contract1 = delegate_contract()
    trusted_contract2 = delegate_contract()
    trusted_contract3 = delegate_contract()
    trusted_contract4 = delegate_contract()

    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract1.address)
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract2.address)
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract3.address)
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract4.address)

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([A])
    assert not ugatecoin_instance.call().trusted_contracts(A)

    txn_hash = ugatecoin_instance.transact(
        {'from': owner}
    ).addTrustedContracts([trusted_contract1.address])
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract1.address)

    print_gas(txn_hash, 'add 1 trusted contract')

    txn_hash = ugatecoin_instance.transact({'from': owner}).addTrustedContracts([
        trusted_contract2.address,
        trusted_contract3.address,
        A,
        trusted_contract4.address
    ])
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract2.address)
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract3.address)
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract4.address)
    assert not ugatecoin_instance.call().trusted_contracts(A)

    print_gas(txn_hash, 'add 3 trusted contracts')


def test_add_trusted_contracts_event(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract,
        event_handler
):
    (A, B) = get_accounts(2)
    ev_handler = event_handler(ugatecoin_instance)
    trusted_contract = delegate_contract()

    txn_hash = ugatecoin_instance.transact({'from': owner}).addTrustedContracts(
        [trusted_contract.address]
    )

    ev_handler.add(
        txn_hash,
        UGATECOIN_EVENTS['trusted'],
        checkTrustedEvent(trusted_contract.address, True)
    )
    ev_handler.check()


def test_remove_trusted_contracts_call(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract
):
    (A, B) = get_accounts(2)
    trusted_contract1 = delegate_contract()
    trusted_contract2 = delegate_contract()

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts(
        [trusted_contract1.address, trusted_contract2.address]
    )

    with pytest.raises(TypeError):
        ugatecoin_instance.transact({'from': owner}).removeTrustedContracts([FAKE_ADDRESS])

    ugatecoin_instance.transact({'from': owner}).removeTrustedContracts([])
    ugatecoin_instance.transact({'from': owner}).removeTrustedContracts(
        [EMPTY_ADDRESS, trusted_contract1.address]
    )


def test_remove_trusted_contracts_only_owner(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract
):
    (A, B) = get_accounts(2)
    trusted_contract = delegate_contract()

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([trusted_contract.address])
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract.address)

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({'from': A}).removeTrustedContracts([trusted_contract.address])

    ugatecoin_instance.transact({'from': owner}).removeTrustedContracts(
        [trusted_contract.address]
    )
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract.address)


def test_remove_trusted_contracts_state(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract,
        print_gas
):
    (A, B) = get_accounts(2)
    trusted_contract1 = delegate_contract()
    trusted_contract2 = delegate_contract()
    trusted_contract3 = delegate_contract()

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts([
        trusted_contract1.address,
        trusted_contract2.address,
        trusted_contract3.address
    ])

    assert ugatecoin_instance.call().trusted_contracts(trusted_contract1.address)
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract2.address)
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract3.address)

    txn_hash = ugatecoin_instance.transact({'from': owner}).removeTrustedContracts([
        trusted_contract1.address,
        trusted_contract2.address,
        A
    ])
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract1.address)
    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract2.address)
    assert ugatecoin_instance.call().trusted_contracts(trusted_contract3.address)

    print_gas(txn_hash, 'remove 3 trusted contracts')

    txn_hash = ugatecoin_instance.transact({'from': owner}).removeTrustedContracts([
        trusted_contract3.address
    ])

    assert not ugatecoin_instance.call().trusted_contracts(trusted_contract3.address)

    print_gas(txn_hash, 'remove 1 trusted contract')


def test_remove_trusted_contracts_event(
        owner,
        get_accounts,
        ugatecoin_instance,
        delegate_contract,
        event_handler
):
    (A, B) = get_accounts(2)
    ev_handler = event_handler(ugatecoin_instance)
    trusted_contract1 = delegate_contract()
    trusted_contract2 = delegate_contract()

    ugatecoin_instance.transact({'from': owner}).addTrustedContracts(
        [trusted_contract1.address, trusted_contract2.address]
    )

    txn_hash = ugatecoin_instance.transact({'from': owner}).removeTrustedContracts(
        [trusted_contract1.address]
    )

    ev_handler.add(
        txn_hash,
        UGATECOIN_EVENTS['trusted'],
        checkTrustedEvent(trusted_contract1.address, False)
    )
    ev_handler.check()
