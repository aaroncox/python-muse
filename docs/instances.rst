Instances
~~~~~~~~~

Default instance to be used when no ``muse_instance`` is given to
the Objects!

.. code-block:: python

   from muse.instance import shared_muse_instance

   account = Account("xeroc")
   # is equivalent with 
   account = Account("xeroc", muse_instance=shared_muse_instance())

.. automethod:: muse.instance.shared_muse_instance
.. automethod:: muse.instance.set_shared_muse_instance
