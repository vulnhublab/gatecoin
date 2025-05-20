import traceback
from functools import wraps
from typing import Any, Callable, List

import gevent
import pytest
import structlog
from gevent.event import AsyncResult

from gatecoin.api.rest import APIServer
from gatecoin.gatecoin_service import GatecoinService

log = structlog.get_logger(__name__)


def raise_on_failure(test_function: Callable) -> Callable:
    """Wait on the result for the test function and any of the apps.

    This decorator should be used for happy path testing with more than one app.
    This will raise if any of the apps is killed.
    """

    @wraps(test_function)
    def wrapper(**kwargs: Any) -> None:
        result = AsyncResult()
        gatecoin_services: List[GatecoinService] = []

        apps: List[GatecoinService] = kwargs.get("gatecoin_network", kwargs.get("gatecoin_chain"))

        if apps:
            assert all(isinstance(app, GatecoinService) for app in apps)
            gatecoin_services = apps
        else:
            api_server = kwargs.get("api_server_test_instance")
            if isinstance(api_server, APIServer):
                gatecoin_services = [api_server.rest_api.gatecoin_api.gatecoin]

        if not gatecoin_services:
            raise Exception(
                f"Can't use `raise_on_failure` on test function {test_function.__name__} "
                "which uses neither `gatecoin_network` nor `gatecoin_chain` fixtures."
            )

        restart_node = kwargs.get("restart_node", None)
        if restart_node is not None:
            restart_node.link_exception_to(result)

        # Do not use `link` or `link_value`, an app can be stopped to test restarts.
        for gatecoin in gatecoin_services:
            assert gatecoin, "The GatecoinService must be started"
            gatecoin.greenlet.link_exception(result)

        test_greenlet = gevent.spawn(test_function, **kwargs)
        test_greenlet.link(result)

        # Returns if either happens:
        # - The test finished (successfully or not)
        # - One of the apps crashed during the test
        try:
            result.get()
        except:  # noqa
            # Print the stack trace of the running test to know in which line the
            # test is waiting.
            #
            # This may print a duplicated stack trace, when the test fails.
            log.exception(
                "Test failed",
                test_traceback="".join(traceback.format_stack(test_greenlet.gr_frame)),
                all_tracebacks="\n".join(gevent.util.format_run_info()),
            )

            raise

    wrapper._decorated_raise_on_failure = True  # type: ignore
    return wrapper


expect_failure = pytest.mark.expect_failure
