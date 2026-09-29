"""API launcher supporting psycopg async checkpoints on native Windows."""
import argparse
import asyncio
import sys

import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = uvicorn.Server(uvicorn.Config("app.main:app", host=args.host, port=args.port))
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    with asyncio.Runner(loop_factory=factory) as runner:
        runner.run(server.serve())


if __name__ == "__main__":
    main()
