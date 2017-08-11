from .instance import shared_muse_instance
from .account import Account
from .exceptions import ProposalDoesNotExistException
import logging
log = logging.getLogger(__name__)


class Proposal(dict):
    """ Read data about a Proposal Balance in the chain

        :param str id: Id of the proposal
        :param muse muse_instance: muse() instance to use when accesing a RPC

    """
    def __init__(
        self,
        id,
        muse_instance=None,
    ):
        self.id = id

        self.muse = muse_instance or shared_muse_instance()
        self.refresh()

    def refresh(self):
        a, b, c = self.id.split(".")
        assert int(a) == 1 and int(b) == 10, "Valid proposal ids are 1.10.x"
        proposal = self.muse.rpc.get_objects([self.id])
        if not any(proposal):
            raise ProposalDoesNotExistException
        super(Proposal, self).__init__(proposal[0])


class Proposals(list):
    """ Obtain a list of pending proposals for an account

        :param str account: Account name
        :param muse muse_instance: muse() instance to use when accesing a RPC
    """
    def __init__(self, account, muse_instance=None):
        self.muse = muse_instance or shared_muse_instance()

        account = Account(account)
        proposals = self.muse.rpc.get_proposed_transactions(account["id"])

        super(Proposals, self).__init__(
            [
                Proposal(x, muse_instance=self.muse)
                for x in proposals
            ]
        )
