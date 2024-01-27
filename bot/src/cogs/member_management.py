import csv
from io import StringIO

from config import config
from nextcord import Attachment, File, Interaction, Member, SlashOption
from nextcord.ext.commands import Bot, Cog
from utils.access_control_decorators import is_exco, subcommand
from utils.database import database
from utils.error import send_error

from .cache import Cache


class MemberManagement(Cog):
    __slots__ = "bot", "cache"

    def __init__(self, bot: Bot, cache: Cache) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache

    @is_exco()
    async def members(self, _: Interaction) -> None:
        pass

    @subcommand(members, description="Import members from a csv", name="import")
    async def _import(
        self,
        interaction: Interaction,
        *,
        members: Attachment = SlashOption(description='Members to add, "name" and "email"'),
        update_existing: bool = SlashOption(
            description="Whether to update existing members on conflict", default=False
        ),
    ) -> None:
        try:
            content = (await members.read()).decode("utf-8")
        except UnicodeDecodeError:
            return await send_error(interaction, "Could not decode, is the file in UTF-8?")

        reader = csv.DictReader(StringIO(content))
        emails = []
        names = []
        for row_num, row in enumerate(reader):
            if not row.get("name", None) or not row.get("email", None):
                return await send_error(
                    interaction, f"Invalid row on line {row_num + 1}, are the values (`name`, `email`) correct?"
                )

            emails.append(row["email"])
            names.append(row["name"])

        if len(emails) != len(names):
            # This should never happen, but just in case
            raise ValueError("Emails and names are not the same length???")

        success = database.create_members(emails, names, update_existing)

        if not success:
            await send_error(interaction, "Insertion failed, check logs for more info.")
        else:
            if update_existing:
                await interaction.send(
                    content=f"Done! Added {success[1]} new members and updated {success[2]} members."
                )
            else:
                await interaction.send(content=f"Done! Added {success[1]} new members.")

    @subcommand(members, description="Export non-graduated members to csv")
    async def export(
        self,
        interaction: Interaction,
        *,
        count_graduating: bool = SlashOption(description="Whether to count graduating Y6s or not", default=True),
        all_members: bool = SlashOption(
            description="Return everyone, including alumni (overrides count_graduating)", default=False
        ),
    ) -> None:
        file = StringIO()
        writer = csv.writer(file)
        writer.writerow(["year", "email", "name", "discord-id", "github"])

        if not all_members:
            members = database.get_non_graduated(strict=(not count_graduating), with_github=True)
        else:
            members = database.get_members()

        for member in members:
            writer.writerow((member.year, member.email, member.name, member.discord_id, member.github))

        file.seek(0)

        await interaction.send(content=f"Here you go! ({len(members)} records)", file=File(fp=file, filename="members.csv"))  # type: ignore

        file.close()

    @subcommand(members, description="Give alumni role to those graduating")
    async def refresh(self, interaction: Interaction) -> None:
        await interaction.response.defer()

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

    @subcommand(members, description="Modify a member's year (for retained people)")
    async def modify_year(
        self,
        interaction: Interaction,
        *,
        member: Member = SlashOption(description="Member to modify", required=True),
        year: int = SlashOption(description="Their current school year", required=True),
    ):
        # get member in db
        member_db = database.get_member_by_discord_id(member.id)
        if not member_db:
            return await send_error(interaction, "Member not found in database")

        if member_db.year == year:
            return await send_error(interaction, "Member is already in that year")

        member_db.year_offset = member_db.year_offset + member_db.year - year

        database.update_member(member_db)

        await interaction.send(content=f"Done! {member.mention} is now in year {year}")

    @subcommand(members, description="Change a member to guest")
    async def leave(
        self,
        interaction: Interaction,
        *,
        member: Member = SlashOption(description="Leaving member", required=True),
    ):
        # get member in db
        member_db = database.get_member_by_discord_id(member.id)
        if not member_db:
            return await send_error(interaction, "Member not found in database")

        # give guest role, remove member role
        await member.remove_roles(self.cache.member_role)
        await member.add_roles(self.cache.guest_role)

        database.delete_member(member_db)

        await interaction.send(content=f"Done! {member.mention} is now a guest")


__all__ = ["MemberManagement"]
