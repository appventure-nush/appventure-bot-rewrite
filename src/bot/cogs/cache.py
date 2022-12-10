from nextcord import Guild, Role, TextChannel
from nextcord.ext.commands import Bot, Cog

from config import config


class Cache(Cog, name="Cache"):
    __slots__ = "_guild", "bot", "_alumni_role", "_exco_channel", "_member_role", "_guest_role"

    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot
        self._guild = None
        self._alumni_role = None
        self._member_role = None
        self._guest_role = None
        self._exco_channel = None

    @property
    def guild(self) -> Guild:
        if not self._guild:
            self._guild = self.bot.get_guild(config.guild_id)
            if not self._guild:
                raise RuntimeError("Cannot find guild!")

        return self._guild

    @property
    def alumni_role(self) -> Role:
        if not self._alumni_role:
            self._alumni_role = self.guild.get_role(config.alumni_role)
            if not self._alumni_role:
                raise RuntimeError("Cannot find alumni role!")

        return self._alumni_role

    @property
    def member_role(self) -> Role:
        if not self._member_role:
            self._member_role = self.guild.get_role(config.member_role)
            if not self._member_role:
                raise RuntimeError("Cannot find member role!")

        return self._member_role

    @property
    def guest_role(self) -> Role:
        if not self._guest_role:
            self._guest_role = self.guild.get_role(config.guest_role)
            if not self._guest_role:
                raise RuntimeError("Cannot find guest role!")

        return self._guest_role

    @property
    def exco_channel(self) -> TextChannel:
        if not self._exco_channel:
            self._exco_channel = self.guild.get_channel(config.exco_channel_id)
            if not self._exco_channel or not isinstance(self._exco_channel, TextChannel):
                raise RuntimeError("Cannot find ExCo channel!")

        return self._exco_channel  # type: ignore


__all__ = ["Cache"]
