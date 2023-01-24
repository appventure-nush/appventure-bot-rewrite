import logging
import time
import uuid
from textwrap import dedent
from typing import MutableMapping, Tuple, Union

import orjson
import requests
from github import Github
from nextcord import ButtonStyle, Interaction, Member
from nextcord.ext import tasks
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View
from werkzeug.datastructures import MultiDict

from config import config
from utils.access_control_decorators import is_in_server, subcommand
from utils.database import database
from utils.error import send_error

from .cache import Cache

logger = logging.getLogger(__name__)


class GithubAuth(Cog, name="GithubAuth"):
    __slots__ = "bot", "cache", "github_accts", "github_pending_auth_flows"

    def __init__(self, bot: Bot, cache: Cache) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache
        self.github_accts: MutableMapping[str, str] = {}  # discord id (as str) -> github name
        self.github_auth_flows: MutableMapping[str, Tuple[int, int]] = {}  # state -> timestamp, discord id

        self.load_data()

    @is_in_server()
    async def gh(self, _: Interaction) -> None:
        pass

    @subcommand(gh, description="Link with your GitHub account")
    async def verify(self, interaction: Interaction) -> None:
        if not interaction.user:
            raise RuntimeError("Interaction had no user!")

        member = self.cache.guild.get_member(interaction.user.id)
        if not member:
            raise RuntimeError("User not in AppVenture server, is permission check correct?")

        member_in_database = database.get_member_by_discord_id(member.id)
        is_appventure_member = self.cache.member_role in member.roles
        if is_appventure_member and not member_in_database:
            # appventure member; doesn't have MS linked
            return await send_error(interaction, "Please link your Microsoft email first, by running `/ms verify`!")

        # check already added github
        if (not is_appventure_member and str(member.id) in self.github_accts) or (
            member_in_database and member_in_database.github
        ):
            return await send_error(interaction, "You have already linked your GitHub account!")

        # generate auth flow
        state = uuid.uuid4().hex
        github_link = f"https://github.com/login/oauth/authorize?client_id={config.github_client_id}&state={state}"

        # add to pending auth flows
        self.github_auth_flows[state] = (int(time.time()), member.id)

        # generate message
        buttons = View()
        buttons.add_item(Button(label="Verify Github!", url=github_link, style=ButtonStyle.green))
        github_message = dedent(
            """
            Please click the button below to link your GitHub account!
            The link is valid for 1 day; run `/gh verify` again to get a new link.
            """
        )

        await interaction.send(content=github_message, view=buttons, ephemeral=True)

    async def on_gh_auth_response(self, params: MultiDict[str, str]) -> Union[str, Tuple[str, int]]:
        _, member_id = self.github_auth_flows.get(params.get("state", ""), (0, None))
        if not member_id or not (github_code := params.get("code", None)):
            return "Not found in pending requests, try running <code>/gh verify</code> again", 404

        response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": config.github_client_id,
                "client_secret": config.github_client_secret,
                "code": github_code,
            },
            headers={"Accept": "application/json"},
        )
        if not response.ok:
            return (
                "Github returned an error: " + response.text + "\nTry running <code>/gh verify</code> again",
                500,
            )

        del self.github_auth_flows[params["state"]]

        # get their name
        github_user = Github(response.json()["access_token"]).get_user()
        github_username = github_user.login
        github_display_name = github_user.name

        appventure_member = self.cache.guild.get_member(member_id)
        if not appventure_member:
            return "You're not in the AppVenture server, please join and try again", 400

        await self.do_verification(appventure_member, github_username, github_display_name)

        return "Successfully linked with Github!"

    async def do_verification(self, appventure_member: Member, github_username: str, github_display_name: str) -> None:
        member = database.get_member_by_discord_id(appventure_member.id)
        if member:
            # is (or was) AppVenture member
            database.set_github(str(member.email), github_username)
        else:
            # store in json
            self.github_accts[str(appventure_member.id)] = github_username

        await appventure_member.send(
            f"Your GitHub account, `{github_display_name} (@{github_username})`, is successfully linked!"
        )

    def load_data(self):
        try:
            with open("storage/github_auth_flows.json", "rb") as f:
                data = f.read()
        except FileNotFoundError:
            data = b"{}"

        self.github_auth_flows: MutableMapping[str, Tuple[int, int]] = orjson.loads(data)

        try:
            with open("storage/github_accts.json", "rb") as f:
                data = f.read()
        except FileNotFoundError:
            data = b"{}"

        self.github_accts: MutableMapping[str, str] = orjson.loads(data)

        logger.info(
            f"Loaded {len(self.github_auth_flows)} pending auth flows & {len(self.github_accts)} github accounts"
        )

        self.save_data_loop.start()

    def prune_auth_flows(self) -> None:
        current_time = time.time()
        new_auth_flows: MutableMapping[str, Tuple[int, int]] = {}
        for key, auth_flow_data in self.github_auth_flows.items():
            if current_time - auth_flow_data[0] < 86400:
                new_auth_flows[key] = auth_flow_data
        self.github_auth_flows = new_auth_flows

    def save_data(self) -> None:
        self.prune_auth_flows()
        logger.info(
            f"Saving {len(self.github_auth_flows)} pending auth flows & {len(self.github_accts)} github accounts"
        )

        with open("storage/github_auth_flows.json", "wb") as f:
            f.write(orjson.dumps(self.github_auth_flows))
        with open("storage/github_accts.json", "wb") as f:
            f.write(orjson.dumps(self.github_accts))

    @tasks.loop(minutes=5)
    async def save_data_loop(self) -> None:
        self.save_data()

    @save_data_loop.after_loop
    async def save_data_on_shutdown(self) -> None:
        self.save_data()

    def cog_unload(self) -> None:
        self.save_data_loop.cancel()
        return super().cog_unload()


__all__ = ["GithubAuth"]
