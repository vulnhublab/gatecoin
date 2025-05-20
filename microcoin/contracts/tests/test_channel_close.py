import pytest
from ethereum import tester
from utils import sign
from tests.utils import balance_proof_hash, closing_message_hash
from eth_utils import encode_hex, is_same_address
from tests.constants import (
    FAKE_ADDRESS,
    MAX_UINT256,
    MAX_UINT32,
    UGATECOIN_EVENTS,
)
from tests.utils import (
    checkClosedEvent,
    checkSettledEvent,
    channel_settle_tests,
)


def test_uncooperative_close_call(channel_params, ugatecoin_instance, get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            0x0,
            open_block_number,
            balance
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            FAKE_ADDRESS,
            open_block_number,
            balance
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            -2,
            balance
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            MAX_UINT32 + 1,
            balance
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number,
            -2
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number,
            MAX_UINT256 + 1
        )

    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )


def test_uncooperative_close_fail_no_channel(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel):
    A = get_accounts(1, 5)[0]
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    # Should fail if called by anyone else than the sender
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": receiver}).uncooperativeClose(
            receiver,
            open_block_number,
            balance
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": A}).uncooperativeClose(
            receiver,
            open_block_number,
            balance
        )

    # Should fail if the channel does not exist
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            A,
            open_block_number,
            balance
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number - 1,
            balance
        )

    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )


def test_uncooperative_close_fail_big_balance(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        token_instance,
        get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    deposit = channel_params['deposit']

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number,
            deposit + 1
        )

    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        deposit
    )


def test_uncooperative_close_fail_in_challenge_period(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        token_instance,
        get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    # Should fail if the channel is already in a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )

    channel_info = ugatecoin_instance.call().getChannelInfo(sender, receiver, open_block_number)
    assert channel_info[2] > 0  # settle_block_number

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number,
            balance
        )


def test_uncooperative_close_fail_uint32_overflow(
        web3,
        channel_params,
        get_ugatecoin_contract,
        token_instance,
        get_channel):
    challenge_period = MAX_UINT32 - 20
    ugatecoin_instance = get_ugatecoin_contract(
        [token_instance.address, challenge_period, []]
    )

    (sender, receiver, open_block_number) = get_channel(ugatecoin_instance)[:3]
    balance = channel_params['balance']

    block_number = web3.eth.getBlock('latest')['number']
    web3.testing.mine(MAX_UINT32 - block_number - challenge_period)
    assert web3.eth.getBlock('latest')['number'] + challenge_period == MAX_UINT32

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
            receiver,
            open_block_number,
            balance
        )


def test_uncooperative_close_uint32_overflow(
        web3,
        channel_params,
        get_ugatecoin_contract,
        token_instance,
        get_channel):
    challenge_period = MAX_UINT32 - 20
    ugatecoin_instance = get_ugatecoin_contract(
        [token_instance.address, challenge_period, []]
    )

    (sender, receiver, open_block_number) = get_channel(ugatecoin_instance)[:3]
    balance = channel_params['balance']

    block_number = web3.eth.getBlock('latest')['number']
    web3.testing.mine(MAX_UINT32 - 1 - block_number - challenge_period)

    assert web3.eth.getBlock('latest')['number'] + challenge_period == MAX_UINT32 - 1

    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )


def test_uncooperative_close_state(
        contract_params,
        channel_params,
        ugatecoin_instance,
        get_channel,
        get_block,
        print_gas):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    txn_hash = ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )

    channel_info = ugatecoin_instance.call().getChannelInfo(sender, receiver, open_block_number)
    # settle_block_number
    assert channel_info[2] == get_block(txn_hash) + contract_params['challenge_period']
    # closing_balance
    assert channel_info[3] == balance

    print_gas(txn_hash, 'uncooperativeClose')


def test_uncooperative_close_event(
        channel_params,
        ugatecoin_instance,
        get_channel,
        event_handler):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    ev_handler = event_handler(ugatecoin_instance)

    txn_hash = ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )

    ev_handler.add(txn_hash, UGATECOIN_EVENTS['closed'], checkClosedEvent(
        sender,
        receiver,
        open_block_number,
        balance)
    )
    ev_handler.check()


def test_cooperative_close_call(channel_params, ugatecoin_instance, get_channel):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            0x0,
            open_block_number,
            balance,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            FAKE_ADDRESS,
            open_block_number,
            balance,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            -2,
            balance,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            MAX_UINT32 + 1,
            balance,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            -2,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            MAX_UINT256 + 1,
            balance_msg_sig,
            closing_sig
        )

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            encode_hex(bytearray()),
            closing_sig
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            balance_msg_sig,
            encode_hex(bytearray())
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            encode_hex(bytearray(64)),
            closing_sig
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            balance_msg_sig,
            encode_hex(bytearray(64))
        )

    ugatecoin_instance.transact({"from": sender}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )


def test_cooperative_close_fail_no_channel(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel):
    A = get_accounts(1, 5)[0]
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    # Should fail if the channel does not exist
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            A,
            open_block_number,
            balance,
            balance_msg_sig,
            closing_sig
        )
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number - 1,
            balance,
            balance_msg_sig,
            closing_sig
        )

    ugatecoin_instance.transact({"from": sender}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )


def test_cooperative_close_fail_wrong_balance(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        token_instance,
        get_channel):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    balance_message_hash_fake = balance_proof_hash(
        receiver,
        open_block_number,
        balance - 1,
        ugatecoin_instance.address
    )
    balance_msg_sig_fake, addr = sign.check(balance_message_hash_fake, tester.k2)

    closing_msg_hash_fake = closing_message_hash(
        sender,
        open_block_number,
        balance - 1,
        ugatecoin_instance.address
    )
    closing_sig_fake, addr = sign.check(closing_msg_hash_fake, tester.k3)

    # Wrong balance as an argument
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance + 1,
            balance_msg_sig,
            closing_sig
        )

    # Sender signs wrong balance
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            balance_msg_sig_fake,
            closing_sig
        )

    # Receiver signs wrong balance
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            balance_msg_sig,
            closing_sig_fake
        )

    ugatecoin_instance.transact({"from": sender}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )


def test_cooperative_close_fail_diff_receiver(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel):
    A = get_accounts(1, 5)[0]
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    balance_message_hash_A = balance_proof_hash(
        A,
        open_block_number,
        balance,
        ugatecoin_instance.address
    )
    balance_msg_sig_A, addr = sign.check(balance_message_hash_A, tester.k2)

    # Should fail if someone tries to use a closing signature from another receiver
    # with the same sender, block, balance
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).cooperativeClose(
            A,
            open_block_number,
            balance,
            balance_msg_sig_A,
            closing_sig
        )


def test_cooperative_close_call_receiver(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel,
        print_gas):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    sender_verified = ugatecoin_instance.call().extractBalanceProofSignature(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig
    )
    assert is_same_address(sender_verified, sender)

    receiver_verified = ugatecoin_instance.call().extractClosingSignature(
        sender,
        open_block_number,
        balance,
        closing_sig
    )
    assert is_same_address(receiver_verified, receiver)

    # Cooperative close can be called by anyone
    txn_hash = ugatecoin_instance.transact({"from": receiver}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )

    print_gas(txn_hash, 'cooperativeClose')


def test_cooperative_close_call_sender(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    sender_verified = ugatecoin_instance.call().extractBalanceProofSignature(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig
    )
    assert is_same_address(sender_verified, sender)

    receiver_verified = ugatecoin_instance.call().extractClosingSignature(
        sender,
        open_block_number,
        balance,
        closing_sig
    )
    assert is_same_address(receiver_verified, receiver)

    # Cooperative close can be called by anyone
    ugatecoin_instance.transact({"from": sender}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )


def test_cooperative_close_call_delegate(
        channel_params,
        get_accounts,
        ugatecoin_instance,
        get_channel):
    A = get_accounts(1, 5)[0]
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    sender_verified = ugatecoin_instance.call().extractBalanceProofSignature(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig
    )
    assert is_same_address(sender_verified, sender)

    receiver_verified = ugatecoin_instance.call().extractClosingSignature(
        sender,
        open_block_number,
        balance,
        closing_sig
    )
    assert is_same_address(receiver_verified, receiver)

    # Cooperative close can be called by anyone
    ugatecoin_instance.transact({"from": A}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )


def test_cooperative_close_state(
        web3,
        contract_params,
        channel_params,
        ugatecoin_instance,
        token_instance,
        get_channel,
        get_block):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']
    deposit = channel_params['deposit']

    # Keep track of pre closing balances
    receiver_pre_balance = token_instance.call().balanceOf(receiver)
    sender_pre_balance = token_instance.call().balanceOf(sender)
    contract_pre_balance = token_instance.call().balanceOf(ugatecoin_instance.address)

    # Cooperative close can be called by anyone
    ugatecoin_instance.transact({"from": receiver}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )

    # Check post closing balances
    receiver_post_balance = receiver_pre_balance + balance
    sender_post_balance = sender_pre_balance + (deposit - balance)
    contract_post_balance = contract_pre_balance - deposit

    assert token_instance.call().balanceOf(receiver) == receiver_post_balance
    assert token_instance.call().balanceOf(sender) == sender_post_balance
    assert token_instance.call().balanceOf(ugatecoin_instance.address) == contract_post_balance

    channel_settle_tests(
        ugatecoin_instance,
        token_instance,
        (sender, receiver, open_block_number),
    )

    # Channel does not exist anymore, so this will fail
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.call().getChannelInfo(sender, receiver, open_block_number)

    web3.testing.mine(30)

    # Cannot be called another time
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": receiver}).cooperativeClose(
            receiver,
            open_block_number,
            balance,
            balance_msg_sig,
            closing_sig
        )


def test_cooperative_close_event(
        channel_params,
        ugatecoin_instance,
        get_channel,
        event_handler):
    (sender, receiver, open_block_number, balance_msg_sig, closing_sig) = get_channel()
    balance = channel_params['balance']

    ev_handler = event_handler(ugatecoin_instance)

    txn_hash = ugatecoin_instance.transact({"from": receiver}).cooperativeClose(
        receiver,
        open_block_number,
        balance,
        balance_msg_sig,
        closing_sig
    )

    ev_handler.add(txn_hash, UGATECOIN_EVENTS['settled'], checkClosedEvent(
        sender,
        receiver,
        open_block_number,
        balance)
    )
    ev_handler.check()


def test_settle_call(
        web3,
        contract_params,
        channel_params,
        ugatecoin_instance,
        token_instance,
        get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    # Trigger a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )
    web3.testing.mine(contract_params['challenge_period'] + 1)

    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).settle(0x0, open_block_number)
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).settle(FAKE_ADDRESS, open_block_number)
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, -2)
    with pytest.raises(TypeError):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, MAX_UINT32 + 1)

    ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)


def test_settle_no_channel(
        web3,
        contract_params,
        channel_params,
        ugatecoin_instance,
        get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    # Trigger a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )
    web3.testing.mine(contract_params['challenge_period'] + 1)

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(sender, open_block_number)
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": receiver}).settle(receiver, open_block_number)
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number + 1)

    ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)


def test_settle_fail_in_challenge(
        web3,
        contract_params,
        channel_params,
        ugatecoin_instance,
        get_channel):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    # Trigger a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )

    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    web3.testing.mine(contract_params['challenge_period'] - 1)
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    web3.testing.mine(1)

    ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)


def test_settle_state(
        web3,
        channel_params,
        contract_params,
        ugatecoin_instance,
        token_instance,
        get_channel,
        print_gas):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']
    deposit = channel_params['deposit']

    # Trigger a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )
    web3.testing.mine(contract_params['challenge_period'] + 1)

    # Keep track of pre closing balances
    receiver_pre_balance = token_instance.call().balanceOf(receiver)
    sender_pre_balance = token_instance.call().balanceOf(sender)
    contract_pre_balance = token_instance.call().balanceOf(ugatecoin_instance.address)

    txn_hash = ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    # Check post closing balances
    receiver_post_balance = receiver_pre_balance + balance
    sender_post_balance = sender_pre_balance + (deposit - balance)
    contract_post_balance = contract_pre_balance - deposit

    assert token_instance.call().balanceOf(receiver) == receiver_post_balance
    assert token_instance.call().balanceOf(sender) == sender_post_balance
    assert token_instance.call().balanceOf(ugatecoin_instance.address) == contract_post_balance

    channel_settle_tests(
        ugatecoin_instance,
        token_instance,
        (sender, receiver, open_block_number),
    )

    # Channel does not exist anymore, so this will fail
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.call().getChannelInfo(sender, receiver, open_block_number)

    web3.testing.mine(30)

    # Cannot be called another time
    with pytest.raises(tester.TransactionFailed):
        ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    print_gas(txn_hash, 'settle')


def test_settle_event(
        web3,
        channel_params,
        contract_params,
        ugatecoin_instance,
        get_channel,
        event_handler):
    (sender, receiver, open_block_number) = get_channel()[:3]
    balance = channel_params['balance']

    ev_handler = event_handler(ugatecoin_instance)

    # Trigger a challenge period
    ugatecoin_instance.transact({"from": sender}).uncooperativeClose(
        receiver,
        open_block_number,
        balance
    )
    web3.testing.mine(contract_params['challenge_period'] + 1)

    txn_hash = ugatecoin_instance.transact({"from": sender}).settle(receiver, open_block_number)

    ev_handler.add(txn_hash, UGATECOIN_EVENTS['settled'], checkSettledEvent(
        sender,
        receiver,
        open_block_number,
        balance,
        balance)
    )
    ev_handler.check()
