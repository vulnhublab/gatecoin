API Tutorial
############

This tutorial will show you how to use Gatecoin via the API by walking you through a few API calls. 
The steps are similar to the WebUI tutorial, but directly use the API endpoints.
We will outline the steps necessary for participating in a token
network. To see all available endpoints visit the
:ref:`resources <api_endpoints>` part of the documentation.

In the examples throughout this tutorial we will be using a hypothetical
ERC20 token with the address ``0x9aBa529db3FF2D8409A1da4C9eB148879b046700``.

Check if Gatecoin was started correctly
=====================================

Before we start we'll make sure that Gatecoin is running correctly.

This gives us an opportunity to introduce the
:ref:`address <api_address>` endpoint.

.. code:: bash

   curl -i http://localhost:5001/api/v1/address

Your Gatecoin node is up and running if the response returns the same
address as the Ethereum address used for starting Gatecoin.

You're now ready to start interacting with the different endpoints and
learn how they can be used.

.. include:: 1-join-a-token-network.inc.rst

.. include:: 2-open-a-channel.inc.rst

.. include:: 3-deposit.inc.rst

.. include:: 3-make-a-payment.inc.rst

.. include:: withdraw-tokens.inc.rst

.. include:: 4-settle-payments-and-close-channels.inc.rst
