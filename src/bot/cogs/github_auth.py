from github import Github
from nextcord.ext.commands import Bot, Cog

from config import config


class GithubAuth(Cog, name="GithubAuth"):
    __slots__ = "bot", "github", "appventure_org"

    def __init__(self, bot: Bot) -> None:
        super().__init__()

        self.bot = bot
        self.github = Github(str(config.github_token))
        self.appventure_org = self.github.get_organization("appventure-nush")
