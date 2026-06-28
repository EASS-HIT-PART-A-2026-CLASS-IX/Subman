#!/usr/bin/env python3
"""
SubMan Pro — async refresh worker (EX3 / Sessions 09–10).

Consumes jobs from a Redis list, recalculates next_billing_date for active
subscriptions, and guarantees at-most-once side effects via Redis idempotency keys.

Features:
  - Bounded concurrency (N parallel worker loops)
  - Exponential-backoff retries per job
  - Redis-backed idempotency (skip duplicate job_id within TTL)
  - Periodic re-enqueue of refresh jobs from PostgreSQL
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import date
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

# Ensure project root is importable when executed as `python scripts/refresh.py`
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import calculate_next_billing, engine  # noqa: E402
from app.models import Subscription  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [refresh-worker] %(levelname)s %(message)s",
)
logger = logging.getLogger("refresh-worker")

# ---------------------------------------------------------------------------
# Configuration (environment-driven for Docker Compose)
# ---------------------------------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "subman:refresh:queue")
IDEMPOTENCY_PREFIX = os.getenv("IDEMPOTENCY_PREFIX", "subman:idempotency:")
CLAIM_PREFIX = os.getenv("CLAIM_PREFIX", "subman:claim:")

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))
CLAIM_TTL_SECONDS = int(os.getenv("CLAIM_TTL_SECONDS", "300"))
BRPOP_TIMEOUT = int(os.getenv("BRPOP_TIMEOUT", "5"))
ENQUEUE_INTERVAL_SECONDS = int(os.getenv("ENQUEUE_INTERVAL_SECONDS", "60"))
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "5"))


# ---------------------------------------------------------------------------
# Job helpers
# ---------------------------------------------------------------------------


def build_job_id(subscription_id: int, run_date: date | None = None) -> str:
    """Stable idempotency key — one refresh per subscription per calendar day."""
    run_date = run_date or date.today()
    return f"refresh:sub:{subscription_id}:{run_date.isoformat()}"


def wait_for_database() -> None:
    """Block until PostgreSQL accepts connections (Docker startup race)."""
    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            with Session(engine) as session:
                session.exec(select(Subscription).limit(1)).first()
            logger.info("Database connection ready")
            return
        except OperationalError as exc:
            logger.warning(
                "Database not ready (attempt %s/%s): %s",
                attempt,
                DB_CONNECT_RETRIES,
                exc,
            )
            time.sleep(3)
    raise RuntimeError("Could not connect to the database")


async def wait_for_redis(redis: Redis) -> None:
    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            await redis.ping()
            logger.info("Redis connection ready")
            return
        except Exception as exc:
            logger.warning(
                "Redis not ready (attempt %s/%s): %s",
                attempt,
                DB_CONNECT_RETRIES,
                exc,
            )
            await asyncio.sleep(2)
    raise RuntimeError("Could not connect to Redis")


# ---------------------------------------------------------------------------
# Idempotency (Redis)
# ---------------------------------------------------------------------------


async def is_job_completed(redis: Redis, job_id: str) -> bool:
    return bool(await redis.exists(f"{IDEMPOTENCY_PREFIX}{job_id}"))


async def mark_job_completed(redis: Redis, job_id: str) -> None:
    await redis.set(
        f"{IDEMPOTENCY_PREFIX}{job_id}",
        "completed",
        ex=IDEMPOTENCY_TTL_SECONDS,
    )


async def try_claim_job(redis: Redis, job_id: str) -> bool:
    """Prevent duplicate in-flight processing across worker replicas."""
    return bool(
        await redis.set(
            f"{CLAIM_PREFIX}{job_id}",
            "1",
            nx=True,
            ex=CLAIM_TTL_SECONDS,
        )
    )


async def release_claim(redis: Redis, job_id: str) -> None:
    await redis.delete(f"{CLAIM_PREFIX}{job_id}")


# ---------------------------------------------------------------------------
# Core refresh logic (sync DB I/O offloaded to thread pool)
# ---------------------------------------------------------------------------


def refresh_subscription_sync(subscription_id: int) -> dict[str, Any]:
    """
    Recalculate next_billing_date for a single subscription.
    Returns a result dict consumed by logging / metrics.
    """
    with Session(engine) as session:
        sub = session.get(Subscription, subscription_id)
        if sub is None:
            return {"status": "not_found", "subscription_id": subscription_id}

        if sub.billing_cycle == "one_time":
            return {"status": "skipped", "reason": "one_time", "name": sub.name}

        if sub.status != "active":
            return {"status": "skipped", "reason": "inactive", "name": sub.name}

        new_date = calculate_next_billing(sub.purchase_date, sub.billing_cycle)
        previous = sub.next_billing_date

        if previous == new_date:
            return {
                "status": "unchanged",
                "name": sub.name,
                "next_billing_date": new_date,
            }

        sub.next_billing_date = new_date
        session.add(sub)
        session.commit()

        return {
            "status": "updated",
            "name": sub.name,
            "previous": previous,
            "next_billing_date": new_date,
        }


def collect_refresh_jobs_sync() -> list[dict[str, Any]]:
    """Build job payloads for every eligible subscription in the ledger."""
    jobs: list[dict[str, Any]] = []
    with Session(engine) as session:
        subscriptions = session.exec(
            select(Subscription).where(
                Subscription.status == "active",
                Subscription.billing_cycle != "one_time",
            )
        ).all()

        for sub in subscriptions:
            if sub.id is None:
                continue
            job_id = build_job_id(sub.id)
            jobs.append(
                {
                    "job_id": job_id,
                    "subscription_id": sub.id,
                    "name": sub.name,
                }
            )
    return jobs


async def enqueue_refresh_jobs(redis: Redis) -> int:
    jobs = await asyncio.to_thread(collect_refresh_jobs_sync)
    if not jobs:
        logger.info("No subscriptions eligible for refresh")
        return 0

    pipeline = redis.pipeline()
    for job in jobs:
        pipeline.rpush(QUEUE_KEY, json.dumps(job))
    await pipeline.execute()

    logger.info("Enqueued %d refresh job(s) onto %s", len(jobs), QUEUE_KEY)
    return len(jobs)


# ---------------------------------------------------------------------------
# Job processing — retries + bounded concurrency
# ---------------------------------------------------------------------------


async def process_job(redis: Redis, job: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    job_id = job["job_id"]
    sub_id = job["subscription_id"]
    name = job.get("name", sub_id)

    async with semaphore:
        if await is_job_completed(redis, job_id):
            logger.info("SKIP idempotent duplicate — job_id=%s name=%s", job_id, name)
            return

        if not await try_claim_job(redis, job_id):
            logger.info("SKIP in-flight claim — job_id=%s name=%s", job_id, name)
            return

        try:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = await asyncio.to_thread(refresh_subscription_sync, sub_id)
                    await mark_job_completed(redis, job_id)
                    logger.info(
                        "DONE job_id=%s name=%s result=%s",
                        job_id,
                        name,
                        result,
                    )
                    return
                except Exception as exc:
                    if attempt >= MAX_RETRIES:
                        logger.error(
                            "FAILED job_id=%s name=%s after %s attempts: %s",
                            job_id,
                            name,
                            MAX_RETRIES,
                            exc,
                        )
                        raise
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "RETRY job_id=%s attempt=%s/%s in %.1fs — %s",
                        job_id,
                        attempt,
                        MAX_RETRIES,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
        finally:
            await release_claim(redis, job_id)


async def worker_loop(
    worker_id: int,
    redis: Redis,
    semaphore: asyncio.Semaphore,
    stop_event: asyncio.Event,
) -> None:
    logger.info("Worker loop %s started (concurrency cap=%s)", worker_id, MAX_CONCURRENCY)

    while not stop_event.is_set():
        popped = await redis.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT)
        if popped is None:
            continue

        _, raw_payload = popped
        try:
            job = json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.error("Invalid job payload: %s", raw_payload)
            continue

        try:
            await process_job(redis, job, semaphore)
        except Exception:
            # Logged inside process_job; keep the loop alive
            continue


async def periodic_enqueue_loop(redis: Redis, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await enqueue_refresh_jobs(redis)
        except Exception as exc:
            logger.error("Enqueue cycle failed: %s", exc)
        await asyncio.sleep(ENQUEUE_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_worker() -> None:
    wait_for_database()
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await wait_for_redis(redis)

    stop_event = asyncio.Event()
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    await enqueue_refresh_jobs(redis)

    worker_tasks = [
        asyncio.create_task(worker_loop(i + 1, redis, semaphore, stop_event))
        for i in range(MAX_CONCURRENCY)
    ]
    enqueuer_task = asyncio.create_task(periodic_enqueue_loop(redis, stop_event))

    logger.info(
        "Refresh worker running — queue=%s redis=%s concurrency=%s",
        QUEUE_KEY,
        REDIS_URL,
        MAX_CONCURRENCY,
    )

    try:
        await asyncio.gather(*worker_tasks, enqueuer_task)
    except asyncio.CancelledError:
        logger.info("Shutdown signal received")
        stop_event.set()
        for task in worker_tasks:
            task.cancel()
        enqueuer_task.cancel()
        await asyncio.gather(*worker_tasks, enqueuer_task, return_exceptions=True)
    finally:
        await redis.aclose()


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")


if __name__ == "__main__":
    main()
