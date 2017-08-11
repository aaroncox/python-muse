import os
import json
import sys
from muse.account import Account
from prettytable import PrettyTable, ALL as allBorders
import pkg_resources
import click
import logging
log = logging.getLogger(__name__)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('{prog} {version}'.format(
        prog=pkg_resources.require("muse")[0].project_name,
        version=pkg_resources.require("muse")[0].version
    ))
    ctx.exit()


def print_permissions(account):
    t = PrettyTable(["Permission", "Threshold", "Key/Account"], hrules=allBorders)
    t.align = "r"
    for permission in ["owner", "active"]:
        auths = []
        # account auths:
        for authority in account[permission]["account_auths"]:
            auths.append("%s (%d)" % (Account(authority[0])["name"], authority[1]))
        # key auths:
        for authority in account[permission]["key_auths"]:
            auths.append("%s (%d)" % (authority[0], authority[1]))
        t.add_row([
            permission,
            account[permission]["weight_threshold"],
            "\n".join(auths),
        ])
    print(t)


def get_terminal(text="Password", confirm=False, allowedempty=False):
    import getpass
    while True:
        pw = getpass.getpass(text)
        if not pw and not allowedempty:
            print("Cannot be empty!")
            continue
        else:
            if not confirm:
                break
            pwck = getpass.getpass(
                "Confirm " + text
            )
            if (pw == pwck):
                break
            else:
                print("Not matching!")
    return pw


def pprintOperation(op):
    return json.dumps(op["op"][1], indent=4)
