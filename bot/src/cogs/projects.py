import csv
from io import StringIO
from typing import Optional

from config import config
from github import Github
from nextcord import (
    CategoryChannel,
    File,
    Interaction,
    PermissionOverwrite,
    Permissions,
    Role,
    SlashOption,
    TextChannel,
    VoiceChannel,
)
from nextcord.ext.commands import Bot, Cog
from utils.access_control_decorators import is_exco, subcommand
from utils.database import Project, database
from utils.error import send_error

from .cache import Cache
from .github_auth import GithubAuth
from .ui_helper import UIHelper


class Projects(Cog):
    __slots__ = "bot", "cache", "ui_helper", "ci", "org", "github_auth"

    def __init__(self, bot: Bot, cache: Cache, ui_helper: UIHelper, github_auth: GithubAuth) -> None:
        super().__init__()

        self.bot = bot
        self.cache = cache
        self.ui_helper = ui_helper
        self.ci = Github(config.github_token)
        self.org = self.ci.get_organization("appventure-nush")
        self.github_auth = github_auth

    @is_exco()
    async def project(self, _: Interaction) -> None:
        pass

    @subcommand(project, description="Create a project")
    async def create(
        self,
        interaction: Interaction,
        *,
        category: CategoryChannel = SlashOption(description="Category to create project in", required=True),
        project_name: str = SlashOption(description="Project name", required=True),
        with_github: bool = SlashOption(
            description="Whether to also create a GitHub repository", default=True, required=True
        ),
        with_voice: bool = SlashOption(
            description="Whether to also create a voice channel", default=True, required=True
        ),
    ) -> None:
        await interaction.response.defer()

        project_name = project_name.lower().replace(" ", "-")

        if database.get_project(project_name):
            return await send_error(interaction, "Project already exists")

        guild = self.cache.guild
        project_role = await guild.create_role(name=project_name, permissions=guild.default_role.permissions)
        deny_all = PermissionOverwrite.from_pair(allow=Permissions.none(), deny=Permissions(view_channel=False))
        channel_overrides = PermissionOverwrite.from_pair(allow=Permissions(view_channel=True), deny=Permissions.none())

        project_text_channel = await guild.create_text_channel(
            project_name,
            category=category,
            overwrites={guild.default_role: deny_all, project_role: channel_overrides},
        )

        project = Project(
            name=project_name,
            discord_role_id=project_role.id,
            discord_text_channel_id=project_text_channel.id,
        )

        if with_voice:
            project_voice_channel = await guild.create_voice_channel(
                f"{project_role}-voice",
                category=category,
                overwrites={guild.default_role: deny_all, project_role: channel_overrides},
            )

            project.discord_voice_channel_id = project_voice_channel.id  # type: ignore

        if with_github:
            # make github repo and attach webhook
            repo = self.org.create_repo(project_name, private=True)

            discord_webhook = await project_text_channel.create_webhook(
                name=f"GitHub Updates (appventure-nush/{project_name})"
            )
            webhook_url = f"{discord_webhook.url}/github"
            github_webhook = repo.create_hook(
                "web",
                {
                    "url": webhook_url,
                    "content_type": "json",
                },
                events=["push", "pull_request", "pull_request_review", "pull_request_review_comment"],
                active=True,
            )

            await project_text_channel.send(f"Linked with `{repo.full_name}`!")

            project.github_repo = repo.name  # type: ignore
            project.webhook_id = discord_webhook.id  # type: ignore
            project.github_webhook_id = github_webhook.id  # type: ignore

        database.insert_project(project)

        await interaction.send("Project created successfully!")

    @subcommand(project, description="Delete a project")
    async def delete(
        self,
        interaction: Interaction,
        *,
        project_name: str = SlashOption(description="Project name", required=True),
        internal_only: bool = SlashOption(
            description="Whether to only delete in the internal project database", default=False
        ),
    ) -> None:
        project_name = project_name.lower().replace(" ", "-")

        project = database.get_project(project_name)
        if not project:
            return await send_error(interaction, "Project does not exist")

        database.delete_project(project)

        if internal_only:
            await interaction.send("Project deleted successfully!")
            return

        guild = self.cache.guild

        project_role = guild.get_role(project.discord_role_id)  # type: ignore
        if project_role:
            await project_role.delete()

        project_text_channel = guild.get_channel(project.discord_text_channel_id)  # type: ignore
        if project_text_channel:
            await project_text_channel.delete()

        if project.discord_voice_channel_id:
            project_voice_channel = guild.get_channel(project.discord_voice_channel_id)  # type: ignore
            if project_voice_channel:
                await project_voice_channel.delete()

        if project.github_repo and project.github_webhook_id:
            repo = self.org.get_repo(project.github_repo)  # type: ignore
            hook = repo.get_hook(project.github_webhook_id)  # type: ignore
            hook.delete()

        await interaction.send("Project deleted successfully!")

    @subcommand(project, description="Link existing project", name="import")
    async def _import(
        self,
        interaction: Interaction,
        *,
        project_name: str = SlashOption(description="Project name", required=True),
        project_role: Optional[Role] = SlashOption(description="Project role (default: <project name>)"),
        project_text_channel: Optional[TextChannel] = SlashOption(
            description="Project text channel (default: <project name>)"
        ),
        project_voice_channel: Optional[VoiceChannel] = SlashOption(
            description="Project voice channel (default: <project name>-voice)"
        ),
    ):
        await interaction.response.defer()

        project_name = project_name.lower().replace(" ", "-")

        project = database.get_project(project_name)
        if project:
            return await send_error(interaction, "Project already exists")

        guild = self.cache.guild
        _project_role = project_role
        if not _project_role:
            for role in guild.roles:
                if role.name == project_name:
                    _project_role = role
                    break

        if not _project_role:
            return await send_error(interaction, "Project role does not exist")

        _project_text_channel = project_text_channel
        if not _project_text_channel:
            for channel in guild.text_channels:
                if channel.name == project_name and isinstance(channel, TextChannel):
                    _project_text_channel = channel
                    break

        if not _project_text_channel:
            return await send_error(
                interaction, "Project text channel does not exist, or the channel is not a text channel"
            )

        _project_voice_channel = project_voice_channel
        if not _project_voice_channel:
            for channel in guild.voice_channels:
                if channel.name == f"{project_name}-voice" and isinstance(channel, VoiceChannel):
                    _project_voice_channel = channel
                    break

        if not _project_voice_channel:
            return await send_error(
                interaction, "Project voice channel does not exist, or the channel is not a voice channel"
            )

        project = Project(
            name=project_name,
            discord_role_id=_project_role.id,
            discord_text_channel_id=_project_text_channel.id,
            discord_voice_channel_id=_project_voice_channel.id,
        )

        database.insert_project(project)

        await interaction.send("Project linked successfully!")

    @subcommand(project, description="Link project to GitHub repo", name="link")
    async def link(
        self,
        interaction: Interaction,
        *,
        project_name: str = SlashOption(description="Project name", required=True),
        github_repo: str = SlashOption(
            description="GitHub repo name (only the part after appventure-nush)", required=True
        ),
        force: bool = SlashOption(description="Whether to force link even if project already linked", default=False),
    ) -> None:
        project_name = project_name.lower().replace(" ", "-")

        project = database.get_project(project_name)
        if not project:
            return await send_error(interaction, "Project does not exist")

        if not force and project.github_repo:
            return await send_error(interaction, "Project already linked to GitHub repo")

        repo = self.org.get_repo(github_repo)
        if not repo:
            return await send_error(interaction, "GitHub repo does not exist")

        project_text_channel = self.cache.guild.get_channel(project.discord_text_channel_id)  # type: ignore
        if not project_text_channel:
            return await send_error(interaction, "Project text channel does not exist, was it manually deleted?")

        if not isinstance(project_text_channel, TextChannel):
            return await send_error(interaction, "Project text channel is not a text channel, was it manually changed?")

        if force and project.github_repo:
            # delete old webhooks
            repo = self.org.get_repo(project.github_repo)  # type: ignore
            hook = repo.get_hook(project.github_webhook_id)  # type: ignore
            hook.delete()
            for webhook in await project_text_channel.webhooks():
                if webhook.id == project.webhook_id:
                    await webhook.delete()
                    break

        discord_webhook = await project_text_channel.create_webhook(
            name=f"GitHub Updates (appventure-nush/{project_name})"
        )
        webhook_url = f"{discord_webhook.url}/github"
        github_webhook = repo.create_hook(
            "web",
            {
                "url": webhook_url,
                "content_type": "json",
            },
            events=["push", "pull_request", "pull_request_review", "pull_request_review_comment"],
            active=True,
        )

        await project_text_channel.send(f"Linked with `{repo.full_name}`!")

        project.github_repo = repo.name  # type: ignore
        project.webhook_id = discord_webhook.id  # type: ignore
        project.github_webhook_id = github_webhook.id  # type: ignore

        database.update_project(project)

        await interaction.send("Project linked successfully!")

    @subcommand(project, description="Share GitHub repo with project members")
    async def share(
        self,
        interaction: Interaction,
        *,
        project_name: str = SlashOption(description="Project name", required=True),
    ) -> None:
        project_name = project_name.lower().replace(" ", "-")

        await interaction.response.defer()

        project = database.get_project(project_name)

        if not project:
            return await send_error(interaction, "Project does not exist")

        if not project.github_repo:
            return await send_error(interaction, "Project not linked to GitHub repo")

        repo = self.org.get_repo(project.github_repo)  # type: ignore
        if not repo:
            return await send_error(interaction, "GitHub repo link broken; please re-link project")

        role = self.cache.guild.get_role(project.discord_role_id)  # type: ignore
        if not role:
            return await send_error(interaction, "Project role not found")

        members = role.members
        github_names = []
        no_github = []

        for member in members:
            github_name = database.get_github(member.id)  # type: ignore
            if (not github_name):
                no_github.append(member.display_name)
                continue
            github_names.append(github_name.github)

        for contributor in repo.get_contributors():
            if contributor.login in github_names:
                github_names.remove(contributor.login)

        # add everyone remaining to repo
        for github_name in github_names:
            repo.add_to_collaborators(github_name, permission="maintain")

        await interaction.send(f"Project shared to ```{', '.join(github_names)}``` (no GitHub linked: ```{', '.join(no_github)}```)")

    @subcommand(project, description="Export all projects and member assignments")
    async def export(self, interaction: Interaction) -> None:
        guild = self.cache.guild

        await interaction.response.defer()

        projects_file = StringIO()
        projects_writer = csv.writer(projects_file)
        projects_writer.writerow(["project-name", "github-name"])

        members_file = StringIO()
        members_writer = csv.writer(members_file)
        members_writer.writerow(["member", "project", "in-github"])

        projects = database.get_projects()

        for project in projects:
            project_role = guild.get_role(project.discord_role_id)  # type: ignore
            if not project_role:
                raise ValueError(f"Project role {project.discord_role_id} not found")

            for member in project_role.members:
                # check if member in github
                in_github = False
                if project.github_repo:
                    contributor_names = [
                        contributor.login for contributor in self.ci.get_repo(project.github_repo).get_contributors()  # type: ignore
                    ]
                    in_github = (await self.github_auth.get_github_name(member.id)) in contributor_names

                members_writer.writerow([project.name, member.display_name, in_github])

            projects_writer.writerow([project.name, project.github_repo])

        projects_file.seek(0)
        members_file.seek(0)

        await interaction.send(content=f"Here you go! ({len(projects)} projects)", files=[File(fp=projects_file, filename="projects.csv"), File(fp=members_file, filename="project_members.csv")])  # type: ignore

        projects_file.close()
        members_file.close()

    @subcommand(project, description="Archive a project")
    async def archive(
        self,
        interaction: Interaction,
        *,
        project_name: str = SlashOption(description="Project name", required=True),
        archive_category: CategoryChannel = SlashOption(description="Channel to move project to", required=True),
    ) -> None:
        project_name = project_name.lower().replace(" ", "-")

        project = database.get_project(project_name)
        if not project:
            return await send_error(interaction, "Project does not exist")

        guild = self.cache.guild
        text_channel = guild.get_channel(project.discord_text_channel_id)  # type: ignore
        if not text_channel:
            return await send_error(interaction, "Project text channel does not exist, was it manually deleted?")
        if not isinstance(text_channel, TextChannel):
            return await send_error(interaction, "Project text channel is not a text channel, was it manually changed?")

        voice_channel = guild.get_channel(project.discord_voice_channel_id)  # type: ignore
        if not voice_channel:
            return await send_error(interaction, "Project text channel does not exist, was it manually deleted?")
        if not isinstance(voice_channel, VoiceChannel):
            return await send_error(
                interaction, "Project voice channel is not a voice channel, was it manually changed?"
            )

        await text_channel.edit(category=archive_category)
        await voice_channel.delete()

        # delete from the internal db
        database.delete_project(project)

        await interaction.send("Project archived successfully!")


__all__ = ["Projects"]
