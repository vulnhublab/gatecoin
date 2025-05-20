function mainSwitch(id) {
  $(".main_switch"+id).show();
  $(".main_switch:not("+id+")").hide();
  $(".container").show();
}

function pageReady(contractABI, tokenABI, startBlock) {

  // ==== BASIC INITIALIZATION ====

  // you can set this variable in a new 'script' tag, for example
  window.uGatecoinParams = {
    contract: Cookies.get("RDN-Contract-Address"),
    token: Cookies.get("RDN-Token-Address"),
    receiver: Cookies.get("RDN-Receiver-Address"),
    amount: Cookies.get("RDN-Price"),
  };

  window.ugatecoin = new microcoin.MicroCoin(
    window.web3,
    uGatecoinParams.contract,
    contractABI,
    uGatecoinParams.token,
    tokenABI,
    startBlock,
  );

  // ==== MAIN VARIABLES ====

  var $accounts = $("#accounts");
  var autoSign = false;

  // ==== FUNCTIONS ====

  function errorDialog(text, err) {
    var msg = err && err.message ?
      err.message.split(/\r?\n/)[0] :
      typeof err === "string" ?
        err.split(/\r?\n/)[0] :
        JSON.stringify(err);
    return window.alert(text+ ':\n' + msg);
  }

  function refreshAccounts(_autoSign) {

    autoSign = !!_autoSign;

    $accounts.empty();
    // use challenge period to assert configured channel
    // is valid in current provider's network
    ugatecoin.getChallengePeriod()
      .then(function() { return ugatecoin.getAccounts(); })
      .then(function(accounts) {
        if (!accounts || !accounts.length) {
          throw new Error('No account');
        }
        mainSwitch("#channel_loading");
        $.each(accounts, function(k,v) {
          var o = $("<option></option>").attr("value", v).text(v);
          $accounts.append(o);
          if (k === 0) {
            $accounts.change();
          };
        });
      })
      .catch(function(err) {
        if (err.message && err.message.includes('account'))
          mainSwitch("#no_accounts");
        else
          mainSwitch("#invalid_contract");
        // retry after 1s
        setTimeout(refreshAccounts, 1000);
      });
  }

  function signRetry(amount) {
    autoSign = false;
    ugatecoin.incrementBalanceAndSign(!isNaN(amount) ? amount : uGatecoinParams.amount)
      .then(function(proof) {
        $('.channel_present_sign').removeClass('green-btn')
        console.log("SIGNED!", proof);
        Cookies.set("RDN-Sender-Address", ugatecoin.channel.account);
        Cookies.set("RDN-Open-Block", ugatecoin.channel.block);
        Cookies.set("RDN-Sender-Balance", proof.balance.toString());
        Cookies.set("RDN-Balance-Signature", proof.sig);
        Cookies.remove("RDN-Nonexisting-Channel");
        mainSwitch("#channel_loading");
        location.reload();
      })
      .catch(function(err) {
        if (err.message && err.message.includes('Insuficient funds')) {
          console.error(err);
          var current = err['current'];
          var missing = err['required'].sub(current);
          $('#deposited').text(ugatecoin.tkn2num(current));
          $('#required').text(ugatecoin.tkn2num(missing));
          $('#remaining').text(ugatecoin.tkn2num(current.sub(ugatecoin.channel.proof.balance)));
          mainSwitch("#topup");
        } else if (err.message && err.message.includes('User denied message signature')) {
          console.error(err);
          $('.channel_present_sign').addClass('green-btn');
        } else {
          console.error(err);
          errorDialog("An error occurred trying to sign the transfer", err);
          refreshAccounts();
        }
      });
  }

  function closeChannel(closingSig) {
    return ugatecoin.closeChannel(closingSig)
      .then(function(res) {
        console.log("CLOSED", res);
        refreshAccounts();
        return res;
      })
      .catch(function(err) {
        errorDialog("An error occurred trying to close the channel", err);
        refreshAccounts();
        throw err;
      });
  }

  // ==== BINDINGS ====

  $accounts.change(function($event) {
    var account = $event.target.value;

    ugatecoin.loadStoredChannel(account, uGatecoinParams.receiver);
    if (ugatecoin.isChannelValid() && Cookies.get("RDN-Balance-Signature")) {
      ugatecoin.verifyProof({
        balance: ugatecoin.web3.toBigNumber(Cookies.get("RDN-Sender-Balance")),
        sig: Cookies.get("RDN-Balance-Signature"),
      });
    }

    (ugatecoin.isChannelValid() ?
      Promise.reject(ugatecoin.channel) :
      ugatecoin.loadChannelFromBlockchain(account, uGatecoinParams.receiver)
    ).then(
      function() { // resolved == loadFromBlockchain successful, retry page with balance=0
        signRetry(0);
        throw new Error('loadChannelFromBlockchain successful');
      },
      function() { // rejected == isChannelValid or loadChannelFromBlockchain didn't find anything,
        // continue normal loading, for channel creation
        return ugatecoin.getTokenInfo(account);
      }
    ).then(function(token) {
      $('.tkn-name').text(token.name);
      $('.tkn-symbol').text(token.symbol);
      $('.tkn-balance').attr("value", ugatecoin.tkn2num(token.balance) + ' ' + token.symbol);
      $('.tkn-decimals')
        .attr("min", Math.pow(10, -token.decimals).toFixed(token.decimals));
      $("#amount").text(ugatecoin.tkn2num(uGatecoinParams["amount"]));

      if (ugatecoin.isChannelValid() &&
          ugatecoin.channel.account === $event.target.value &&
          ugatecoin.channel.receiver === uGatecoinParams.receiver) {

        return ugatecoin.getChannelInfo()
          .then(function(info) {
            if (Cookies.get("RDN-Nonexisting-Channel")) {
              Cookies.remove("RDN-Nonexisting-Channel");
              window.alert("Server won't accept this channel.\n" +
                "Please, close+settle+forget, and open a new channel");
              $('#channel_present .channel_present_sign').attr("disabled", true);
              autoSign = false;
            } else {
              $('#channel_present .channel_present_sign').attr("disabled", false);
            }
            return info;
          })
          .catch(function(err) {
            console.error(err);
            return { state: "error", deposit: ugatecoin.num2tkn(0) };
          })
          .then(function(info) {
            $('#channel_present .on-state.on-state-' + info.state).show();
            $('#channel_present .on-state:not(.on-state-'+ info.state + ')').hide();

            var remaining = 0;
            if (info.deposit.gt(0) && ugatecoin.channel && ugatecoin.channel.proof
                && ugatecoin.channel.proof.balance.isFinite()) {
              remaining = info.deposit.sub(ugatecoin.channel.proof.balance);
            }
            $("#channel_present #channel_present_balance").text(ugatecoin.tkn2num(remaining));
            $("#channel_present #channel_present_deposit").attr(
              "value", ugatecoin.tkn2num(info.deposit));
            $(".btn-bar").show()

            if (info.state === 'opened') {
              $("#balance-column").removeClass('col-sm-12').addClass('col-sm-8');
              $("#topup-column").show();
            } else {
              $("#balance-column").removeClass('col-sm-8').addClass('col-sm-12');
              $("#topup-column").hide();
            }

            if (info.state === 'opened' && autoSign) {
              signRetry();
            }
            mainSwitch("#channel_present");
          });
      } else {
        mainSwitch("#channel_missing");
      }
    },
    function(err) {
      console.error('Error getting token info', err);
      throw err;
    });
  });

  $("#channel_missing_deposit").bind("input", function($event) {
    if (+$event.target.value > 0) {
      $("#channel_missing_start").attr("disabled", false);
    } else {
      $("#channel_missing_start").attr("disabled", true);
    }
  });
  $("#channel_missing_start").attr("disabled", false);

  $("#channel_missing_start").click(function() {
    var deposit = ugatecoin.num2tkn($("#channel_missing_deposit").val());
    var account = $("#accounts").val();
    mainSwitch("#channel_opening");
    ugatecoin.openChannel(account, uGatecoinParams.receiver, deposit)
      .then(function(channel) {
        Cookies.remove("RDN-Nonexisting-Channel");
        refreshAccounts(true);
      })
      .catch(function(err) {
        console.error(err);
        errorDialog("An error ocurred trying to open a channel", err);
        refreshAccounts();
      });
  });

  $(".channel_present_sign").click(signRetry);

  $(".channel_present_close").click(function() {
    if (!window.confirm("Are you sure you want to close this channel?")) {
      return;
    }
    mainSwitch("#channel_opening");
    // if cooperative close signature exists, use it (api will fail)
    if (ugatecoin.channel.closing_sig) {
      return closeChannel(ugatecoin.channel.closing_sig);
    }
    // signNewProof without balance, sign (if needed) and return current balance
    return ugatecoin.signNewProof(null)
      .catch(function(err) {
        errorDialog("An error occurred trying to get balance signature", err);
        refreshAccounts();
        throw err;
      })
      .then(function(proof) {
        // call cooperative-close URL, and closeChannel with close_signature data
        return $.ajax({
          url: '/api/1/channels/' + ugatecoin.channel.account + '/' + ugatecoin.channel.block,
          method: 'DELETE',
          contentType: 'application/json',
          dataType: 'json',
          data: JSON.stringify({ 'balance': proof.balance.toNumber() }),
        })
        .done(function(result) {
          var closingSig = null;
          if (result && typeof result === 'object' && result['close_signature']) {
            closingSig = result['close_signature'];
          } else {
            console.warn('Invalid cooperative-close response', result);
          }
          return closeChannel(closingSig);
        })
        .fail(function(request, msg, error) {
          console.warn('Error calling cooperative-close', request, msg, error);
          return closeChannel(null);
        });
      });
  });

  $(".channel_present_settle").click(function() {
    if (!window.confirm("Are you sure you want to settle this channel?")) {
      return;
    }
    mainSwitch("#channel_opening");
    ugatecoin.settleChannel()
      .then(function(res) {
        console.log("SETTLED", res);
        refreshAccounts();
      })
      .catch(function(err) {
        errorDialog("An error occurred trying to settle the channel", err);
        refreshAccounts();
      });
  });

  $(".channel_present_forget").click(function() {
    if (!window.confirm("Are you sure you want to forget this channel?" +
        ($('.on-state-settled').is(':visible') ? "" :
         "\nWarning: channel will be left in an unsettled state."))) {
      return;
    }
    Cookies.remove("RDN-Sender-Address");
    Cookies.remove("RDN-Open-Block");
    Cookies.remove("RDN-Sender-Balance");
    Cookies.remove("RDN-Balance-Signature");
    Cookies.remove("RDN-Nonexisting-Channel");
    ugatecoin.forgetStoredChannel();
    refreshAccounts();
  });

  $("#topup_deposit").bind("input", function($event) {
    $(".topup_start").attr("disabled", !(+$event.target.value > 0));
  });

  $(".topup_start").click(function() {
    var deposit = ugatecoin.num2tkn($("#topup_deposit").val());
    mainSwitch("#channel_opening");
    ugatecoin.topUpChannel(deposit)
      .then(function() {
        refreshAccounts(true);
      })
      .catch(function(err) {
        refreshAccounts();
        console.error(err);
        errorDialog("An error ocurred trying to deposit to channel", err);
      });
  });

  $(".token_buy").click(function() {
    var account = $accounts.val();
    mainSwitch("#channel_opening");
    ugatecoin.buyToken(account)
      .then(refreshAccounts)
      .catch(function(err) {
        console.error(err);
        errorDialog("An error ocurred trying to buy tokens", err);
      });
  });

  // ==== FINAL SETUP ====

  refreshAccounts(true);
  $('[data-toggle="tooltip"]').tooltip();

};


mainSwitch("#channel_loading");

$(function() {
  $.getJSON("/api/1/stats").done(function(json) {
    var cnt = 20;
    // wait up to 20*200ms for web3 and call ready()
    var pollingId = setInterval(function() {
      if (Cookies.get("RDN-Insufficient-Confirmations")) {
        Cookies.remove("RDN-Insufficient-Confirmations");
        clearInterval(pollingId);
        $("body").html('<h1>Waiting confirmations...</h1>');
        setTimeout(function() { location.reload(); }, 5000);
      } else if (cnt <= 0 || window.web3) {
        clearInterval(pollingId);
        pageReady(json['manager_abi'], json['token_abi'], json['sync_block']);
      } else {
        --cnt;
      }
    }, 200);
  });
});
