import logging
from typing import Any, Coroutine

from nextcord import Intents
from nextcord.ext.commands import Bot

from bot.cogs import Cache, GithubAuth, MemberManagement, MSAuth, Nick, UIHelper
from config import config
from server import server


def do_on_shutdown():
    raise KeyboardInterrupt


def main(server_coroutine: Coroutine[Any, Any, None]) -> None:
    logging.basicConfig(level=logging.INFO)

    intents = Intents.default()
    intents.members = True

    bot = Bot(intents=intents)

    bot.add_cog(cache := Cache(bot))
    bot.add_cog(ui_helper := UIHelper(bot))
    bot.add_cog(MSAuth(bot, cache, ui_helper))
    bot.add_cog(GithubAuth(bot))
    bot.add_cog(MemberManagement(bot, cache))
    bot.add_cog(Nick(bot, cache, ui_helper))

    server.set_bot(bot)

    task = bot.loop.create_task(server_coroutine)
    task.add_done_callback(lambda _: do_on_shutdown())

    bot.run(config.discord_token)


__all__ = ["main"]
