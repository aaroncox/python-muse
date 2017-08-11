import json
import logging
import random
import re
from datetime import datetime, timedelta

from museapi.node import MuseNodeRPC
from musebase.account import PrivateKey, PublicKey
from musebase import transactions, operations
from .asset import Asset
from .account import Account
from .amount import Amount
from .witness import Witness
from .committee import Committee
from .storage import configStorage as config
from .exceptions import (
    AccountExistsException,
    AccountDoesNotExistsException,
    InsufficientAuthorityError,
    MissingKeyError,
)
from .wallet import Wallet
from .transactionbuilder import TransactionBuilder
from .utils import formatTime

log = logging.getLogger(__name__)


class Muse(object):
    """ Connect to the muse network.

        :param str node: Node to connect to *(optional)*
        :param str rpcuser: RPC user *(optional)*
        :param str rpcpassword: RPC password *(optional)*
        :param bool nobroadcast: Do **not** broadcast a transaction! *(optional)*
        :param bool debug: Enable Debugging *(optional)*
        :param array,dict,string keys: Predefine the wif keys to shortcut the wallet database *(optional)*
        :param bool offline: Boolean to prevent connecting to network (defaults to ``False``) *(optional)*
        :param str proposer: Propose a transaction using this proposer *(optional)*
        :param int proposal_expiration: Expiration time (in seconds) for the proposal *(optional)*
        :param int expiration: Delay in seconds until transactions are supposed to expire *(optional)*
        :param bool bundle: Do not broadcast transactions right away, but allow to bundle operations *(optional)*

        Three wallet operation modes are possible:

        * **Wallet Database**: Here, the muselibs load the keys from the
          locally stored wallet SQLite database (see ``storage.py``).
          To use this mode, simply call ``muse()`` without the
          ``keys`` parameter
        * **Providing Keys**: Here, you can provide the keys for
          your accounts manually. All you need to do is add the wif
          keys for the accounts you want to use as a simple array
          using the ``keys`` parameter to ``muse()``.
        * **Force keys**: This more is for advanced users and
          requires that you know what you are doing. Here, the
          ``keys`` parameter is a dictionary that overwrite the
          ``active``, ``owner``, or ``memo`` keys for
          any account. This mode is only used for *foreign*
          signatures!

        If no node is provided, it will connect to the node of
        http://MUSE-node.bitshares.eu. It is **highly** recommended that you pick your own
        node instead. Default settings can be changed with:

        .. code-block:: python

            muse set node <host>

        where ``<host>`` starts with ``ws://`` or ``wss://``.

        The purpose of this class it to simplify interaction with
        muse.

        The idea is to have a class that allows to do this:

        .. code-block:: python

            from muse import Muse
            muse = muse()
            print(muse.info())

        All that is requires is for the user to have added a key with ``muse``

        .. code-block:: bash

            muse addkey

        and setting a default author:

        .. code-block:: bash

            muse set default_account xeroc

        This class also deals with edits, votes and reading content.
    """

    def __init__(self,
                 node="",
                 rpcuser="",
                 rpcpassword="",
                 debug=False,
                 **kwargs):

        # More specific set of APIs to register to
        if "apis" not in kwargs:
            kwargs["apis"] = [
                "database",
                "network_broadcast",
            ]

        self.rpc = None
        self.debug = debug

        self.offline = bool(kwargs.get("offline", False))
        self.nobroadcast = bool(kwargs.get("nobroadcast", False))
        self.unsigned = bool(kwargs.get("unsigned", False))
        self.expiration = int(kwargs.get("expiration", 30))
        self.proposer = kwargs.get("proposer", None)
        self.proposal_expiration = int(kwargs.get("proposal_expiration", 60 * 60 * 24))
        self.bundle = bool(kwargs.get("bundle", False))

        # Store config for access through other Classes
        self.config = config

        if not self.offline:
            self.connect(node=node,
                         rpcuser=rpcuser,
                         rpcpassword=rpcpassword,
                         **kwargs)

        self.wallet = Wallet(self.rpc, **kwargs)
        self.txbuffer = TransactionBuilder(muse_instance=self)

    def connect(self,
                node="",
                rpcuser="",
                rpcpassword="",
                **kwargs):
        """ Connect to Steem network (internal use only)
        """
        if not node:
            if "node" in config:
                node = config["node"]
            else:
                raise ValueError("A Steem node needs to be provided!")

        if not rpcuser and "rpcuser" in config:
            rpcuser = config["rpcuser"]

        if not rpcpassword and "rpcpassword" in config:
            rpcpassword = config["rpcpassword"]

        self.rpc = MuseNodeRPC(node, rpcuser, rpcpassword, **kwargs)

    def finalizeOp(self, ops, account, permission):
        """ This method obtains the required private keys if present in
            the wallet, finalizes the transaction, signs it and
            broadacasts it

            :param operation ops: The operation (or list of operaions) to broadcast
            :param operation account: The account that authorizes the
                operation
            :param string permission: The required permission for
                signing (active, owner, posting)

            ... note::

                If ``ops`` is a list of operation, they all need to be
                signable by the same key! Thus, you cannot combine ops
                that require active permission with ops that require
                posting permission. Neither can you use different
                accounts for different operations!
        """
        # Append transaction
        self.txbuffer.appendOps(ops)

        if self.unsigned:
            # In case we don't want to sign anything
            self.txbuffer.addSigningInformation(account, permission)
            return self.txbuffer
        elif self.bundle:
            # In case we want to add more ops to the tx (bundle)
            self.txbuffer.appendSigner(account, permission)
        else:
            # default behavior: sign + broadcast
            self.txbuffer.appendSigner(account, permission)
            self.txbuffer.sign()
            return self.txbuffer.broadcast()

    def sign(self, tx=None, wifs=[]):
        """ Sign a provided transaction witht he provided key(s)

            :param dict tx: The transaction to be signed and returned
            :param string wifs: One or many wif keys to use for signing
                a transaction. If not present, the keys will be loaded
                from the wallet as defined in "missing_signatures" key
                of the transactions.
        """
        if tx:
            txbuffer = TransactionBuilder(tx, muse_instance=self)
        else:
            txbuffer = self.txbuffer
        txbuffer.appendWif(wifs)
        txbuffer.appendMissingSignatures()
        txbuffer.sign()
        return txbuffer.json()

    def broadcast(self, tx=None):
        """ Broadcast a transaction to the muse network

            :param tx tx: Signed transaction to broadcast
        """
        if tx:
            # If tx is provided, we broadcast the tx
            return TransactionBuilder(tx).broadcast()
        else:
            return self.txbuffer.broadcast()

    def info(self):
        """ Returns the global properties
        """
        return self.rpc.get_dynamic_global_properties()

    def create_account(
        self,
        account_name,
        registrar=None,
        referrer="1.2.0",
        referrer_percent=50,
        owner_key=None,
        active_key=None,
        memo_key=None,
        password=None,
        additional_owner_keys=[],
        additional_active_keys=[],
        additional_owner_accounts=[],
        additional_active_accounts=[],
        proxy_account="proxy-to-self",
        storekeys=True,
    ):
        """ Create new account on muse

            The brainkey/password can be used to recover all generated keys (see
            `musebase.account` for more details.

            By default, this call will use ``default_account`` to
            register a new name ``account_name`` with all keys being
            derived from a new brain key that will be returned. The
            corresponding keys will automatically be installed in the
            wallet.

            .. warning:: Don't call this method unless you know what
                          you are doing! Be sure to understand what this
                          method does and where to find the private keys
                          for your account.

            .. note:: Please note that this imports private keys
                      (if password is present) into the wallet by
                      default. However, it **does not import the owner
                      key** for security reasons. Do NOT expect to be
                      able to recover it from the wallet if you lose
                      your password!

            :param str account_name: (**required**) new account name
            :param str registrar: which account should pay the registration fee
                                (defaults to ``default_account``)
            :param str owner_key: Main owner key
            :param str active_key: Main active key
            :param str memo_key: Main memo_key
            :param str password: Alternatively to providing keys, one
                                 can provide a password from which the
                                 keys will be derived
            :param array additional_owner_keys:  Additional owner public keys
            :param array additional_active_keys: Additional active public keys
            :param array additional_owner_accounts: Additional owner account names
            :param array additional_active_accounts: Additional acctive account names
            :param bool storekeys: Store new keys in the wallet (default: ``True``)
            :raises AccountExistsException: if the account already exists on the blockchain

        """
        if not registrar and config["default_account"]:
            registrar = config["default_account"]
        if not registrar:
            raise ValueError(
                "Not registrar account given. Define it with " +
                "registrar=x, or set the default_account using 'muse'")
        if password and (owner_key or active_key or memo_key):
            raise ValueError(
                "You cannot use 'password' AND provide keys!"
            )

        try:
            Account(account_name, muse_instance=self)
            raise AccountExistsException
        except:
            pass

        referrer = Account(referrer, muse_instance=self)
        registrar = Account(registrar, muse_instance=self)

        " Generate new keys from password"
        from musebase.account import PasswordKey, PublicKey
        if password:
            active_key = PasswordKey(account_name, password, role="active")
            owner_key = PasswordKey(account_name, password, role="owner")
            memo_key = PasswordKey(account_name, password, role="memo")
            active_pubkey = active_key.get_public_key()
            owner_pubkey = owner_key.get_public_key()
            memo_pubkey = memo_key.get_public_key()
            active_privkey = active_key.get_private_key()
            # owner_privkey   = owner_key.get_private_key()
            memo_privkey = memo_key.get_private_key()
            # store private keys
            if storekeys:
                # self.wallet.addPrivateKey(owner_privkey)
                self.wallet.addPrivateKey(active_privkey)
                self.wallet.addPrivateKey(memo_privkey)
        elif (owner_key and active_key and memo_key):
            active_pubkey = PublicKey(active_key, prefix=self.rpc.chain_params["prefix"])
            owner_pubkey = PublicKey(owner_key, prefix=self.rpc.chain_params["prefix"])
            memo_pubkey = PublicKey(memo_key, prefix=self.rpc.chain_params["prefix"])
        else:
            raise ValueError(
                "Call incomplete! Provide either a password or public keys!"
            )
        owner = format(owner_pubkey, self.rpc.chain_params["prefix"])
        active = format(active_pubkey, self.rpc.chain_params["prefix"])
        memo = format(memo_pubkey, self.rpc.chain_params["prefix"])

        owner_key_authority = [[owner, 1]]
        active_key_authority = [[active, 1]]
        owner_accounts_authority = []
        active_accounts_authority = []

        # additional authorities
        for k in additional_owner_keys:
            owner_key_authority.append([k, 1])
        for k in additional_active_keys:
            active_key_authority.append([k, 1])

        for k in additional_owner_accounts:
            addaccount = Account(k, muse_instance=self)
            owner_accounts_authority.append([addaccount["id"], 1])
        for k in additional_active_accounts:
            addaccount = Account(k, muse_instance=self)
            active_accounts_authority.append([addaccount["id"], 1])

        # voting account
        voting_account = Account(proxy_account or "proxy-to-self", muse_instance=self)

        op = {
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "registrar": registrar["id"],
            "referrer": referrer["id"],
            "referrer_percent": referrer_percent * 100,
            "name": account_name,
            'owner': {'account_auths': owner_accounts_authority,
                      'key_auths': owner_key_authority,
                      "address_auths": [],
                      'weight_threshold': 1},
            'active': {'account_auths': active_accounts_authority,
                       'key_auths': active_key_authority,
                       "address_auths": [],
                       'weight_threshold': 1},
            "options": {"memo_key": memo,
                        "voting_account": voting_account["id"],
                        "num_witness": 0,
                        "num_committee": 0,
                        "votes": [],
                        "extensions": []
                        },
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        }
        op = operations.Account_create(**op)
        return self.finalizeOp(op, registrar, "active")

    def transfer(self, to, amount, asset, memo="", account=None):
        """ Transfer an asset to another account.

            :param str to: Recipient
            :param float amount: Amount to transfer
            :param str asset: Asset to transfer
            :param str memo: (optional) Memo, may begin with `#` for encrypted messaging
            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        from .memo import Memo
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        account = Account(account, muse_instance=self)
        amount = Amount(amount, asset, muse_instance=self)
        to = Account(to, muse_instance=self)

        memoObj = Memo(
            from_account=account,
            to_account=to,
            muse_instance=self
        )

        op = operations.Transfer(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "from": account["id"],
            "to": to["id"],
            "amount": {
                "amount": int(amount),
                "asset_id": amount.asset["id"]
            },
            "memo": memoObj.encrypt(memo),
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account, "active")

    def _test_weights_treshold(self, authority):
        """ This method raises an error if the threshold of an authority cannot
            be reached by the weights.

            :param dict authority: An authority of an account
            :raises ValueError: if the threshold is set too high
        """
        weights = 0
        for a in authority["account_auths"]:
            weights += a[1]
        for a in authority["key_auths"]:
            weights += a[1]
        if authority["weight_threshold"] > weights:
            raise ValueError("Threshold too restrictive!")

    def allow(self, foreign, weight=None, permission="active",
              account=None, threshold=None):
        """ Give additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param int weight: (optional) The weight to use. If not
                define, the threshold will be used. If the weight is
                smaller than the threshold, additional signatures will
                be required. (defaults to threshold)
            :param str permission: (optional) The actual permission to
                modify (defaults to ``active``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
            :param int threshold: The threshold that needs to be reached
                by signatures to be able to interact
        """
        from copy import deepcopy
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        if permission not in ["owner", "active"]:
            raise ValueError(
                "Permission needs to be either 'owner', or 'active"
            )
        account = Account(account, muse_instance=self)

        if not weight:
            weight = account[permission]["weight_threshold"]

        authority = deepcopy(account[permission])
        try:
            pubkey = PublicKey(foreign, prefix=self.rpc.chain_params["prefix"])
            authority["key_auths"].append([
                str(pubkey),
                weight
            ])
        except:
            try:
                foreign_account = Account(foreign, muse_instance=self)
                authority["account_auths"].append([
                    foreign_account["id"],
                    weight
                ])
            except:
                raise ValueError(
                    "Unknown foreign account or invalid public key"
                )
        if threshold:
            authority["weight_threshold"] = threshold
            self._test_weights_treshold(authority)

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            permission: authority,
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        })
        if permission == "owner":
            return self.finalizeOp(op, account["name"], "owner")
        else:
            return self.finalizeOp(op, account["name"], "active")

    def disallow(self, foreign, permission="active",
                 account=None, threshold=None):
        """ Remove additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param str permission: (optional) The actual permission to
                modify (defaults to ``active``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
            :param int threshold: The threshold that needs to be reached
                by signatures to be able to interact
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        if permission not in ["owner", "active"]:
            raise ValueError(
                "Permission needs to be either 'owner', or 'active"
            )
        account = Account(account, muse_instance=self)
        authority = account[permission]

        try:
            pubkey = PublicKey(foreign, prefix=self.rpc.chain_params["prefix"])
            affected_items = list(
                filter(lambda x: x[0] == str(pubkey),
                       authority["key_auths"]))
            authority["key_auths"] = list(filter(
                lambda x: x[0] != str(pubkey),
                authority["key_auths"]
            ))
        except:
            try:
                foreign_account = Account(foreign, muse_instance=self)
                affected_items = list(
                    filter(lambda x: x[0] == foreign_account["id"],
                           authority["account_auths"]))
                authority["account_auths"] = list(filter(
                    lambda x: x[0] != foreign_account["id"],
                    authority["account_auths"]
                ))
            except:
                raise ValueError(
                    "Unknown foreign account or unvalid public key"
                )

        removed_weight = affected_items[0][1]

        # Define threshold
        if threshold:
            authority["weight_threshold"] = threshold

        # Correct threshold (at most by the amount removed from the
        # authority)
        try:
            self._test_weights_treshold(authority)
        except:
            log.critical(
                "The account's threshold will be reduced by %d"
                % (removed_weight)
            )
            authority["weight_threshold"] -= removed_weight
            self._test_weights_treshold(authority)

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            permission: authority,
            "extensions": {}
        })
        if permission == "owner":
            return self.finalizeOp(op, account["name"], "owner")
        else:
            return self.finalizeOp(op, account["name"], "active")

    def update_memo_key(self, key, account=None):
        """ Update an account's memo public key

            This method does **not** add any private keys to your
            wallet but merely changes the memo public key.

            :param str key: New memo public key
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        PublicKey(key, prefix=self.rpc.chain_params["prefix"])

        account = Account(account, muse_instance=self)
        account["options"]["memo_key"] = key
        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            "new_options": account["options"],
            "extensions": {}
        })
        return self.finalizeOp(op, account["name"], "active")

    def approvewitness(self, witnesses, account=None):
        """ Approve a witness

            :param list witnesses: list of Witness name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account, muse_instance=self)
        options = account["options"]

        if not isinstance(witnesses, (list, set)):
            witnesses = set(witnesses)

        for witness in witnesses:
            witness = Witness(witness, muse_instance=self)
            options["votes"].append(witness["vote_id"])

        options["votes"] = list(set(options["votes"]))
        options["num_witness"] = len(list(filter(
            lambda x: float(x.split(":")[0]) == 1,
            options["votes"]
        )))

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            "new_options": options,
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def disapprovewitness(self, witnesses, account=None):
        """ Disapprove a witness

            :param list witnesses: list of Witness name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account, muse_instance=self)
        options = account["options"]

        if not isinstance(witnesses, (list, set)):
            witnesses = set(witnesses)

        for witness in witnesses:
            witness = Witness(witness, muse_instance=self)
            if witness["vote_id"] in options["votes"]:
                options["votes"].remove(witness["vote_id"])

        options["votes"] = list(set(options["votes"]))
        options["num_witness"] = len(list(filter(
            lambda x: float(x.split(":")[0]) == 1,
            options["votes"]
        )))

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            "new_options": options,
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def approvecommittee(self, committees, account=None):
        """ Approve a committee

            :param list committees: list of committee member name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account, muse_instance=self)
        options = account["options"]

        if not isinstance(committees, (list, set)):
            committees = set(committees)

        for committee in committees:
            committee = Committee(committee, muse_instance=self)
            options["votes"].append(committee["vote_id"])

        options["votes"] = list(set(options["votes"]))
        options["num_committee"] = len(list(filter(
            lambda x: float(x.split(":")[0]) == 0,
            options["votes"]
        )))

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            "new_options": options,
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def disapprovecommittee(self, committees, account=None):
        """ Disapprove a committee

            :param list committees: list of committee name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account, muse_instance=self)
        options = account["options"]

        if not isinstance(committees, (list, set)):
            committees = set(committees)

        for committee in committees:
            committee = Committee(committee, muse_instance=self)
            if committee["vote_id"] in options["votes"]:
                options["votes"].remove(committee["vote_id"])

        options["votes"] = list(set(options["votes"]))
        options["num_committee"] = len(list(filter(
            lambda x: float(x.split(":")[0]) == 0,
            options["votes"]
        )))

        op = operations.Account_update(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account": account["id"],
            "new_options": options,
            "extensions": {},
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def cancel(self, orderNumber, account=None):
        """ Cancels an order you have placed in a given market. Requires
            only the "orderNumber". An order number takes the form
            ``1.7.xxx``.

            :param str orderNumber: The Order Object ide of the form ``1.7.xxxx``
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account, full=False, muse_instance=self)

        op = []
        for order in list(orderNumber):
            op.append(
                operations.Limit_order_cancel(**{
                    "fee": {"amount": 0, "asset_id": "1.3.0"},
                    "fee_paying_account": account["id"],
                    "order": order,
                    "extensions": [],
                    "prefix": self.rpc.chain_params["prefix"]}))
        return self.finalizeOp(op, account["name"], "active")

    def approveproposal(self, proposal_ids, account=None, approver=None):
        """ Approve Proposal

            :param list proposal_id: Ids of the proposals
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        from .proposal import Proposal
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        if not approver:
            approver = account
        else:
            approver = Account(approver)

        if not isinstance(proposal_ids, (list, set)):
            proposal_ids = set(proposal_ids)

        op = []
        for proposal_id in proposal_ids:
            proposal = Proposal(proposal_id, muse_instance=self)
            op.append(operations.Proposal_update(**{
                "fee": {"amount": 0, "asset_id": "1.3.0"},
                'fee_paying_account': account["id"],
                'proposal': proposal["id"],
                'active_approvals_to_add': [approver["id"]],
                "prefix": self.rpc.chain_params["prefix"]
            }))
        return self.finalizeOp(op, account["name"], "active")

    def disapproveproposal(self, proposal_ids, account=None, approver=None):
        """ Disapprove Proposal

            :param list proposal_ids: Id of the proposals
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        from .proposal import Proposal
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        if not approver:
            approver = account
        else:
            approver = Account(approver)

        if not isinstance(proposal_ids, (list, set)):
            proposal_ids = set(proposal_ids)

        op = []
        for proposal_id in proposal_ids:
            proposal = Proposal(proposal_id, muse_instance=self)
            op.append(operations.Proposal_update(**{
                "fee": {"amount": 0, "asset_id": "1.3.0"},
                'fee_paying_account': account["id"],
                'proposal': proposal["id"],
                'active_approvals_to_remove': [approver["id"]],
                "prefix": self.rpc.chain_params["prefix"]
            }))
        return self.finalizeOp(op, account["name"], "active")

    def upgrade_account(self, account=None):
        """ Upgrade an account to Lifetime membership

            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        op = operations.Account_upgrade(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "account_to_upgrade": account["id"],
            "upgrade_to_lifetime_member": True,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def sport_create(self, names, account=None):
        """ Create a sport. This needs to be **proposed**.

            :param list names: Internationalized names, e.g. ``[['de', 'Foo'], ['en', 'bar']]``
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'sport_create' needs to be proposed"
        assert isinstance(names, list)
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        op = operations.Sport_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "name": names,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def competitor_create(self, names, sport_id="0.0.0", account=None):
        """ Create a competitor. This needs to be **proposed**.

            :param list names: Internationalized names, e.g. ``[['de', 'Foo'], ['en', 'bar']]``
            :param str sport_id: Sport ID to create the competitors for (defaults to *relative* id ``0.0.0``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'competitor_create' needs to be proposed"
        assert isinstance(names, list)
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        op = operations.Competitor_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "name": names,
            "sport_id": sport_id,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def event_group_create(self, names, sport_id="0.0.0", account=None):
        """ Create an event group. This needs to be **proposed**.

            :param list names: Internationalized names, e.g. ``[['de', 'Foo'], ['en', 'bar']]``
            :param str sport_id: Sport ID to create the competitors for (defaults to *relative* id ``0.0.0``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'event_group_create' needs to be proposed"
        assert isinstance(names, list)
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        op = operations.Event_group_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "name": names,
            "sport_id": sport_id,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def event_create(
        self,
        season,
        start_time,
        competitors,
        event_group_id="0.0.0",
        account=None
    ):
        """ Create an event. This needs to be **proposed**.

            :param list season: Internationalized names, e.g. ``[['de', 'Foo'], ['en', 'bar']]``
            :param list competitors: List of (*relative*) ids of the competitors
            :param str event_group_id: Event group ID to create the competitors for (defaults to *relative* id ``0.0.0``)
            :param datetime start_time: Time of the start of the event
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'event_create' needs to be proposed"
        assert isinstance(season, list)
        assert isinstance(competitors, list)
        assert isinstance(start_time, datetime), "start_time needs to be a `datetime.datetime`"
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        op = operations.Event_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "season": season,
            "start_time": formatTime(start_time),
            "event_group_id": event_group_id,
            "competitors": competitors,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def betting_market_group_create(self, type, margin=0, score=0, event_id="0.0.0", account=None):
        """ Create an betting market. This needs to be **proposed**.

            :param str type: One of ``moneyline``, ``spread``, ``overunder``
            :param str event_id: Event ID to create the competitors for (defaults to *relative* id ``0.0.0``)
            :param int margin: Margin for ``spread`` types
            :param int score: Score for ``overunder`` types
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'betting_market_create' needs to be proposed"
        assert type in ["moneyline", "spread", "overunder"], "invalid type"
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)

        if type == "moneyline":
            options = [0, {}]
        elif type == "spread":
            options = [1, {"margin": margin}]
        elif type == "overunder":
            options = [2, {"score": score}]

        op = operations.Betting_market_group_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "event_id": event_id,
            "options": options,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def betting_market_create(
        self,
        payout_condition,
        asset,
        group_id="0.0.0",
        account=None
    ):
        """ Create an event group. This needs to be **proposed**.

            :param list payout_condition: Internationalized names, e.g. ``[['de', 'Foo'], ['en', 'bar']]``
            :param muse.asset.Asset asset: Asset to be used for this market
            :param str group_id: Group ID to create the competitors for (defaults to *relative* id ``0.0.0``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'betting_market_create' needs to be proposed"
        assert isinstance(payout_condition, list)
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)
        asset = Asset(asset)
        op = operations.Betting_market_create(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "group_id": group_id,
            "payout_condition": payout_condition,
            "asset_id": asset["id"],
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")

    def resolve_betting_market(self, market_id, result, account=None):
        """ Create an betting market. This needs to be **proposed**.

            :param str market_id: Market ID to resolve
            :param int result: Result of the market (``win``, ``not_win``, or ``cancel``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert self.proposer, "'betting_market_create' needs to be proposed"
        assert result in ["win", "not_win", "cancel"], "invalid result"
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        account = Account(account)

        op = operations.Betting_market_resolve(**{
            "fee": {"amount": 0, "asset_id": "1.3.0"},
            "betting_market_id": market_id,
            "resolution": result,
            "prefix": self.rpc.chain_params["prefix"]
        })
        return self.finalizeOp(op, account["name"], "active")
