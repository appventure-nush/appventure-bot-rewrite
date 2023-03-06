import logging

from config import config
from nextcord.ext.ipc.client import Client
from quart import Quart, redirect, request

app = Quart(__name__)
ipc_client = Client(host="bot", secret_key=config.ipc_secret)

logger = logging.getLogger(__name__)


@app.route("/", methods=["GET", "POST"])
async def ms_auth_result():
    if request.method == "GET":
        return "Hello! This is for the AppVenture bot.", 405

    resp = await ipc_client.request(endpoint="on_ms_auth_response", response=dict(await request.form))
    if isinstance(resp, list):
        resp = tuple(resp)
    return resp


@app.route("/ms_auth", methods=["GET"])
async def redirect_to_ms_auth():
    if not (state := request.args.get("state")):
        return "Invalid request, try running <code>/ms verify</code> again", 400

    link = await ipc_client.request(endpoint="get_real_ms_auth_link", state=state)
    if link is None:
        return "Invalid request, try running <code>/ms verify</code> again", 400
    elif not link:
        return "Internal IPC error, contact exco", 500

    return redirect(link)


@app.route("/github", methods=["GET"])
async def do_github_auth():
    resp = await ipc_client.request(endpoint="on_gh_auth_response", response=dict(request.args))
    if isinstance(resp, list):
        resp = tuple(resp)
    return resp


__all__ = ["app"]
