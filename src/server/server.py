from quart import Quart, request

from utils.ms_auth import on_ms_auth_response

app = Quart(__name__)


@app.route("/")
def ms_auth():
    return str(on_ms_auth_response(request.args))


__all__ = ["app"]
