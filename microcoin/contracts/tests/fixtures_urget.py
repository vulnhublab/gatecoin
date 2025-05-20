import pytest
from ethereum import tester
from utils import sign
from tests.utils import (
    print_logs,
    balance_proof_hash,
    closing_message_hash
)


@pytest.fixture()
def get_ugatecoin_contract(chain, create_contract, enable_logs):
    def get(arguments, transaction=None):
        GetMicroTransferChannels = chain.provider.get_contract_factory(
            'GetMicroTransferChannels'
        )

        ugatecoin_contract = create_contract(
            GetMicroTransferChannels,
            arguments,
            transaction
        )

        if enable_logs:
            print_logs(ugatecoin_contract, 'ChannelCreated', 'GetMicroTransferChannels')
            print_logs(ugatecoin_contract, 'ChannelToppedUp', 'GetMicroTransferChannels')
            print_logs(ugatecoin_contract, 'ChannelCloseRequested', 'GetMicroTransferChannels')
            print_logs(ugatecoin_contract, 'ChannelSettled', 'GetMicroTransferChannels')
            print_logs(ugatecoin_contract, 'ChannelWithdraw', 'GetMicroTransferChannels')

        return ugatecoin_contract
    return get


@pytest.fixture()
def token_contract(contract_params, get_token_contract):
    def get(transaction=None):
        args = [contract_params['supply'], 'CustomToken', 'TKN', contract_params['decimals']]
        token_contract = get_token_contract(args, transaction)
        return token_contract
    return get


@pytest.fixture()
def token_instance(token_contract):
    return token_contract()


@pytest.fixture()
def delegate_contract(chain, owner, create_contract):
    def get(transaction=None):
        Delegate = chain.provider.get_contract_factory('Delegate')
        delegate_contract = create_contract(Delegate, [], {})
        return delegate_contract
    return get


@pytest.fixture()
def delegate_instance(delegate_contract):
    return delegate_contract()


@pytest.fixture
def ugatecoin_contract(contract_params, token_instance, get_ugatecoin_contract):
    def get(token=None, trusted_contracts=[], transaction=None):
        if not token:
            token = token_instance
        ugatecoin_contract = get_ugatecoin_contract(
            [token.address, contract_params['challenge_period'], trusted_contracts]
        )
        return ugatecoin_contract
    return get


@pytest.fixture
def ugatecoin_instance(owner, ugatecoin_contract, token_instance, delegate_instance):
    ugatecoin_instance = ugatecoin_contract(
        token_instance,
        [delegate_instance.address]
    )
    delegate_instance.transact({'from': owner}).setup(
        token_instance.address,
        ugatecoin_instance.address
    )
    return ugatecoin_instance


@pytest.fixture
def get_channel(channel_params, owner, get_accounts, ugatecoin_instance, token_instance, get_block):
    def get(
        ugatecoin=None,
        token=None,
        deposit=None,
        sender=None,
        receiver=None,
        contract_type=None
    ):
        deposit = deposit or channel_params['deposit']
        contract_type = contract_type or channel_params['type']
        balance = channel_params['balance']
        ugatecoin = ugatecoin or ugatecoin_instance
        token = token or token_instance

        if not sender:
            (sender, receiver) = get_accounts(2)

        # Supply accounts with tokens
        token.transact({"from": owner}).transfer(sender, deposit + 500)
        token.transact({"from": owner}).transfer(receiver, 100)

        # Create channel (ERC20 or ERC223 logic)
        if contract_type == '20':
            token.transact({"from": sender}).approve(
                ugatecoin.address,
                deposit
            )
            txn_hash = ugatecoin.transact({"from": sender}).createChannel(
                receiver,
                deposit
            )
        else:
            txdata = bytes.fromhex(sender[2:] + receiver[2:])
            txn_hash = token.transact({"from": sender}).transfer(
                ugatecoin.address,
                deposit,
                txdata
            )

        open_block_number = get_block(txn_hash)

        balance_message_hash = balance_proof_hash(
            receiver,
            open_block_number,
            balance,
            ugatecoin_instance.address
        )
        balance_msg_sig, addr = sign.check(balance_message_hash, tester.k2)

        closing_msg_hash = closing_message_hash(
            sender,
            open_block_number,
            balance,
            ugatecoin_instance.address
        )
        closing_sig, addr = sign.check(closing_msg_hash, tester.k3)

        return (sender, receiver, open_block_number, balance_msg_sig, closing_sig)
    return get
