import click
from muse.storage import configStorage as config
from .ui import (
    print_version,
)


@click.group()
@click.option(
    '--debug/--no-debug',
    default=False,
    help="Enable/Disable Debugging (no-broadcasting mode)"
)
@click.option(
    '--node',
    type=str,
    default=config["node"],
    help='Websocket URL for public muse API (default: "wss://t.b.d./")'
)
@click.option(
    '--rpcuser',
    type=str,
    default=config["rpcuser"],
    help='Websocket user if authentication is required'
)
@click.option(
    '--rpcpassword',
    type=str,
    default=config["rpcpassword"],
    help='Websocket password if authentication is required')
@click.option(
    '--nobroadcast/--broadcast',
    '-d',
    default=False,
    help='Do not broadcast anything')
@click.option(
    '--unsigned/--signed',
    '-x',
    default=False,
    help='Do not try to sign the transaction')
@click.option(
    '--expires',
    '-e',
    default=30,
    help='Expiration time in seconds (defaults to 30)')
@click.option(
    '--verbose',
    '-v',
    type=int,
    default=3,
    help='Verbosity (0-15)')
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show version")
@click.pass_context
def main(ctx, **kwargs):
    ctx.obj = {}
    for k, v in kwargs.items():
        ctx.obj[k] = v
