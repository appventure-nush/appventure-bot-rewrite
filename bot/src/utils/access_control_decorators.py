from typing import Callable

from cogs.cache import Cache
from config import config
from nextcord import (
    ApplicationCheckFailure,
    Client,
    ClientCog,
    Interaction,
    SlashApplicationCommand,
    slash_command,
)
from nextcord.ext.application_checks import check
from nextcord.ext.commands import Bot
from utils.error import send_error


async def on_access_control_failure(_: ClientCog, interaction: Interaction, error: Exception) -> None:
    if isinstance(error, ApplicationCheckFailure):
        await send_error(interaction, "You cannot run this command!", ephemeral=True)
        return

    raise error


def check_in_server():
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

        # make sure user has "member" in guild
        return (guild.get_member(user.id)) is not None

    return check(predicate)


def is_in_server(**kwargs):
    kwargs["force_global"] = True

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_in_server()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


def check_is_verified():
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

        # make sure user has any of "alumni", "member" or "guest" in guild
        return ((member := guild.get_member(user.id)) is not None) and len(
            {cache.member_role, cache.alumni_role, cache.guest_role}.intersection(member.roles)
        ) > 0

    return check(predicate)


def is_verified(**kwargs):
    kwargs["force_global"] = True

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_in_server()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


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

        # make sure user has "member" in guild
        return ((member := guild.get_member(user.id)) is not None) and (member.get_role(config.member_role) is not None)

    return check(predicate)


def is_member(**kwargs):
    kwargs["force_global"] = True

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_is_member()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


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

        # make sure user has "exco" in guild
        return ((member := guild.get_member(user.id)) is not None) and (member.get_role(config.exco_role) is not None)

    return check(predicate)


def is_exco(**kwargs):
    kwargs["force_global"] = True

    def wrapped(func: Callable):
        func = slash_command(**kwargs)(check_is_exco()(func))
        func.error(on_access_control_failure)
        return func

    return wrapped


# ensure we keep the checks
def subcommand(main_command: SlashApplicationCommand, **kwargs):
    if "inherit_hooks" not in kwargs:
        kwargs["inherit_hooks"] = True

    def wrapped(func: Callable):
        return main_command.subcommand(**kwargs)(func)

    return wrapped


__all__ = [
    "is_member",
    "check_is_member",
    "is_exco",
    "check_is_exco",
    "is_in_server",
    "check_in_server",
    "is_verified",
    "check_is_verified",
    "subcommand",
]
