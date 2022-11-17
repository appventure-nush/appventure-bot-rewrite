from textwrap import dedent

from nextcord import Interaction, Member
from nextcord.ext.commands import Bot, Cog

from utils.access_control_decorators import member_command
from utils.database import database
from utils.ms_auth import get_ms_auth_link

from .cache import Cache


class Verify(Cog):
    __slots__ = "bot", "cache"

    def __init__(self, bot: Bot, cache: Cache):
        self.bot = bot
        self.cache = cache

    async def handle_login(self) -> None:
        pass

    def get_verify_message(self, member: Member) -> str:
        link = get_ms_auth_link()

        return dedent(
            f"""
                Welcome to the AppVenture Discord!

                To complete verification, click [this link]({link}) and follow the instructions.
                The link is valid for 1 hour.
                Alternatively, you can DM any ExCo to complete verification manually, or run `/verify` for a new link.
            """
        )

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        if member.guild != self.cache.guild:
            return  # do nothing

        message = self.get_verify_message(member)

    @member_command(description="Start the verification process, if you are not verified yet")
    async def verify(self, interaction: Interaction) -> None:
        if not interaction.user:
            raise RuntimeError("Interaction had no user!")

        member = self.cache.guild.get_member(interaction.user.id)
        if not member:
            raise RuntimeError("User not in AppVenture server, is permission check correct?")

        if len(database.get_member_by_discord_id(member.id)) > 0:
            # return await send_error(interaction, "You are already verified!")
            pass

        message = self.get_verify_message(member)

        await interaction.send(content=message)


__all__ = ["Verify"]
