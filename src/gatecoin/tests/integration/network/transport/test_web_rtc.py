import gevent
import pytest
from gevent.timeout import Timeout

from gatecoin.constants import EMPTY_SIGNATURE
from gatecoin.messages.synchronization import Processed
from gatecoin.network.transport.matrix.transport import MessagesQueue
from gatecoin.network.transport.matrix.utils import validate_and_parse_message
from gatecoin.settings import CapabilitiesConfig
from gatecoin.tests.utils import factories
from gatecoin.tests.utils.mocks import MockGatecoinService
from gatecoin.transfer import views
from gatecoin.transfer.identifiers import QueueIdentifier
from gatecoin.utils.typing import MessageID

TIMEOUT_MESSAGE_RECEIVE = 15
TIMEOUT_WEB_RTC_CONNECTION = 120

pytestmark = pytest.mark.asyncio


class MessageHandler:
    def __init__(self, bag):
        self.bag = bag

    def on_messages(self, _, messages):
        self.bag.update(messages)


@pytest.mark.skip(reason="web RTC is disabled")
@pytest.mark.parametrize("matrix_server_count", [1])
@pytest.mark.parametrize("number_of_transports", [2])
@pytest.mark.parametrize("capabilities", [CapabilitiesConfig(web_rtc=True)])
def test_web_rtc_message_sync(matrix_transports):

    transport0, transport1 = matrix_transports
    transport1_messages = set()

    gatecoin_service0 = MockGatecoinService()
    gatecoin_service1 = MockGatecoinService()

    def mock_handle_web_rtc_messages(message_data, partner_address):
        messages = validate_and_parse_message(message_data, partner_address)
        transport1_messages.update(messages)

    # set mock function to make sure messages are sent via web rtc
    transport1._web_rtc_manager._handle_message_callback = mock_handle_web_rtc_messages

    transport0.start(gatecoin_service0, None)
    transport1.start(gatecoin_service1, None)

    with Timeout(TIMEOUT_WEB_RTC_CONNECTION):
        # wait until web rtc connection is ready
        while not transport0._web_rtc_manager.has_ready_channel(gatecoin_service1.address):
            gevent.sleep(1)
        while not transport1._web_rtc_manager.has_ready_channel(gatecoin_service0.address):
            gevent.sleep(1)

    queue_identifier = QueueIdentifier(
        recipient=transport1._gatecoin_service.address,
        canonical_identifier=factories.UNIT_CANONICAL_ID,
    )

    gatecoin0_queues = views.get_all_messagequeues(views.state_from_gatecoin(gatecoin_service0))
    gatecoin0_queues[queue_identifier] = []

    for i in range(5):
        message = Processed(message_identifier=MessageID(i), signature=EMPTY_SIGNATURE)
        gatecoin0_queues[queue_identifier].append(message)
        transport0._gatecoin_service.sign(message)
        transport0.send_async([MessagesQueue(queue_identifier, [(message, None)])])

    with Timeout(TIMEOUT_MESSAGE_RECEIVE):
        while not len(transport1_messages) == 5:
            gevent.sleep(0.1)
