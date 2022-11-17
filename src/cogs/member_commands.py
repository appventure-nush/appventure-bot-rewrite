import csv
from io import StringIO

from nextcord import File, Interaction, SlashOption, NotFound
from nextcord.ext.commands import Bot, Cog

from database import database
from utils.access_control import exco_command

from config import config


class MemberCommands(Cog):
    __slots__ = "bot"

    def __init__(self, bot: Bot) -> None:
        super().__init__()

        self.bot = bot

    @exco_command()
    async def members(self, _interaction: Interaction) -> None:
        pass

    @members.subcommand(description="Export non-graduated members to csv")
    async def export(self, interaction: Interaction, *, strict: bool = SlashOption(description="Whether to count graduating Y6s or not")) -> None:
        file = StringIO()
        writer = csv.writer(file)
        writer.writerow(["Email", "Name", "Discord ID", "GitHub"])

        members = database.get_non_graduated(strict=strict)

        for member in members:
            writer.writerow([member.email, member.name, member.discord_id, member.github])

        file.seek(0)

        await interaction.response.send_message(content=f"Here you go! ({len(members)} members)", file=File(fp=file, filename="members.csv"))  # type: ignore

        file.close()

    @members.subcommand(description="Give alumni role to those graduating")
    async def refresh(self, interaction: Interaction) -> None:
        guild = self.bot.get_guild(config.guild_id)
        if not guild:
            await interaction.response.send_message(content=f"Could not find server, is GUILD_ID correct?")
            return

        role = guild.get_role(config.alumni_role)
        if not role:
            await interaction.response.send_message(content=f"Could not find alumni role, is ALUMNI_ROLE correct?")
            return

        new_alumni = database.get_graduated()
        updated = 0

        for member in new_alumni:
            discord_id = member.discord_id
            if not (discord_id): continue

            profile = guild.get_member(discord_id)  # type: ignore

            if (not profile) or (profile.get_role(config.alumni_role)):
                continue
        
            await profile.add_roles(role)
            updated += 1
        
        await interaction.response.send_message(content=f"Done! {updated} people graduated.")

