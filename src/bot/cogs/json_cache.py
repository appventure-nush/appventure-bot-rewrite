import logging
from typing import Callable, MutableMapping, Any, Optional, Tuple
from nextcord.ext.commands import Cog, Bot
from nextcord.ext import tasks

import orjson

logger = logging.getLogger(__name__)

class JSONCache(Cog):
    __slots__ = "bot", "json_caches"

    def __init__(self, bot: Bot) -> None:
        super().__init__()

        self.bot = bot
        self.json_caches: MutableMapping[str, Tuple[Callable[[MutableMapping[str, Any]], None], MutableMapping[str, Any]]] = {}

    def register_cache(self, cache_name: str, do_before_save: Optional[Callable[[MutableMapping[str, Any]], None]] = None) -> MutableMapping[str, Any]:
        if not do_before_save:
            _do_before_save: Callable[[MutableMapping[str, Any]], None] = lambda _: None
        else:
            _do_before_save = do_before_save
        
        try:
            with open(f"storage/{cache_name}.json", "rb") as f:
                data = f.read()
        except FileNotFoundError:
            data = b"{}"
        
        cache: MutableMapping[str, Any] = orjson.loads(data)

        logger.info(f"Loaded {len(cache)} records in {cache_name}.json")

        self.json_caches[cache_name] = (_do_before_save, cache)
        return cache

    @Cog.listener()
    async def on_connect(self) -> None:
        self.save_data_loop.start()

    def save_data(self) -> None:
        for cache_name, (call_fn, cache) in self.json_caches.items():
            call_fn(cache)

            with open(f"storage/{cache_name}.json", "wb") as f:
                f.write(orjson.dumps(cache))
            
            logger.info(f"Saved {len(cache)} records in {cache_name}.json")
            
    @tasks.loop(minutes=5)
    async def save_data_loop(self) -> None:
        self.save_data()

    @save_data_loop.after_loop
    async def save_data_on_shutdown(self) -> None:
        self.save_data()

    def cog_unload(self) -> None:
        self.save_data_loop.cancel()
        return super().cog_unload()

__all__ = ["JSONCache"]