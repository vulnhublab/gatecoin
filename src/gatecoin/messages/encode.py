from gatecoin.messages.abstract import Message
from gatecoin.messages.synchronization import Processed
from gatecoin.messages.transfers import (
    LockedTransfer,
    LockExpired,
    RevealSecret,
    SecretRequest,
    Unlock,
)
from gatecoin.messages.withdraw import WithdrawConfirmation, WithdrawExpired, WithdrawRequest
from gatecoin.transfer.architecture import SendMessageEvent
from gatecoin.transfer.events import (
    SendProcessed,
    SendWithdrawConfirmation,
    SendWithdrawExpired,
    SendWithdrawRequest,
)
from gatecoin.transfer.mediated_transfer.events import (
    SendLockedTransfer,
    SendLockExpired,
    SendSecretRequest,
    SendSecretReveal,
    SendUnlock,
)


_EVENT_MAP = {
    SendLockExpired: LockExpired,
    SendLockedTransfer: LockedTransfer,
    SendProcessed: Processed,
    SendSecretRequest: SecretRequest,
    SendSecretReveal: RevealSecret,
    SendUnlock: Unlock,
    SendWithdrawConfirmation: WithdrawConfirmation,
    SendWithdrawExpired: WithdrawExpired,
    SendWithdrawRequest: WithdrawRequest,
}


def message_from_sendevent(send_event: SendMessageEvent) -> Message:
    t_event = type(send_event)
    EventClass = _EVENT_MAP.get(t_event)
    if EventClass is None:
        raise ValueError(f"Unknown event type {t_event}")
    return EventClass.from_event(send_event)  # type: ignore
