Try the echo service
====================


System context
--------------

In order to get you started, we created an example application, that receives micropayments and some
parameter over a http-request - and simply echos this parameter when the micropayment was valid.
Please follow the
:doc:`microcoin installation instructions <dev-setup>`
and the
:doc:`instructions to set up geth <blockchain>`.

.. figure:: /diagrams/uGatecoinEchoOverview.png 


   Schematic overview of a machine-to-machine µGateCoin application [3]_

Starting the µGateCoin Receiver
-----------------------------

Before starting the receiver, it needs to be assigned a private key with some TKN. Navigate to :code:`./microcoin/microcoin/examples` and create a new file containing your private key as exported in the Blockchain Setup guide by MetaMask. The file should be named :code:`pk_tut.txt`.

From the root directory of µGateCoin, start:

.. code:: sh

    python microcoin/examples/echo_server.py --private-key microcoin/examples/pk_tut.txt

Starting the µGateCoin Sender
---------------------------

To actually start the request for resource :code:`/hello`, we will fire up the µGateCoin client with the prefunded account.

While the Receiver is still running (in another terminal window for example), execute this command from the µGateCoin root folder:

.. code:: sh

   python microcoin/examples/echo_client.py --private-key microcoin/examples/pk_tut.txt --resource /echofix/hello

After some seconds, you should get the output

.. code:: sh

   INFO:root:Got the resource /echofix/hello type=text/html; charset=utf-8:
   hello

This means: 
 - a channel has been created
 - a deposit of 50 aTKN has been escrowed 
 - a micropayment of 1 aTKN has been transferred to the receiver
 - the receiver returned the requested resource (the “hello” parameter in this simple case) for this payment

Congratulations, you just performed your first micropayment!

.. rubric:: Footnotes

.. [#] All robot icons made by `Freepic <http://flaticon.com/authors/freepik>`_ from http://www.flaticon.com.
.. [#] Raspberry PI Pictograms by `TinkTank.club <http://www.tinktank.club>`_
.. [#] All other icons from http://icomoon.io IcoMoon Icon Pack Free, licensed under a Creative Commons Attribution 4.0 International License
