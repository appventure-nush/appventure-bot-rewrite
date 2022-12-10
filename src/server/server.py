import logging
from typing import Optional

from nextcord.ext.commands import Bot
from quart import Quart, redirect, request

from bot.cogs.ms_auth import MSAuth

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


@app.route("/", methods=["POST"])
async def ms_auth_result():
    if not (handler := get_ms_auth_handler()):
        return "Internal server error, please contact ExCo", 500

    return str(await handler.on_ms_auth_response(await request.form))


@app.route("/ms_auth", methods=["GET"])
async def redirect_to_ms_auth():
    if not (handler := get_ms_auth_handler()):
        return "Internal server error, please contact ExCo", 500

    if not (state := request.args.get("state")) or not (link := handler.get_real_ms_auth_link(state)):
        return "Invalid request, try running <code>/ms verify</code> again", 400

    return redirect(link)


__all__ = ["app"]
