from gatecoin.constants import LOCKSROOT_OF_NO_LOCKS
from gatecoin.transfer.channel import compute_locksroot
from gatecoin.transfer.state import PendingLocksState


def test_empty():
    locks = PendingLocksState([])
    assert compute_locksroot(locks) == LOCKSROOT_OF_NO_LOCKS
