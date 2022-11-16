from nextcord import Permissions, slash_command

from config import config


def member_command(**kwargs):
    kwargs["guild_ids"] = [config.guild_id, 789468266803625984]  # TODO: remove testing guild id

    def wrapper(func):
        wrapped = slash_command(func, **kwargs)
        wrapper.subcommand = wrapped.subcommand
        return wrapped

    return wrapper


def exco_command(**kwargs):
    kwargs["guild_ids"] = [config.guild_id, 789468266803625984]  # TODO: remove testing guild id
    kwargs["default_member_permissions"] = Permissions(administrator=True)

    def wrapper(func):
        return slash_command(**kwargs)(func)

    return wrapper


__all__ = ["member_command", "exco_command"]
