import logging
from typing import Any

from nextcord import ButtonStyle, Forbidden, Interaction, SlashOption, User
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import View

from config import config
from utils import emojis
from utils.access_control_decorators import member_command
from utils.error import send_error, send_no_permission

from .cache import Cache
from .ui_helper import ButtonCallback, UIHelper

logger = logging.getLogger(__name__)


class Nick(Cog):
    __slots__ = "bot", "cache", "ui_helper"

    def __init__(self, bot: Bot, cache: Cache, ui_helper: UIHelper) -> None:
        self.bot = bot
        self.cache = cache
        self.ui_helper = ui_helper

        self.ui_helper.register_callback("accept-nick-change", self.accept_wrapper)
        self.ui_helper.register_callback("reject-nick-change", self.reject_wrapper)

    def accept_wrapper(self, requester_id: Any, new_name: Any) -> ButtonCallback:
        if not isinstance(requester_id, int) or not isinstance(new_name, str):
            raise ValueError("Invalid values passed!")

        async def callback(interaction: Interaction) -> None:
            requester = self.cache.guild.get_member(requester_id)
            if not requester:
                await interaction.edit(content="User no longer in server!")
                return

            if not interaction.user or isinstance(interaction.user, User):
                raise RuntimeError("Interaction had invalid user!")

            if not interaction.message:
                raise RuntimeError("Interaction had no message?")

            if not interaction.user.get_role(config.exco_role):
                return await send_no_permission(interaction)

            await interaction.edit(
                content=f"{interaction.user.mention} has accepted {requester.mention}'s request to change name to {new_name}.",
                view=None,
            )

            try:
                await requester.edit(nick=new_name)
            except Forbidden:
                await interaction.edit(content="No permission to rename that user!")
                return

            await requester.send(f"Your rename request to {new_name} was accepted by an exco member!")

        return callback

    def reject_wrapper(self, requester_id: Any, new_name: Any) -> ButtonCallback:
        if not isinstance(requester_id, int) or not isinstance(new_name, str):
            raise ValueError("Invalid values passed!")

        async def callback(interaction: Interaction) -> None:
            requester = self.cache.guild.get_member(requester_id)
            if not requester:
                await interaction.edit(content="User no longer in server!")
                return

            if not interaction.user or isinstance(interaction.user, User):
                raise RuntimeError("Interaction had invalid user!")

            if not interaction.message:
                raise RuntimeError("Interaction had no message?")

            if not interaction.user.get_role(config.exco_role):
                return await send_no_permission(interaction)

            await interaction.edit(
                content=f"{interaction.user.mention} has rejected {requester.mention}'s request to change name to {new_name}.",
                view=None,
            )

            await requester.send(f"Your rename request to {new_name} was rejected by an exco member.")

        return callback

    @member_command(description="Request for a name change")
    async def nick(
        self, interaction: Interaction, *, new_name: str = SlashOption(description="Your new name", required=True)
    ) -> None:
        new_name = new_name.strip()

        if len(new_name) == 0:
            return await send_error(interaction, "Please enter a name!", ephemeral=True)

        exco_channel = self.cache.exco_channel

        if not interaction.user or not (member := self.cache.guild.get_member(interaction.user.id)):
            raise RuntimeError("Interaction had invalid user!")

        responses = View(timeout=None, auto_defer=False)
        responses.add_item(
            self.ui_helper.get_button(
                callback_name="accept-nick-change",
                callback_args=(member.id, new_name),
                label="Accept",
                emoji=emojis.tick,
                style=ButtonStyle.green,
            )
        )
        responses.add_item(
            self.ui_helper.get_button(
                callback_name="reject-nick-change",
                callback_args=(member.id, new_name),
                label="Deny",
                emoji=emojis.cross,
                style=ButtonStyle.red,
            )
        )

        await exco_channel.send(
            content=f"{interaction.user.mention} has requested to be renamed to {new_name}.", view=responses
        )

        await interaction.send(content="Your request has been sent!", ephemeral=True)


__all__ = ["Nick"]
