import logging

import uvloop
from cogs import (
    Cache,
    GithubAuth,
    JSONCache,
    MemberManagement,
    MSAuth,
    Nick,
    Projects,
    UIHelper,
)
from config import config
from nextcord import Intents
from nextcord.ext import ipc
from nextcord.ext.commands import Bot


def do_on_shutdown():
    raise KeyboardInterrupt


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    uvloop.install()

    intents = Intents.default()
    intents.members = True

    bot = Bot(intents=intents)

    bot.add_cog(cache := Cache(bot))

    ipc_server = ipc.server.Server(bot, host="0.0.0.0", secret_key=config.ipc_secret)

    bot.add_cog(json_cache := JSONCache(bot))
    bot.add_cog(ui_helper := UIHelper(bot, json_cache))
    bot.add_cog(MSAuth(bot, cache, ui_helper, json_cache))
    bot.add_cog(github_auth := GithubAuth(bot, cache, json_cache))
    bot.add_cog(MemberManagement(bot, cache))
    bot.add_cog(Nick(bot, cache, ui_helper))
    bot.add_cog(Projects(bot, cache, ui_helper, github_auth))

    ipc_server.start()

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
