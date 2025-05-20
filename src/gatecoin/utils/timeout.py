import gevent
from gevent import Greenlet

from gatecoin.gatecoin_service import GatecoinService
from gatecoin.utils.typing import Any, BlockNumber, Callable, Optional
from gatecoin.waiting import wait_for_block


def _timeout_task(  # pragma: no unittest
    throw: Callable,
    exception_to_throw: Exception,
    gatecoin: GatecoinService,
    block_number: BlockNumber,
    retry_timeout: float,
) -> None:
    wait_for_block(gatecoin, block_number, retry_timeout)
    throw(exception_to_throw)


class BlockTimeout:  # pragma: no unittest
    def __init__(
        self,
        exception_to_throw: Exception,
        gatecoin: GatecoinService,
        block_number: BlockNumber,
        retry_timeout: float,
    ) -> None:
        self.exception_to_throw = exception_to_throw
        self.gatecoin = gatecoin
        self.block_number = block_number
        self.retry_timeout = retry_timeout
        self._task: Optional[Greenlet] = None

    def __enter__(self) -> None:
        self._task = gevent.spawn(
            _timeout_task,
            gevent.getcurrent().throw,
            self.exception_to_throw,
            self.gatecoin,
            self.block_number,
            self.retry_timeout,
        )
        self._task.name = "timout_task"

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self._task:
            self._task.kill()
