import os


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
        "ms_auth_client_id",
        "ms_auth_tenant_id",
        "ms_auth_redirect_domain",
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
        self.ms_auth_client_id = os.environ["MS_AUTH_CLIENT_ID"]
        self.ms_auth_tenant_id = os.environ["MS_AUTH_TENANT_ID"]
        self.ms_auth_redirect_domain = os.environ["MS_AUTH_REDIRECT_DOMAIN"]


config = Config()

__all__ = ["config"]
