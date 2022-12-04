import uvicorn
import uvloop

from bot.bot import main
from server.server import app # type: ignore

if __name__ == "__main__":
    uvloop.install()

    config = uvicorn.Config("main:app", port=3000)
    server = uvicorn.Server(config)

    main(server.serve())
