import logging
import time
import uuid
from textwrap import dedent
from typing import Any, Literal, MutableMapping, Optional, Tuple, Union

import msal
import requests
from config import config
from nextcord import ButtonStyle, Interaction, Member, SlashOption, User
from nextcord.ext import ipc
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View
from utils import emojis
from utils.access_control_decorators import check_is_exco, is_in_server, subcommand
from utils.database import database
from utils.error import send_error, send_no_permission

from .cache import Cache
from .json_cache import JSONCache
from .ui_helper import ButtonCallback, UIHelper

logger = logging.getLogger(__name__)


class MSAuth(Cog, name="MSAuth"):
    __slots__ = "application", "auth_flows", "bot", "cache", "ui_helper"

    def __init__(self, bot: Bot, cache: Cache, ui_helper: UIHelper, json_cache: JSONCache) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache
        self.ui_helper = ui_helper

        self.application = msal.PublicClientApplication(
            client_id=config.ms_auth_client_id,
            authority=f"https://login.microsoftonline.com/{config.ms_auth_tenant_id}",
        )

        self.auth_flows: MutableMapping[str, Tuple[int, int, Any]] = json_cache.register_cache(
            "auth_flows", self.prune_auth_flows
        )  # state -> timestamp, discord id, flow

        self.ui_helper.register_callback("accept-join-alumni", self.accept_as_alumni_wrapper)
        self.ui_helper.register_callback("accept-join-guest", self.accept_as_guest_wrapper)
        self.ui_helper.register_callback("reject-join", self.reject_wrapper)

    def accept_as_alumni_wrapper(self, requester_id: Any) -> ButtonCallback:
        if not isinstance(requester_id, int):
            raise ValueError("Invalid values passed!")

        async def callback(interaction: Interaction) -> None:
            requester = self.cache.guild.get_member(requester_id)
            if not requester:
                await interaction.edit(content="User no longer in server!", view=None)
                return

            if not interaction.user or isinstance(interaction.user, User):
                raise RuntimeError("Interaction had invalid user!")

            if not interaction.message:
                raise RuntimeError("Interaction had no message?")

            if not interaction.user.get_role(config.exco_role):
                return await send_no_permission(interaction)

            await interaction.edit(
                content=f"{interaction.user.mention} has accepted {requester.mention}'s request to join as alumni.",
                view=None,
            )

            await requester.add_roles(self.cache.alumni_role)

            await requester.send(f"Welcome back to AppVenture, {requester.display_name}!")

        return callback

    def accept_as_guest_wrapper(self, requester_id: Any) -> ButtonCallback:
        if not isinstance(requester_id, int):
            raise ValueError("Invalid values passed!")

        async def callback(interaction: Interaction) -> None:
            requester = self.cache.guild.get_member(requester_id)
            if not requester:
                await interaction.edit(content="User no longer in server!", view=None)
                return

            if not interaction.user or isinstance(interaction.user, User):
                raise RuntimeError("Interaction had invalid user!")

            if not interaction.message:
                raise RuntimeError("Interaction had no message?")

            if not interaction.user.get_role(config.exco_role):
                return await send_no_permission(interaction)

            await interaction.edit(
                content=f"{interaction.user.mention} has accepted {requester.mention}'s request to join as guest.",
                view=None,
            )

            await requester.add_roles(self.cache.guest_role)

            await requester.send(f"Welcome to AppVenture as a guest, {requester.display_name}!")

        return callback

    def reject_wrapper(self, requester_id: Any) -> ButtonCallback:
        if not isinstance(requester_id, int):
            raise ValueError("Invalid values passed!")

        async def callback(interaction: Interaction) -> None:
            requester = self.cache.guild.get_member(requester_id)
            if not requester:
                await interaction.edit(content="User no longer in server!", view=None)
                return

            if not interaction.user or isinstance(interaction.user, User):
                raise RuntimeError("Interaction had invalid user!")

            if not interaction.message:
                raise RuntimeError("Interaction had no message?")

            if not interaction.user.get_role(config.exco_role):
                return await send_no_permission(interaction)

            await interaction.edit(
                content=f"{interaction.user.mention} has rejected {requester.mention}'s request to join the server.",
                view=None,
            )

            await requester.send("An exco rejected your join application.")

            await requester.kick()

        return callback

    @ipc.server.route()
    async def get_real_ms_auth_link(self, data) -> Optional[Union[str, Literal[False]]]:
        try:
            state = data.state
        except AttributeError:
            return False

        return self.auth_flows.get(state, (0, 0, {}))[2].get("auth_uri")

    def get_ms_auth_link(self, member_id: int) -> str:
        while (state := uuid.uuid4().hex) in self.auth_flows:
            pass

        auth_flow = self.application.initiate_auth_code_flow(
            scopes=["User.Read"],
            redirect_uri=f"{config.ms_auth_redirect_domain}",
            state=state,
            response_mode="form_post",
        )

        self.auth_flows[state] = (int(time.time()), member_id, auth_flow)

        return f"{config.ms_auth_redirect_domain}ms_auth?state={state}"

    @ipc.server.route()
    async def on_ms_auth_response(self, data) -> Union[str, Tuple[str, int]]:
        try:
            params = data.response
        except AttributeError:
            return "Internal IPC error, contact exco", 500

        _, member_id, auth_flow = self.auth_flows.get(params.get("state", ""), (0, 0, None))
        if not auth_flow:
            return "Not found in pending requests, try running <code>/ms verify</code> again", 404

        response = self.application.acquire_token_by_auth_code_flow(auth_flow, params)
        if response.get("error"):
            return (
                response.get("error_description", "Unknown Microsoft error")
                + "\nTry running <code>/ms verify</code> again",
                500,
            )

        del self.auth_flows[params["state"]]

        # get their email and name
        user_data = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": "Bearer " + response["access_token"]},
        ).json()

        email: str = user_data.get("mail")
        if not email:
            return "Could not get your email from Microsoft, try running <code>/ms verify</code> again", 500

        name: str = user_data.get("displayName").title()
        if not name:
            return "Could not get your name from Microsoft, try running <code>/ms verify</code> again", 500

        appventure_member = self.cache.guild.get_member(member_id)
        if not appventure_member:
            return "You're not in the AppVenture server, please join and try again", 400

        await self.do_verification(email, appventure_member, name)

        return "Successfully linked with Microsoft!"

    async def do_verification(self, email: str, appventure_member: Member, name: str) -> None:
        member = database.get_member_by_email(email)
        if member:
            # is AppVenture member
            database.set_discord(email, appventure_member.id)
            await appventure_member.add_roles(self.cache.member_role)
            await appventure_member.send(f"Welcome, {name}, to AppVenture!")
        else:
            responses = View(timeout=None, auto_defer=False)
            responses.add_item(
                self.ui_helper.get_button(
                    callback_name="accept-join-alumni",
                    callback_args=(appventure_member.id,),
                    label="Join as Alumni",
                    emoji=emojis.hat,
                    style=ButtonStyle.green,
                )
            )
            responses.add_item(
                self.ui_helper.get_button(
                    callback_name="accept-join-guest",
                    callback_args=(appventure_member.id,),
                    label="Join as Guest",
                    emoji=emojis.tick,
                    style=ButtonStyle.green,
                )
            )
            responses.add_item(
                self.ui_helper.get_button(
                    callback_name="reject-join",
                    callback_args=(appventure_member.id,),
                    label="Deny",
                    emoji=emojis.cross,
                    style=ButtonStyle.red,
                )
            )
            await self.cache.exco_channel.send(
                f"{name} ({appventure_member.mention}) is requesting to join the server.", view=responses
            )
            await appventure_member.send(
                "As you're not a current AppVenture member, your join request has been forwarded to current exco."
            )

        await appventure_member.edit(nick=name)

    def get_verify_message(self, member_id: int) -> Tuple[str, View]:
        link = self.get_ms_auth_link(member_id)

        buttons = View()
        buttons.add_item(Button(url=link, label="Verify!", style=ButtonStyle.green))

        return (
            dedent(
                """
                Welcome to the AppVenture Discord!

                To complete verification, click the button and follow the instructions.
                The link is valid for 1 day.
                Alternatively, you can DM any exco to complete verification manually, or run `/ms verify` for a new link.
                """
            ),
            buttons,
        )

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        if member.guild != self.cache.guild:
            return  # do nothing

        message = self.get_verify_message(member.id)

        await member.send(content=message[0], view=message[1])

    @is_in_server()
    async def ms(self, _: Interaction) -> None:
        pass

    @subcommand(ms, description="Start the verification process, if you are not verified yet")
    async def verify(self, interaction: Interaction) -> None:
        if not interaction.user:
            raise RuntimeError("Interaction had no user!")

        member = self.cache.guild.get_member(interaction.user.id)
        if not member:
            raise RuntimeError("User not in AppVenture server, is permission check correct?")

        if (
            database.get_member_by_discord_id(member.id)
            or len({self.cache.alumni_role, self.cache.guest_role}.intersection(member.roles)) > 0
        ):
            return await send_error(interaction, "You are already verified!", ephemeral=True)

        message = self.get_verify_message(interaction.user.id)

        await interaction.send(content=message[0], view=message[1], ephemeral=True)

    @subcommand(ms, description="Manually verify a user", inherit_hooks=False)
    @check_is_exco()
    async def manual_verify(
        self,
        interaction: Interaction,
        user: Member = SlashOption(description="Who to verify", required=True),
        email: str = SlashOption(description="Full NUSH email of the user", required=True),
        name: str = SlashOption(description="Full name of the user", required=True),
    ) -> None:
        if not interaction.user:
            raise RuntimeError("Interaction had no user!")

        if len({self.cache.member_role, self.cache.alumni_role, self.cache.guest_role}.intersection(user.roles)) > 0:
            return await send_error(interaction, "User is already verified!", ephemeral=True)

        await self.do_verification(email, user, name)

        await interaction.send(f"Successful manual verification of {name}!", ephemeral=True)

    def prune_auth_flows(self, auth_flows: MutableMapping[str, Tuple[int, int, Any]]) -> None:
        current_time = time.time()
        current_auth_flows: MutableMapping[str, Tuple[int, int, Any]] = auth_flows
        # wrap in list to create a copy of items (we modify the dict in the loop)
        for key, auth_flow_data in list(current_auth_flows.items()):
            if current_time - auth_flow_data[0] >= 86400:
                del auth_flows[key]


__all__ = ["MSAuth"]
