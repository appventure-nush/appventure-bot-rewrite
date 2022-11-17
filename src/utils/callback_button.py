from typing import Protocol

from nextcord import Interaction
from nextcord.ui import Button


class ButtonCallback(Protocol):
    async def __call__(self, interaction: Interaction) -> None:
        ...


def button_with_callback(callback: ButtonCallback, **kwargs) -> Button:
    button = Button(**kwargs)
    button.callback = callback
    return button


__all__ = ["button_with_callback", "ButtonCallback"]
