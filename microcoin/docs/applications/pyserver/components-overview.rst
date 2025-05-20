Components overview
-------------------

This section will give you an overview of the architecture of the µGateCoin server.
The illustrations are inspired by UML even though they might not be exact standard.


Channel manager
~~~~~~~~~~~~~~~

This component interacts with the blockchain and keeps track of the state of all the channels from the
transactions Receivers point of view.
For more information, look at the API for the :py:class:`~microcoin.channel_manager.manager.ChannelManager`

.. figure:: /diagrams/ChannelManagerClass.png
   :alt: 

Proxy
~~~~~~~~~~~~~~~

This component interacts with the blockchain and keeps track of the state of all the channels from the
transactions Receivers point of view.
For more information, look at the API for the :py:class:`~microcoin.proxy.paywalled_proxy.PaywalledProxy`

.. figure:: /diagrams/ProxyClass.png
   :alt:

