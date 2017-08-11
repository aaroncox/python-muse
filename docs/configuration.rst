*************
Configuration
*************

The pymuse library comes with its own local configuration database
that stores information like

* API node URL
* default account name
* the encrypted master password

and potentially more.

You can access those variables like a regular dictionary by using

.. code-block:: python

    from muse import Muse
    muse = muse()
    print(muse.config.items())

Keys can be added and changed like they are for regular dictionaries.

If you don't want to load the :class:`muse.muse` class, you
can load the configuration directly by using:

.. code-block:: python

    from muse.storage import configStorage as config

API
---
.. autoclass:: muse.storage.Configuration
   :members:
