import muse as dct

_shared_muse_instance = None


def shared_muse_instance():
    """ This method will initialize ``_shared_muse_instance`` and return it.
        The purpose of this method is to have offer single default
        muse instance that can be reused by multiple classes.
    """
    global _shared_muse_instance
    if not _shared_muse_instance:
        _shared_muse_instance = dct.muse()
    return _shared_muse_instance


def set_shared_muse_instance(muse_instance):
    """ This method allows us to override default muse instance for all users of
        ``_shared_muse_instance``.

        :param muse.muse.muse muse_instance: muse instance
    """
    global _shared_muse_instance
    _shared_muse_instance = muse_instance
