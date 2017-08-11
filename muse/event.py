from muse.instance import shared_muse_instance
from .exceptions import EventDoesNotExistException


class Event(dict):
    """ Read data about an event on the chain

        :param str identifier: Identifier
        :param muse muse_instance: muse() instance to use when accesing a RPC

    """
    def __init__(
        self,
        identifier,
        lazy=False,
        muse_instance=None,
    ):
        self.muse = muse_instance or shared_muse_instance()
        self.cached = False

        if isinstance(identifier, str):
            self.identifier = identifier
            if not lazy:
                self.refresh()
        elif isinstance(identifier, dict):
            self.cached = False
            self.identifier = identifier.get("id")
            super(Event, self).__init__(identifier)

    def refresh(self):
        assert self.identifier[:5] == "1.19.",\
            "Identifier needs to be of form '1.19.xx'"
        data = self.muse.rpc.get_object(self.identifier)
        if not data:
            raise EventDoesNotExistException(self.identifier)
        super(Event, self).__init__(data)
        self.cached = True

    def __getitem__(self, key):
        if not self.cached:
            self.refresh()
        return super(Event, self).__getitem__(key)

    def items(self):
        if not self.cached:
            self.refresh()
        return super(Event, self).items()

    def __repr__(self):
        return "<Event %s>" % str(self.identifier)

    @property
    def eventgroup(self):
        from .eventgroup import EventGroup
        return EventGroup(self["event_group_id"])


class Events(list):
    raise NotImplementedError("Missing API calls")
