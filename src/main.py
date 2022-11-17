import logging

import uvloop
from nextcord import Intents
from nextcord.ext.commands import Bot

from cogs import Cache, MemberManagement, Nick
from config import config


def main() -> None:
    uvloop.install()

    logging.basicConfig(level=logging.INFO)

    intents = Intents.default()
    intents.members = True

    bot = Bot(intents=intents)

    bot.add_cog(cache := Cache(bot))
    bot.add_cog(MemberManagement(bot, cache))
    bot.add_cog(Nick(bot, cache))

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
