import logging
import time
import uuid
from textwrap import dedent
from typing import MutableMapping, Optional, Tuple, Union

import requests
from config import config
from github import Github
from nextcord import ButtonStyle, Interaction, Member
from nextcord.ext import ipc
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View
from utils.access_control_decorators import is_in_server, subcommand
from utils.database import database
from utils.error import send_error

from .cache import Cache
from .json_cache import JSONCache

logger = logging.getLogger(__name__)


class GithubAuth(Cog, name="GithubAuth"):
    __slots__ = "bot", "cache", "github_auth_flows"

    def __init__(self, bot: Bot, cache: Cache, json_cache: JSONCache) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache
        self.github_auth_flows: MutableMapping[str, Tuple[int, int]] = json_cache.register_cache(
            "github_auth_flows", self.prune_auth_flows
        )  # state -> timestamp, discord id

    # convenience function: get github name from discord id
    async def get_github_name(self, discord_id: int) -> Optional[str]:
        return (entry := database.get_github(discord_id)) and str(entry.github)

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
            return await send_error(
                interaction, "Please link your Microsoft email first, by running `/ms verify`!", ephemeral=True
            )

        # check already added github
        if await self.get_github_name(member.id):
            return await send_error(interaction, "You have already linked your GitHub account!", ephemeral=True)

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

    @ipc.server.route()
    async def on_gh_auth_response(self, data) -> Union[str, Tuple[str, int]]:
        try:
            params = data.response
        except AttributeError:
            return "Internal IPC error, contact exco", 500

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
        github_display_name = github_user.name or github_username

        appventure_member = self.cache.guild.get_member(member_id)
        if not appventure_member:
            return "You're not in the AppVenture server, please join and try again", 400

        await self.do_verification(appventure_member, github_username, github_display_name)

        return "Successfully linked with Github!"

    async def do_verification(self, appventure_member: Member, github_username: str, github_display_name: str) -> None:
        database.set_github(appventure_member.id, github_username)

        await appventure_member.send(
            f"Your GitHub account, `{github_display_name} (@{github_username})`, is successfully linked!"
        )

    def prune_auth_flows(self, github_auth_flows: MutableMapping[str, Tuple[int, int]]) -> None:
        current_time = time.time()
        current_auth_flows = github_auth_flows
        for key, auth_flow_data in list(current_auth_flows.items()):
            if current_time - auth_flow_data[0] >= 86400:
                del github_auth_flows[key]


__all__ = ["GithubAuth"]
