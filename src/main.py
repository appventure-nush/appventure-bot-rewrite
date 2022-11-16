import nextcord
import uvloop
from nextcord.ext import commands

from config import config


def main() -> None:
    uvloop.install()

    bot = commands.Bot()

    bot.run(config.discord_token)

if __name__ == '__main__':
    main()
