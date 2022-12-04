from typing import MutableMapping, Callable, Any, Coroutine, MutableSequence, Tuple, Any, Coroutine, Collection, Mapping
from nextcord.ext.commands import Cog, Bot
from nextcord import Interaction, Message, RawMessageDeleteEvent, RawBulkMessageDeleteEvent, RawMessageUpdateEvent, InteractionType
from nextcord.ui import Button, View
from nextcord.ext import tasks
import orjson
import uuid

import logging

logger = logging.getLogger(__name__)

ButtonCallback = Callable[[Interaction], Coroutine[Any, Any, None]]
ButtonCallbackFactory = Callable[..., ButtonCallback]

class UIHelper(Cog):
    __slots__ = "bot", "callbacks"

    def __init__(self, bot: Bot):
        self.bot = bot
        self.callbacks: MutableMapping[str, ButtonCallbackFactory] = {}
        self.buttons: MutableMapping[str, MutableSequence[Tuple[str, str, Collection[Any]]]] = {} # message id -> button id, callback name, callback args
        self.pending: MutableMapping[str, Tuple[str, Collection[Any]]] = {} # button id -> callback name, callback args

    def register_callback(self, callback_name: str, callback: ButtonCallbackFactory) -> None:
        if callback_name in self.callbacks:
            raise ValueError(f"Callback {callback_name} already registered")

        self.callbacks[callback_name] = callback

    def get_button(self, callback_name: str, callback_args: Collection[Any], **kwargs) -> Button:
        button_id = str(uuid.uuid4())
        kwargs["custom_id"] = button_id
        button = Button(**kwargs)

        self.pending[button_id] = (callback_name, callback_args)

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
                continue # URL button

            if component.custom_id not in self.pending:
                logger.warn("Adding a button not registered in the UI helper!")
                continue

            if str(message.id) not in self.buttons:
                self.buttons[str(message.id)] = []

            self.buttons[str(message.id)].append((component.custom_id, *self.pending[component.custom_id]))
            del self.pending[component.custom_id]

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        self.buttons.pop(str(payload.message_id), None)

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        for message_id in payload.message_ids:
            self.buttons.pop(str(message_id), None)

    def find_button_ids(self, components: Collection[Any]) -> Collection[str]:
        result = []

        for component in components:
            if component["type"] == 1:
                # Action Row, recurse
                result.extend(self.find_button_ids(component["components"]))
            elif component["type"] == 2:
                # Button
                if "custom_id" in component:
                    result.append(component["custom_id"])

        return result
                
    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        # https://discord.com/developers/docs/topics/gateway-events#message-update
        data: Mapping[str, Any] = payload.data

        author_id: int | None = data.get('author', {}).get('id', None)
        if not author_id:
            logger.warn("Message had no author!")
            return

        if author_id != str(self.bot.application_id):
            return

        components = data.get('components', [])
        button_ids = self.find_button_ids(components)

        message_id = str(payload.message_id)
        if message_id not in self.buttons:
            self.buttons[message_id] = []

        # remove popped components
        self.buttons[message_id] = list(filter(lambda button: button[0] in button_ids, self.buttons[message_id]))

        # add pending components
        for button_id in button_ids:
            if button_id not in self.pending:
                logger.warn("Adding a button not registered in the UI helper!")
                continue

            self.buttons[message_id].append((button_id, *self.pending[button_id]))
            del self.pending[button_id]

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
        with open("storage/buttons.json", "ab+") as f:
            f.seek(0)
            data = f.read()
            if len(data) == 0:
                data = b'{}'
                f.write(b'{}')
        
        self.buttons: MutableMapping[str, MutableSequence[Tuple[str, str, Collection[Any]]]] = orjson.loads(data)

        for message_id in self.buttons:
            self.buttons[message_id] = list(filter(self.check_callback_exists, self.buttons[message_id]))

        no_buttons = sum(len(buttons) for buttons in self.buttons.values())
        logger.info(f"Loaded {no_buttons} buttons")

        self.save_buttons_loop.start()

    def cog_unload(self) -> None:
        self.save_buttons_loop.stop()
        return super().cog_unload()
    
    # Save buttons
    async def save_buttons(self) -> None:
        no_buttons = sum(len(buttons) for buttons in self.buttons.values())
        logger.info(f"Saving {no_buttons} buttons")

        with open("storage/buttons.json", "wb") as f:
            f.write(orjson.dumps(self.buttons))

    @tasks.loop(minutes=5)
    async def save_buttons_loop(self) -> None:
        await self.save_buttons()

    @save_buttons_loop.after_loop
    async def save_buttons_on_shutdown(self) -> None:
        await self.save_buttons()



__all__ = ["UIHelper", "ButtonCallback", "ButtonCallbackFactory"]