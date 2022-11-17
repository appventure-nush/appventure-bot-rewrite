from nextcord import Interaction


async def send_error(interaction: Interaction, message: str, *, ephemeral=False) -> None:
    await interaction.send(content=message, ephemeral=ephemeral, delete_after=30)


async def send_no_permission(interaction: Interaction) -> None:
    await send_error(interaction, "You don't have permission to do that!", ephemeral=True)


__all__ = ["send_error", "send_no_permission"]
