import csv
from io import StringIO

from nextcord import Attachment, File, Interaction, SlashOption
from nextcord.ext.commands import Bot, Cog

from config import config
from utils.access_control_decorators import exco_command, subcommand
from utils.database import database
from utils.error import send_error

from .cache import Cache


class MemberManagement(Cog):
    __slots__ = "bot", "cache"

    def __init__(self, bot: Bot, cache: Cache) -> None:
        self.bot = bot
        self.cache = cache

    @exco_command()
    async def members(self, _interaction: Interaction) -> None:
        pass

    @subcommand(members, description="Import members from a csv", name="import")
    async def _import(self, interaction: Interaction, *, file: Attachment = SlashOption(description="Members to add")):
        try:
            content = (await file.read()).decode("utf-8")
        except UnicodeDecodeError:
            return await send_error(interaction, "Could not decode, is the file in UTF-8?")

        reader = csv.DictReader(StringIO(content))
        row_num = 1
        for row in reader:
            if not row.get("name", None) or not row.get("email", None):
                return await send_error(
                    interaction, f"Invalid row on line {row_num + 1}, are the headings (`name`, `email`) correct?"
                )

            if not database.create_member(row["email"], row["name"]):
                return await send_error(
                    interaction, f"Error writing row {row_num + 1} (already added {row_num - 1} members)"
                )

            row_num += 1

        await interaction.send(content=f"Done! Added {row_num - 1} new members.")

    @subcommand(members, description="Export non-graduated members to csv")
    async def export(
        self,
        interaction: Interaction,
        *,
        count_graduating: bool = SlashOption(description="Whether to count graduating Y6s or not", default=True),
    ) -> None:
        file = StringIO()
        writer = csv.writer(file)
        writer.writerow(["Email", "Name", "Discord ID", "GitHub"])

        members = database.get_non_graduated(strict=(not count_graduating))

        for member in members:
            writer.writerow([member.email, member.name, member.discord_id, member.github])

        file.seek(0)

        await interaction.send(content=f"Here you go! ({len(members)} records)", file=File(fp=file, filename="members.csv"))  # type: ignore

        file.close()

    @subcommand(members, description="Give alumni role to those graduating")
    async def refresh(self, interaction: Interaction) -> None:
        guild = self.cache.guild
        alumni_role = self.cache.alumni_role

        new_alumni = database.get_graduated()
        updated = 0

        for member in new_alumni:
            discord_id = member.discord_id
            if not (discord_id):
                continue

            profile = guild.get_member(discord_id)  # type: ignore

            if (not profile) or (profile.get_role(config.alumni_role)):
                continue

            await profile.add_roles(alumni_role)
            updated += 1

        await interaction.send(content=f"Done! {updated} people graduated.")


__all__ = ["MemberManagement"]