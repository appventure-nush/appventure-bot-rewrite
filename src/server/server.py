import logging
from typing import Optional

from nextcord.ext.commands import Bot
from quart import Quart, redirect, request

from bot.cogs import GithubAuth, MSAuth

app = Quart(__name__)

bot = None

logger = logging.getLogger(__name__)


def set_bot(discord_bot: Bot) -> None:
    global bot
    bot = discord_bot
    logger.info("Linked to discord bot")


def get_ms_auth_handler() -> Optional[MSAuth]:
    if not bot:
        logger.error("No bot set")
        return None

    cog = bot.get_cog("MSAuth")
    if not isinstance(cog, MSAuth):
        logger.error("Cog is not MSAuth, or cog doesn't exist")
        return None

    return cog


def get_gh_auth_handler() -> Optional[GithubAuth]:
    if not bot:
        logger.error("No bot set")
        return None

    cog = bot.get_cog("GithubAuth")
    if not isinstance(cog, GithubAuth):
        logger.error("Cog is not GithubAuth, or cog doesn't exist")
        return None

    return cog


@app.route("/", methods=["GET", "POST"])
async def ms_auth_result():
    if request.method == "GET":
        return "Hello! This is for the AppVenture bot.", 405

    if not (handler := get_ms_auth_handler()):
        return "Internal server error, please contact exco", 500

    return await handler.on_ms_auth_response(await request.form)


@app.route("/ms_auth", methods=["GET"])
async def redirect_to_ms_auth():
    if not (handler := get_ms_auth_handler()):
        return "Internal server error, please contact exco", 500

    if not (state := request.args.get("state")) or not (link := handler.get_real_ms_auth_link(state)):
        return "Invalid request, try running <code>/ms verify</code> again", 400

    return redirect(link)


@app.route("/github", methods=["GET"])
async def do_github_auth():
    if not (handler := get_gh_auth_handler()):
        return "Internal server error, please contact exco", 500

    return await handler.on_gh_auth_response(request.args)


__all__ = ["app"]
