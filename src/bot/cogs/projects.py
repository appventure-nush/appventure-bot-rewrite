from nextcord.ext.commands import Bot, Cog

from config import config
from .cache import Cache
from .ui_helper import UIHelper

from nextcord import Interaction, SlashOption, PermissionOverwrite, Permissions

from utils.access_control_decorators import is_exco, subcommand

from typing import MutableMapping, Optional
from dataclasses import dataclass

from utils.error import send_error

@dataclass
class Project:
    name: str
    discord_role_id: int
    discord_text_channel_id: int
    discord_voice_channel_id: int
    webhook_id: Optional[int] = None
    github_repo: Optional[str] = None

class Projects(Cog):
    __slots__ = "bot", "cache", "ui_helper"

    def __init__(self, bot: Bot, cache: Cache, ui_helper: UIHelper) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache
        self.ui_helper = ui_helper

        self.projects: MutableMapping[str, Project] = {}

    @is_exco()
    async def project(self, _: Interaction) -> None:
        pass

    @subcommand(project, description="Create a project")
    async def create(
        self, interaction: Interaction, 
        *, 
        project_name: str = SlashOption(description="Project name", required=True), 
        with_github: bool = SlashOption(description="Whether to also create a GitHub repository", default=True, required=True)
    ) -> None:
        project_name = project_name.lower().replace(' ', '-')
        
        if project_name in self.projects:
            return await send_error(interaction, "Project already exists")

        guild = self.cache.guild
        project_role = await guild.create_role(name=project_name, permissions=guild.default_role.permissions)
        deny_all = PermissionOverwrite.from_pair(allow=Permissions.none(), deny=Permissions(view_channel=False))
        channel_overrides = PermissionOverwrite.from_pair(allow=Permissions(view_channel=True), deny=Permissions.none())

        projects_category = self.cache.projects_category

        project_text_channel = await guild.create_text_channel(project_name, category=projects_category, overwrites={guild.default_role: deny_all, project_role: channel_overrides})
        project_voice_channel = await guild.create_voice_channel(f"{project_role}-voice", category=projects_category, overwrites={guild.default_role: deny_all, project_role: channel_overrides})

        project = Project(name=project_name, discord_role_id=project_role.id, discord_text_channel_id=project_text_channel.id, discord_voice_channel_id=project_voice_channel.id)

        if with_github:
            # TODO: make github webhook & link
            pass

        self.projects[project_name] = project



__all__ = ['Projects']