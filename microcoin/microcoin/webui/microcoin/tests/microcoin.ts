import 'mocha';
import { expect, use } from 'chai';
import * as chaiAsPromised from 'chai-as-promised';

import * as fs from 'fs';
import * as path from 'path';

import * as Web3 from 'web3';
import BigNumber from 'bignumber.js';
import * as ganache from 'ganache-cli';
import * as tempo from '@digix/tempo';
import { signTypedData, recoverTypedSignature } from 'eth-sig-util';
import { privateToAddress, bufferToHex, toBuffer } from 'ethereumjs-util';

import { MicroCoin, promisify, asyncSleep, encodeHex } from '../src';

use(chaiAsPromised);

const readFileAsync = promisify<Buffer>(fs, 'readFile');
const addr_re = /^0x[0-9A-Fa-f]{40}$/;

const TOKEN = 'CustomToken';
const CHANNEL_MANAGER = 'GetMicroTransferChannels';
const TOKEN_SUPLY = 1e25;
const DECIMALS = 18;
const CHALLENGE_PERIOD = 500;

describe('MicroCoin', () => {
  // initialization
  let accountsKeys: { secretKey: string, balance: string }[] = [
    { secretKey: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', balance: '0x56bc75e2d63100000' },
    { secretKey: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', balance: '0x56bc75e2d63100000' },
    { secretKey: '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', balance: '0x56bc75e2d63100000' },
  ];
  let accounts: string[];

  const web3 = new Web3(ganache.provider({
    blockTime: 1,
    seed: '1337',
    accounts: accountsKeys,
  }));
  let ugatecoin: MicroCoin;
  let sender: string, receiver: string, block: number;
  const { wait, waitUntilBlock } = tempo(web3);
  let snapId, snapChannel;

  // mock/extend web3 instance
  web3._extend({
    property: 'evm',
    methods: [
      new web3._extend.Method({
        name: 'mine',
        call: 'evm_mine',
        params: 0
      }),
      new web3._extend.Method({
        name: 'snapshot',
        call: 'evm_snapshot',
        params: 0,
        outputFormatter: web3._extend.utils.toDecimal
      }),
      new web3._extend.Method({
        name: 'revert',
        call: 'evm_revert',
        params: 1,
        inputFormatter: [web3._extend.utils.fromDecimal]
      }),
      new web3._extend.Method({
        name: 'increaseTime',
        call: 'evm_increaseTime',
        params: 1,
        inputFormatter: [web3._extend.utils.fromDecimal]
      }),
    ]
  });

  // having private keys on testrpc, wrap provider' sendAsync to implement eth_signTypedData
  const origSendAsync = web3.currentProvider.sendAsync;
  web3.currentProvider.sendAsync = function(payload, callback) {
    let args = [].slice.call(arguments, 0);
    if (payload['method'] === 'eth_signTypedData') {
      try {
        const [ params, account ] = payload['params'];
        const pk = accountsKeys.filter((k) => bufferToHex(privateToAddress(k.secretKey)) === account)[0].secretKey;
        const sig = signTypedData(toBuffer(pk), { data: params });
        return callback(null, { result: sig, error: null });
      } catch(err) {
        return callback({ result: null, error: err });
      }
    } else {
      return origSendAsync.apply(this, args);
    }
  }

  // deploy contracts and init ugatecoin
  before(async () => {
    const contracts = JSON.parse((await readFileAsync(path.join(__dirname, 'contracts.json'))).toString());
    accounts = await promisify<string[]>(web3.eth, 'getAccounts')();
    sender = accounts[0];
    receiver = accounts[1];

    // deploy token contract with last account
    const Token = web3.eth.contract(contracts[TOKEN]['abi']);
    let token = await new Promise<Web3.ContractInstance>((resolve, reject) =>
      Token.new(
        TOKEN_SUPLY,
        TOKEN,
        'TKN',
        DECIMALS,
        {
          gas: 5e6,
          from: accounts[accounts.length-1],
          data: contracts[TOKEN]['bytecode'],
        },
        (err, contract) => {
          if (err)
            return reject(err);
          else if (contract.address)
            return resolve(contract);
        }
      )
    );

    // mint 50 tkns to sender and receiver
    for (let acc of [sender, receiver]) {
      promisify<string>(token.mint, 'sendTransaction')({
        from: acc,
        value: web3.toWei(0.1, 'ether'),
      });
    }

    // deploy channel manager contract with last account and token
    const ChannelManager = web3.eth.contract(contracts[CHANNEL_MANAGER]['abi']);
    let channel_manager = await new Promise<Web3.ContractInstance>((resolve, reject) =>
      ChannelManager.new(
        token.address,
        CHALLENGE_PERIOD,
        [],
        {
          gas: 5e6,
          from: accounts[accounts.length-1],
          data: contracts[CHANNEL_MANAGER]['bytecode'],
        },
        (err, contract) => {
          if (err)
            return reject(err);
          else if (contract.address)
            return resolve(contract);
        }
      )
    );

    expect(token.address).to.match(addr_re);
    expect(channel_manager.address).to.match(addr_re);

    // init ugatecoin
    ugatecoin = new MicroCoin(
      web3,
      channel_manager.address,
      channel_manager.abi,
      token.address,
      token.abi,
    );
  });

  it('#getAccounts()', async () => {
    expect(ugatecoin.getAccounts()).to.eventually.have.members(accounts);
  });

  it('#getChallengePeriod()', async () => {
    expect(ugatecoin.getChallengePeriod()).to.eventually.be.equal(CHALLENGE_PERIOD);
  });

  it('#getTokenInfo(account)', async () => {
    // test 2 first accounts: sender, receiver to have 50tkns
    for (let i = 0; i<2; ++i) {
      const acc = accounts[i];
      const result = await ugatecoin.getTokenInfo(acc);
      expect(result).to.have.all.keys('name', 'symbol', 'decimals', 'balance')
      expect(result).to.include({
        name: TOKEN,
        symbol: 'TKN',
        decimals: DECIMALS,
      });
      expect(result.balance.eq(web3.toBigNumber(50).shift(DECIMALS))).to.be.true;
    }
  });

  it('#num2tkn(num)', () => {
    expect(ugatecoin.num2tkn(50).eq(web3.toBigNumber(50).shift(DECIMALS))).to.be.true;
  });

  it('#tkn2num(bal)', () => {
    expect(ugatecoin.tkn2num(web3.toBigNumber(50).shift(DECIMALS))).to.be.equal(50);
  });

  it('#isChannelValid() false', () => {
    expect(ugatecoin.isChannelValid()).to.be.false;
  });

  it('#getChannelInfo() invalid', async () => {
    await expect(ugatecoin.getChannelInfo()).to.be.rejectedWith('No valid');
  });

  it('#openChannel(sender, receiver, deposit)', async () => {
    const result = await ugatecoin.openChannel(sender, receiver, ugatecoin.num2tkn(10));
    expect(result).to.have.all.keys('account', 'receiver', 'block', 'proof');
    expect(result).to.include({
      account: sender,
      receiver
    });
    expect(result.block).to.be.a('number');
    block = result.block;
  });

  it('#isChannelValid() true', async () => {
    expect(ugatecoin.isChannelValid()).to.be.true;
  });

  it('#getChannelInfo() valid', async () => {
    const result = await ugatecoin.getChannelInfo();
    expect(result).to.have.all.keys('state', 'block', 'deposit', 'withdrawn');
    expect(result).to.include({ state: 'opened', block });
    expect(result.deposit.eq(ugatecoin.num2tkn(10))).to.be.true;
  });

  it('#setBalance(value)', () => {
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(0))).to.be.true;
    expect(ugatecoin.channel.proof.sig).to.not.exist;
    expect(ugatecoin.channel.next_proof).to.not.exist;

    ugatecoin.setBalance(ugatecoin.num2tkn(2));

    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(2))).to.be.true;
    expect(ugatecoin.channel.proof.sig).to.not.exist;
    expect(ugatecoin.channel.next_proof).to.not.exist;
  });

  it('#forgetStoredChannel()', () => {
    expect(ugatecoin.isChannelValid()).to.be.true;
    ugatecoin.forgetStoredChannel();
    expect(ugatecoin.isChannelValid()).to.be.false;
  });

  it('#loadChannelFromBlockchain(sender, receiver)', async () => {
    expect(ugatecoin.isChannelValid()).to.be.false;
    const result = await ugatecoin.loadChannelFromBlockchain(sender, receiver);
    expect(ugatecoin.isChannelValid()).to.be.true;
    expect(result.block).to.be.equal(block);

    const info = await ugatecoin.getChannelInfo();
    expect(info.deposit.eq(ugatecoin.num2tkn(10))).to.be.true;
  });

  it('#topUpChannel(deposit)', async () => {
    let info = await ugatecoin.getChannelInfo();
    expect(info.deposit.eq(ugatecoin.num2tkn(10))).to.be.true;

    const topUpTxHash = await ugatecoin.topUpChannel(ugatecoin.num2tkn(5));
    const topUpTx = await promisify<Web3.TransactionReceipt>(web3.eth, 'getTransactionReceipt')(topUpTxHash);
    const topUpBlock = topUpTx.blockNumber;
    expect(topUpBlock).to.be.above(block);
    info = await ugatecoin.getChannelInfo();
    expect(info.deposit.eq(ugatecoin.num2tkn(15))).to.be.true;

    const tokenInfo = await ugatecoin.getTokenInfo(sender);
    expect(tokenInfo.balance.eq(ugatecoin.num2tkn(35))).to.be.true;

    // save channel state: deposit=15, balance=0
    snapId = await promisify<number>(web3.evm, 'snapshot')();
    snapChannel = Object.assign({}, ugatecoin.channel);
  });

  it('#incrementBalanceAndSign() + #confirmPayment(proof) + #verifyProof(proof)', async () => {
    expect(ugatecoin.channel.next_proof).to.not.exist;

    let result = await ugatecoin.incrementBalanceAndSign(ugatecoin.num2tkn(1));
    expect(result).to.have.all.keys('balance', 'sig');
    expect(result.balance.eq(ugatecoin.num2tkn(1))).to.be.true;
    expect(result.sig).to.be.a('string');

    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(0))).to.be.true;
    expect(ugatecoin.channel.next_proof).to.be.an('object').and.have.all.keys('balance', 'sig');
    expect(ugatecoin.channel.next_proof.balance.eq(ugatecoin.num2tkn(1))).to.be.true;

    ugatecoin.confirmPayment(result);
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(1))).to.be.true;
    expect(ugatecoin.channel.next_proof).to.not.exist;

    result = await ugatecoin.incrementBalanceAndSign(ugatecoin.num2tkn(6));
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(1))).to.be.true;
    expect(result).to.have.all.keys('balance', 'sig');
    expect(result.balance.eq(ugatecoin.num2tkn(7))).to.be.true;
    expect(result.sig).to.be.a('string');
    expect(ugatecoin.verifyProof(result)).to.be.true;
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(7))).to.be.true;
  });

  it('#closeChannel() cooperative + #setChannel(channel)', async () => {
    // use previous test incremented value
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(7))).to.be.true;

    // closing signature parameters
    let params = [
      {
        type: 'string',
        name: 'message_id',
        value: 'Receiver closing signature',
      },
      {
        type: 'address',
        name: 'sender',
        value: sender,
      },
      {
        type: 'uint32',
        name: 'block_created',
        value: '' + ugatecoin.channel.block,
      },
      {
        type: 'uint192',
        name: 'balance',
        value: ugatecoin.channel.proof.balance.toString(),
      },
      {
        type: 'address',
        name: 'contract',
        value: ugatecoin.contract.address,
      },
    ];
    let sig = await promisify<{ result: string, error: Error }>(
      web3.currentProvider, 'sendAsync'
    )({
      method: 'eth_signTypedData',
      params: [params, receiver],
      from: receiver
    });
    if (sig.error)
      throw sig.error;
    const closingSig = sig.result;
    expect(recoverTypedSignature({ data: params, sig: closingSig })).to.be.equal(receiver);

    const closingTxHash = await ugatecoin.closeChannel(closingSig);
    const closingTx = await promisify<Web3.TransactionReceipt>(web3.eth, 'getTransactionReceipt')(closingTxHash);
    const closingBlock = closingTx.blockNumber;
    expect(closingBlock).to.be.above(block);

    let result = await ugatecoin.getChannelInfo();
    expect(result).to.have.all.keys('state', 'block', 'deposit', 'withdrawn');
    expect(result.state).to.be.equal('settled');
    expect(result.deposit.eq(ugatecoin.num2tkn(0))).to.be.true;

    let tokenInfo = await ugatecoin.getTokenInfo(sender);
    expect(tokenInfo.balance.eq(ugatecoin.num2tkn(43))).to.be.true;
    tokenInfo = await ugatecoin.getTokenInfo(receiver);
    expect(tokenInfo.balance.eq(ugatecoin.num2tkn(57))).to.be.true;

    // revert channel/blockchain state, use setChannel to set channel data
    await promisify<void>(web3.evm, 'revert')(snapId);
    snapId = await promisify<number>(web3.evm, 'snapshot')();
    ugatecoin.setChannel(Object.assign({}, snapChannel));
  });

  // skipping this test because of https://github.com/ethereumjs/ethereumjs-vm/issues/81
  it.skip('#closeChannel() uncooperative + #settleChannel()', async () => {
    // arbitrarily set balance to 4 with setBalance
    ugatecoin.setBalance(ugatecoin.num2tkn(4));

    let result = await ugatecoin.getChannelInfo();
    expect(result).to.have.all.keys('state', 'block', 'deposit', 'withdrawn');
    expect(result).to.include({ state: 'opened', block });
    expect(result.deposit.eq(ugatecoin.num2tkn(15))).to.be.true;
    expect(ugatecoin.channel.proof.balance.eq(ugatecoin.num2tkn(4))).to.be.true;

    const closingTxHash = await ugatecoin.closeChannel();
    const closingTx = await promisify<Web3.TransactionReceipt>(web3.eth, 'getTransactionReceipt')(closingTxHash);

    result = await ugatecoin.getChannelInfo();
    const closingBlock = result.block;
    expect(closingBlock).to.be.equal(closingTx.blockNumber);
    expect(closingBlock).to.be.above(block);
    expect(result).to.have.all.keys('state', 'block', 'deposit', 'withdrawn');
    expect(result.state).to.be.equal('closed');
    expect(result.deposit.eq(ugatecoin.num2tkn(15))).to.be.true;

    await expect(ugatecoin.settleChannel()).to.be.rejectedWith('Tried settling inside challenge period');

    await wait(20, CHALLENGE_PERIOD); // mine/wait CHALLENGE_PERIOD blocks
    const settleTxHash = await ugatecoin.settleChannel();
    const settleTx = await promisify<Web3.TransactionReceipt>(web3.eth, 'getTransactionReceipt')(settleTxHash);
    expect(settleTx.blockNumber).to.be.at.least(result.block + CHALLENGE_PERIOD);

    result = await ugatecoin.getChannelInfo();
    const settledBlock = result.block;
    expect(result).to.have.all.keys('state', 'block', 'deposit', 'withdrawn');
    expect(result.state).to.be.equal('settled');
    expect(settledBlock).to.be.above(closingBlock);
    expect(result.deposit.eq(ugatecoin.num2tkn(0))).to.be.true;

    // uncooperative close: balance = 0
    let tokenInfo = await ugatecoin.getTokenInfo(sender);
    expect(tokenInfo.balance.eq(ugatecoin.num2tkn(46))).to.be.true;
    tokenInfo = await ugatecoin.getTokenInfo(receiver);
    expect(tokenInfo.balance.eq(ugatecoin.num2tkn(54))).to.be.true;

    // revert channel/blockchain state
    await promisify<void>(web3.evm, 'revert')(snapId);
    snapId = await promisify<number>(web3.evm, 'snapshot')();
    ugatecoin.setChannel(Object.assign({}, snapChannel));
  });

});
