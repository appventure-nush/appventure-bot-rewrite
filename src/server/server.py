from typing import Optional

from quart import Quart, request

from bot.cogs.ms_auth import MSAuth

app = Quart(__name__)

ms_auth_handler: Optional[MSAuth] = None


def set_ms_auth_handler(handler: MSAuth) -> None:
    global ms_auth_handler
    ms_auth_handler = handler


@app.route("/", methods=["POST"])
async def ms_auth_result():
    if not ms_auth_handler:
        return "Internal server error, please contact ExCo", 500

    return str(await ms_auth_handler.on_ms_auth_response(await request.form))


__all__ = ["app"]
