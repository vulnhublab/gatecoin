import time
from contextlib import contextmanager

import gevent
import pytest
from gevent import Timeout
from matrix_client.errors import MatrixRequestError

from gatecoin.constants import DeviceIDs
from gatecoin.network.transport.matrix.client import GMatrixClient, User
from gatecoin.network.transport.matrix.utils import login, make_client
from gatecoin.tests.utils import factories
from gatecoin.tests.utils.detect_failure import raise_on_failure
from gatecoin.tests.utils.transport import ignore_messages
from gatecoin.utils.signer import Signer
from gatecoin.utils.typing import Generator, Tuple

# https://matrix.org/docs/spec/appendices#user-identifiers
USERID_VALID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz-.=_/"


@contextmanager
def must_run_for_at_least(minimum_elapsed_time: float, msg: str) -> Generator:
    start = time.time()
    yield
    elapsed = time.time() - start
    if elapsed < minimum_elapsed_time:
        raise AssertionError(msg)


def create_logged_in_client(server: str) -> Tuple[GMatrixClient, Signer]:
    client = make_client(ignore_messages, [server])
    signer = factories.make_signer()

    login(client, signer, DeviceIDs.GATECOIN)

    return client, signer


def replace_one_letter(s: str) -> str:
    char_at_pos2 = s[2]
    pos_of_char = USERID_VALID_CHARS.index(char_at_pos2)
    pos_of_next_char = pos_of_char + 1 % len(USERID_VALID_CHARS)
    next_char = USERID_VALID_CHARS[pos_of_next_char]

    return s[:2] + next_char + s[2 + 1 :]


def test_assumption_matrix_userid(local_matrix_servers):
    client, _ = create_logged_in_client(local_matrix_servers[0])

    # userid validation expects a str
    none_user_id = None
    with pytest.raises(AttributeError):
        User(client.api, none_user_id)

    # userid validation requires `@`
    empty_user_id = ""
    with pytest.raises(ValueError):
        User(client.api, empty_user_id)

    # userid validation requires `@`
    invalid_user_id = client.user_id[1:]
    with pytest.raises(ValueError):
        User(client.api, invalid_user_id)

    # The format of the userid is valid, however the user does not exist, the
    # server returns an error
    unexisting_user_id = replace_one_letter(client.user_id)
    user = User(client.api, unexisting_user_id)
    with pytest.raises(MatrixRequestError):
        user.get_display_name()

    # The userid is valid and the user exists, this should not raise
    newlogin_client, _ = create_logged_in_client(local_matrix_servers[0])
    user = User(client.api, newlogin_client.user_id)
    user.get_display_name()


@pytest.mark.flaky
@raise_on_failure
@pytest.mark.parametrize("number_of_nodes", [2])
def test_assumption_broadcast_queue_delays_shutdown(gatecoin_chain):
    gatecoin_node = gatecoin_chain[0]
    # mark broadcast queue dirty
    from gevent.queue import JoinableQueue

    gatecoin_node.transport._broadcast_queue = JoinableQueue(unfinished_tasks=1)
    # spawn a "stop" and give it some time
    gevent.spawn(gatecoin_node.stop)
    gevent.sleep(10)
    msg = "Transport stopped before broadcast queue is empty"
    assert not gatecoin_node.transport._client.stop_event.is_set(), msg
    assert gatecoin_node.wal is not None, "Node stopped even though transport is not ready"
    # mark broadcast queue clean
    gatecoin_node.transport._broadcast_queue.task_done()
    assert gatecoin_node.transport._broadcast_queue.unfinished_tasks == 0
    # now the node stop should succeed
    with Timeout(10):
        while True:
            if gatecoin_node.wal is None:
                break
            gevent.sleep(1)
    assert gatecoin_node.wal is None, "Node did not stop"
