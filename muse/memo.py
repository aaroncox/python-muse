from muse.instance import shared_muse_instance
import random
from musebase import memo as MUSEMemo
from musebase.account import PrivateKey, PublicKey
from .account import Account
from .exceptions import MissingKeyError


class Memo(object):
    """ Deals with Memos that are attached to a transfer

        :param muse.account.Account from_account: Account that has sent the memo
        :param muse.account.Account to_account: Account that has received the memo
        :param muse.muse.muse muse_instance: muse instance

        A memo is encrypted with a shared secret derived from a private key of
        the sender and a public key of the receiver. Due to the underlying
        mathematics, the same shared secret can be derived by the private key
        of the receiver and the public key of the sender. The encrypted message
        is perturbed by a nonce that is part of the transmitted message.

        .. code-block:: python

            from muse.memo import Memo
            m = Memo("museeu", "wallet.xeroc")
            enc = (m.encrypt("foobar"))
            print(enc)
            >> {'nonce': '17329630356955254641', 'message': '8563e2bb2976e0217806d642901a2855'}
            print(m.decrypt(enc))
            >> foobar

    """
    def __init__(
        self,
        from_account,
        to_account,
        muse_instance=None
    ):

        self.muse = muse_instance or shared_muse_instance()

        self.to_account = Account(to_account, muse_instance=self.muse)
        self.from_account = Account(from_account, muse_instance=self.muse)

    def encrypt(self, memo):
        """ Encrypt a memo

            :param str memo: clear text memo message
            :returns: encrypted memo
            :rtype: str
        """
        if not memo:
            return None

        nonce = str(random.getrandbits(64))
        memo_wif = self.muse.wallet.getPrivateKeyForPublicKey(
            self.from_account["options"]["memo_key"]
        )
        if not memo_wif:
            raise MissingKeyError("Memo key for %s missing!" % self.from_account["name"])

        enc = MUSEMemo.encode_memo(
            PrivateKey(memo_wif),
            PublicKey(
                self.to_account["options"]["memo_key"],
                prefix=self.muse.rpc.chain_params["prefix"]
            ),
            nonce,
            memo
        )

        return {
            "message": enc,
            "nonce": nonce,
            "from": self.from_account["options"]["memo_key"],
            "to": self.to_account["options"]["memo_key"]
        }

    def decrypt(self, memo):
        """ Decrypt a memo

            :param str memo: encrypted memo message
            :returns: encrypted memo
            :rtype: str
        """
        if not memo:
            return None

        memo_wif = self.muse.wallet.getPrivateKeyForPublicKey(
            self.to_account["options"]["memo_key"]
        )
        if not memo_wif:
            raise MissingKeyError("Memo key for %s missing!" % self.to_account["name"])

        # TODO: Use pubkeys of the message, not pubkeys of account!
        print(
            PrivateKey(memo_wif),
            PublicKey(
                self.from_account["options"]["memo_key"],
                prefix=self.muse.rpc.chain_params["prefix"]
            ),
            memo.get("nonce"),
            memo.get("message")
        )
        return MUSEMemo.decode_memo(
            PrivateKey(memo_wif),
            PublicKey(
                self.from_account["options"]["memo_key"],
                prefix=self.muse.rpc.chain_params["prefix"]
            ),
            memo.get("nonce"),
            memo.get("message")
        )
