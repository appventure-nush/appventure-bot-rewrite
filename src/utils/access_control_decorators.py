from typing import Callable

from nextcord import (
    ApplicationCheckFailure,
    Client,
    ClientCog,
    Interaction,
    Permissions,
    SlashApplicationCommand,
    slash_command,
)
from nextcord.ext.application_checks import check
from nextcord.ext.commands import Bot

from cogs.cache import Cache
from config import config
from utils.error import send_error


def check_is_exco():
    def predicate(interaction: Interaction) -> bool:
        client: Client = interaction.client
        if not isinstance(client, Bot):
            raise RuntimeError("Check not running from a bot!")

        if not (cache := client.get_cog("Cache")) or not isinstance(cache, Cache):
            raise RuntimeError("Cache cog invalid!")

        guild = cache.guild
        user = interaction.user

        if not user:
            raise RuntimeError("User is not defined!")

        # make sure user has "exco" in "guild"
        return ((member := guild.get_member(user.id)) is not None) and (member.get_role(config.exco_role) is not None)

    return check(predicate)


def check_is_member():
    def predicate(interaction: Interaction) -> bool:
        client: Client = interaction.client
        if not isinstance(client, Bot):
            raise RuntimeError("Check not running from a bot!")

        if not (cache := client.get_cog("Cache")) or not isinstance(cache, Cache):
            raise RuntimeError("Cache cog invalid!")

        guild = cache.guild
        user = interaction.user

        if not user:
            raise RuntimeError("User is not defined!")

        # make sure user has "exco" in "guild"
        return guild.get_member(user.id) is not None

    return check(predicate)


async def on_access_control_failure(_cog: ClientCog, interaction: Interaction, error: Exception) -> None:
    if isinstance(error, ApplicationCheckFailure):
        await send_error(interaction, "You cannot run this command!", ephemeral=True)
        return

    raise error


def member_command(**kwargs):
    kwargs["force_global"] = True

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_is_member()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


def exco_command(**kwargs):
    kwargs["force_global"] = True
    kwargs["default_member_permissions"] = Permissions(administrator=True)

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_is_exco()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


# ensure we keep the checks
def subcommand(main_command: SlashApplicationCommand, **kwargs):
    kwargs["inherit_hooks"] = True

    def wrapped(func: Callable):
        return main_command.subcommand(**kwargs)(func)

    return wrapped


__all__ = ["member_command", "exco_command", "subcommand"]
