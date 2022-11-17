from quart import Quart

app = Quart(__name__)


@app.route("/")
def ms_auth():
    # on_ms_auth_response(request.args)
    return ""


__all__ = ["app"]
