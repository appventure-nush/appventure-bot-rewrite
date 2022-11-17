import logging
from typing import Any, Coroutine

from nextcord import Intents
from nextcord.ext.commands import Bot

from bot.cogs import Cache, MemberManagement, Nick, Verify
from config import config


def main(server_coroutine: Coroutine[Any, Any, None]) -> None:
    logging.basicConfig(level=logging.INFO)

    intents = Intents.default()
    intents.members = True

    bot = Bot(intents=intents)

    bot.add_cog(cache := Cache(bot))
    bot.add_cog(MemberManagement(bot, cache))
    bot.add_cog(Nick(bot, cache))
    bot.add_cog(Verify(bot, cache))

    task = bot.loop.create_task(server_coroutine)
    task.add_done_callback(lambda _: bot.loop.stop())

    bot.run(config.discord_token)


__all__ = ["main"]
