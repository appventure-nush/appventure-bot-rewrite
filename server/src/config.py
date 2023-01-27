import os


class Config:
    __slots__ = ("ipc_secret",)

    def __init__(self) -> None:
        self.ipc_secret = os.environ["IPC_SECRET"]


config = Config()

__all__ = ["config"]
