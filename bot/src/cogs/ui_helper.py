import logging
import uuid
from typing import (
    Any,
    Callable,
    Collection,
    Coroutine,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Tuple,
)

from nextcord import (
    Interaction,
    InteractionType,
    Message,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View

from .json_cache import JSONCache

logger = logging.getLogger(__name__)

ButtonCallback = Callable[[Interaction], Coroutine[Any, Any, None]]
ButtonCallbackFactory = Callable[..., ButtonCallback]


class UIHelper(Cog):
    __slots__ = "bot", "callbacks", "buttons", "pending"

    def __init__(self, bot: Bot, json_cache: JSONCache):
        super().__init__()

        self.bot = bot
        self.callbacks: MutableMapping[str, ButtonCallbackFactory] = {}
        self.buttons: MutableMapping[
            str, MutableSequence[Tuple[str, str, Collection[Any]]]
        ] = json_cache.register_cache(
            "buttons"
        )  # message id -> button id, callback name, callback args
        self.pending: MutableMapping[str, Tuple[str, Collection[Any]]] = {}  # button id -> callback name, callback args

    def register_callback(self, callback_name: str, callback: ButtonCallbackFactory) -> None:
        if callback_name in self.callbacks:
            raise ValueError(f"Callback {callback_name} already registered")

        self.callbacks[callback_name] = callback

    def get_button(self, callback_name: str, callback_args: Collection[Any], **kwargs) -> Button:
        while (button_id := uuid.uuid4().hex) in self.pending:
            pass
        
        self.pending[button_id] = (callback_name, callback_args)
        
        kwargs["custom_id"] = button_id
        button = Button(**kwargs)

        return button

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.id != self.bot.application_id:
            return

        if len(message.components) == 0:
            return

        view = View.from_message(message)
        for component in view.children:
            if not isinstance(component, Button):
                continue

            if not component.custom_id:
                continue  # URL button

            if component.custom_id not in self.pending:
                logger.warn("Adding a button not registered in the UI helper!")
                continue

            if str(message.id) not in self.buttons:
                self.buttons[str(message.id)] = []

            self.buttons[str(message.id)].append((component.custom_id, *self.pending[component.custom_id]))
            self.pending.pop(component.custom_id)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        self.buttons.pop(str(payload.message_id), None)

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        for message_id in payload.message_ids:
            self.buttons.pop(str(message_id), None)

    def find_button_ids(self, components: Collection[Any]) -> MutableSet[str]:
        result = set()

        for component in components:
            if component["type"] == 1:
                # Action Row, recurse
                result.update(self.find_button_ids(component["components"]))
            elif component["type"] == 2:
                # Button
                if "custom_id" in component:
                    result.add(component["custom_id"])

        return result

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        # https://discord.com/developers/docs/topics/gateway-events#message-update
        data: Mapping[str, Any] = payload.data

        author_id: str | None = data.get("author", {}).get("id", None)
        if not author_id:
            logger.warn("Message had no author!")
            return

        if author_id != str(self.bot.application_id):
            return

        components = data.get("components", [])
        button_ids = self.find_button_ids(components)

        message_id = str(payload.message_id)
        if message_id not in self.buttons:
            self.buttons[message_id] = []

        def filter_button_id(button: Tuple[str, str, Collection[Any]]) -> bool:
            if button[0] in button_ids:
                button_ids.discard(button[0])
                return True
            return False

        # remove popped components
        self.buttons[message_id] = list(filter(filter_button_id, self.buttons[message_id]))

        # (technically equivalent but cancer)
        # self.buttons[message_id] = list(filter(lambda button: (button[0] in button_ids) and (button_ids.discard(button[0]) or True), self.buttons[message_id]))

        # add pending components
        for button_id in button_ids:
            if button_id not in self.pending:
                logger.warn("Adding a button not registered in the UI helper!")
                continue

            self.buttons[message_id].append((button_id, *self.pending[button_id]))
            self.pending.pop(button_id)

        # if the length is 0, remove the message from the buttons dict
        if len(self.buttons[message_id]) == 0:
            self.buttons.pop(message_id)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        # https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-object-interaction-type
        if not interaction.user or interaction.user.bot:
            return

        if interaction.type != InteractionType.component:
            return

        if interaction.message is None:
            return

        if interaction.message.author.id != self.bot.application_id:
            return

        if str(interaction.message.id) not in self.buttons:
            return

        for button_id, callback_name, callback_args in self.buttons[str(interaction.message.id)]:
            if interaction.data and button_id == interaction.data.get("custom_id", None):
                callback = self.callbacks[callback_name](*callback_args)
                await callback(interaction)
                break

    def check_callback_exists(self, button: Tuple[str, str, Collection[Any]]):
        if button[1] not in self.callbacks:
            logger.warn(f"Callback {button[1]} not found, removing button!")
            return False
        return True

    # Load buttons
    @Cog.listener()
    async def on_connect(self) -> None:
        for message_id in self.buttons:
            self.buttons[message_id] = list(filter(self.check_callback_exists, self.buttons[message_id]))

        no_buttons = sum(len(buttons) for buttons in self.buttons.values())
        logger.info(f"Loaded {no_buttons} buttons")


__all__ = ["UIHelper", "ButtonCallback", "ButtonCallbackFactory"]
