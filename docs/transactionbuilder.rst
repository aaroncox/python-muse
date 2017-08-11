Transaction Builder
~~~~~~~~~~~~~~~~~~~

To build your own transactions and sign them

.. code-block:: python

   from muse.transactionbuilder import TransactionBuilder
   from musebase.operations import Transfer
   tx = TransactionBuilder()
   tx.appendOps(Transfer(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},  # will be filled in automatically
            "from": "1.2.124",
            "to": "1.2.1241",
            "amount": {"amount": 10000, "asset_id": "1.3.0"},
        }))
   tx.appendSigner("xeroc", "active")
   tx.sign()
   tx.broadcast()

.. autoclass:: muse.transactionbuilder.TransactionBuilder
   :members:
