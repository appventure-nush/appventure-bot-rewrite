from nextcord import Interaction
from nextcord.ext.commands import Cog, Bot
from .cache import Cache
from config import config

from utils.access_control_decorators import is_in_server

class Help(Cog):
    __slots__ = "bot", "cache"

    def __init__(self, bot: Bot, cache: Cache):
        self.bot = bot
        self.cache = cache

    def get_commands_members(self):
        return [
            ("/nick", "Send a request to change your server name"),
            ("/ms verify", "Start the email verification process"),
            ("/gh verify", "Link with your GitHub account"),
        ]
    
    def get_commands_exco(self):
        return self.get_commands_members() + [
            ("/members import", "Import new members from a csv (make sure to do this before new members join!)"),
            ("/members export", "Export members to a csv"),
            ("/members refresh", "Give alumni role to members who have graduated"),
            ("/members modify_year", "Modify the year of a member (retained people)"),
            ("/members leave", "Give someone guest role, removing member role"),
            ("/ms manual_verify", "Manually verify someone's email"),
            ("/projects create", "Create a new project"),
            ("/projects delete", "Delete a project"),
            ("/projects import", "Add an existing project to the database"),
            ("/projects link", "Link a project to GitHub"),
            ("/projects share", "Share project GitHub repo to members"),
            ("/projects export", "Export all projects and member assignments"),
            ("/projects archive", "Archive a project")
        ]

    @is_in_server(description="Get help on the commands")
    async def help(self, interaction: Interaction):
        if not interaction.user or not (member := self.cache.guild.get_member(interaction.user.id)):
            raise RuntimeError("Interaction had invalid user!")
        
        if member.get_role(config.exco_role):
            commands = self.get_commands_exco()
        else:
            commands = self.get_commands_members()

        commands = "\n".join([f"> `{command}`\n{description}\n" for command, description in commands])

        await interaction.response.send_message(
            f"Here are the commands you can use:\n\n{commands}",
            ephemeral=True
        )

__all__ = ["Help"]