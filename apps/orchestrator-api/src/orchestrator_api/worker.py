from __future__ import annotations

from redis import Redis
from rq import Worker

from orchestrator_api.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    w = Worker(["indexing"], connection=redis)
    w.work(with_scheduler=False)


if __name__ == "__main__":
    main()

