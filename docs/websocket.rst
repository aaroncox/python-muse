******************
MuseWebsocket
******************

This class allows subscribe to push notifications from the muse
node.

.. code-block:: python

    from pprint import pprint
    from museapi.websocket import MuseWebsocket

    ws = MuseWebsocket(
        "wss://node.testnet.muse.eu",
        markets=[["1.3.0", "1.3.172"]],
        accounts=["xeroc"],
        objects=["2.0.x", "2.1.x"],
        on_market=pprint,
        on_account=print,
    )

    ws.run_forever()

Defintion
=========
.. autoclass:: museapi.websocket.MuseWebsocket
    :members:
    :undoc-members:
    :private-members:
    :special-members:
