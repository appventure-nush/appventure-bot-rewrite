import os

if not os.getenv("Production"):
    # load from .env
    from dotenv import load_dotenv

    load_dotenv()


class Config:
    __slots__ = (
        "alumni_role",
        "archive_category_id",
        "discord_token",
        "exco_channel_id",
        "exco_role",
        "github_client_id",
        "github_client_secret",
        "github_token",
        "guest_role",
        "guild_id",
        "member_role",
        "projects_category_id",
    )

    def __init__(self) -> None:
        self.alumni_role = int(os.environ["ALUMNI_ROLE"])
        self.archive_category_id = int(os.environ["ARCHIVE_CATEGORY_ID"])
        self.discord_token = os.environ["DISCORD_TOKEN"]
        self.exco_channel_id = int(os.environ["EXCO_CHANNEL_ID"])
        self.exco_role = int(os.environ["EXCO_ROLE"])
        self.github_client_id = os.environ["GITHUB_CLIENT_ID"]
        self.github_client_secret = os.environ["GITHUB_CLIENT_SECRET"]
        self.github_token = os.environ["GITHUB_TOKEN"]
        self.guest_role = int(os.environ["GUEST_ROLE"])
        self.guild_id = int(os.environ["GUILD_ID"])
        self.member_role = int(os.environ["MEMBER_ROLE"])
        self.projects_category_id = int(os.environ["PROJECTS_CATEGORY_ID"])


config = Config()

__all__ = ["config"]