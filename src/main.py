import logging

import uvloop
from nextcord.ext.commands import Bot

from cogs.member_commands import MemberCommands
from config import config

from nextcord import Intents

def main() -> None:
    uvloop.install()

    logging.basicConfig(level=logging.INFO)

    intents = Intents.default()
    intents.members = True

    bot = Bot(intents=intents)

    bot.add_cog(MemberCommands(bot))

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
