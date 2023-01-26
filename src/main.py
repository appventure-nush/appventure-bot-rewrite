import uvicorn
import uvloop

from bot.bot import main
from server.server import app  # noqa: F401

if __name__ == "__main__":
    print("Starting bot...")

    uvloop.install()

    config = uvicorn.Config("main:app", port=3000, host="0.0.0.0")
    server = uvicorn.Server(config)

    main(server.serve())
