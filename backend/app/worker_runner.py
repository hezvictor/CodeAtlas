"""Native Windows worker entry point; Docker/Linux also supports the arq CLI."""
import asyncio
import sys


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from arq.worker import run_worker

    from .worker import WorkerSettings
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
