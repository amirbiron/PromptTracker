"""
MongoDB-based distributed lock with TTL and heartbeat.
"""
from __future__ import annotations

import atexit
import logging
import os
import random
import signal
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError, DuplicateKeyError

import config

logger = logging.getLogger(__name__)


@dataclass
class LockConfig:
    service_id: str
    instance_id: str
    host: str
    lease_seconds: int
    heartbeat_interval: int
    wait_for_acquire: bool
    acquire_max_wait: int  # seconds, 0 = unlimited
    backoff_min_seconds: int
    backoff_max_seconds: int


class MongoDistributedLock:
    def __init__(
        self,
        mongo_uri: str,
        db_name: str,
        collection_name: str = "bot_locks",
        lock_cfg: Optional[LockConfig] = None,
    ) -> None:
        # Initialize Mongo client early; validate that URI is usable
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]

        # Build config with fallbacks
        hostname = socket.gethostname() or "unknown-host"
        pid = os.getpid()
        instance_id = (
            config.RENDER_INSTANCE_ID
            or os.getenv("INSTANCE_ID")
            or f"{hostname}:{pid}"
        )
        host = config.RENDER_SERVICE_NAME or hostname

        self.cfg = lock_cfg or LockConfig(
            service_id=config.SERVICE_ID,
            instance_id=instance_id,
            host=host,
            lease_seconds=max(5, int(config.LOCK_LEASE_SECONDS)),
            heartbeat_interval=max(5, int(config.LOCK_HEARTBEAT_INTERVAL)),
            wait_for_acquire=bool(config.LOCK_WAIT_FOR_ACQUIRE),
            acquire_max_wait=max(0, int(config.LOCK_ACQUIRE_MAX_WAIT)),
            backoff_min_seconds=max(1, int(config.LOCK_WAIT_MIN_SECONDS)),
            backoff_max_seconds=max(1, int(config.LOCK_WAIT_MAX_SECONDS)),
        )

        # Internal state
        self._stop_event = threading.Event()
        self._hb_thread: Optional[threading.Thread] = None
        self._is_owner = False

        # One-time configuration log to aid diagnostics (safe, no secrets)
        logger.info(
            "Distributed lock config: service_id=%s instance_id=%s host=%s lease=%ss heartbeat=%ss wait_for_acquire=%s backoff=%s-%ss",
            self.cfg.service_id,
            self.cfg.instance_id,
            self.cfg.host,
            self.cfg.lease_seconds,
            self.cfg.heartbeat_interval,
            self.cfg.wait_for_acquire,
            self.cfg.backoff_min_seconds,
            self.cfg.backoff_max_seconds,
        )

        # Proactive connectivity check so failures are visible and we don't start polling
        try:
            self.client.admin.command("ping")
        except PyMongoError as exc:
            logger.error("Failed to connect to MongoDB (ping): %s", exc)
            raise

        self._ensure_indexes()

        # Ensure clean release on shutdown
        atexit.register(self.release)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._handle_signal)
            except Exception:
                # Not all environments allow setting signals (e.g., threads)
                pass

    def _ensure_indexes(self) -> None:
        try:
            # TTL index on expiresAt ensures orphaned locks are cleared automatically
            self.collection.create_index(
                [("expiresAt", ASCENDING)], name="ttl_expiresAt", expireAfterSeconds=0
            )
        except PyMongoError as exc:
            # Escalate so the bot does not continue without a working DB
            logger.error("Failed to ensure TTL index on bot_locks: %s", exc)
            raise

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _try_acquire(self) -> bool:
        now = self._now()
        expires = now + timedelta(seconds=self.cfg.lease_seconds)
        # Step 1: try to update an existing (expired or re-entrant) doc without upsert
        try:
            result = self.collection.update_one(
                {
                    "_id": self.cfg.service_id,
                    "$or": [
                        {"expiresAt": {"$lte": now}},  # expired
                        {"owner": self.cfg.instance_id},  # re-entrance by same owner
                        {"expiresAt": {"$exists": False}},  # not initialized
                    ],
                },
                {
                    "$set": {
                        "owner": self.cfg.instance_id,
                        "host": self.cfg.host,
                        "updatedAt": now,
                        "expiresAt": expires,
                    }
                },
                upsert=False,
            )
            if result.modified_count == 1:
                self._is_owner = True
                logger.info(
                    "Acquired distributed lock '%s' as %s on %s (lease=%ss)",
                    self.cfg.service_id,
                    self.cfg.instance_id,
                    self.cfg.host,
                    self.cfg.lease_seconds,
                )
                return True
        except PyMongoError as exc:
            logger.error("Lock acquire update failed: %s", exc)
            return False

        # Step 2: try to insert a new doc (first writer wins). Treat DuplicateKey as contention.
        try:
            self.collection.insert_one(
                {
                    "_id": self.cfg.service_id,
                    "owner": self.cfg.instance_id,
                    "host": self.cfg.host,
                    "createdAt": now,
                    "updatedAt": now,
                    "expiresAt": expires,
                }
            )
            self._is_owner = True
            logger.info(
                "Acquired distributed lock '%s' as %s on %s (lease=%ss)",
                self.cfg.service_id,
                self.cfg.instance_id,
                self.cfg.host,
                self.cfg.lease_seconds,
            )
            return True
        except DuplicateKeyError:
            # Another instance inserted the doc concurrently: lock is held by someone else
            logger.info("Lock '%s' currently held by another instance", self.cfg.service_id)
            return False
        except PyMongoError as exc:
            logger.error("Lock acquire insert failed: %s", exc)
            return False

    def acquire_blocking(self) -> None:
        start_ts = time.time()
        if self.cfg.wait_for_acquire:
            # Active wait with optional max timeout
            while not self._try_acquire():
                if self.cfg.acquire_max_wait > 0 and (time.time() - start_ts) > self.cfg.acquire_max_wait:
                    logger.warning(
                        "Lock acquire timed out after %ss; exiting.",
                        self.cfg.acquire_max_wait,
                    )
                    # Exit gracefully to allow platform to restart us later
                    raise SystemExit(0)
                time.sleep(1)
        else:
            # Passive wait with randomized backoff; never exits
            while not self._try_acquire():
                backoff = random.uniform(
                    self.cfg.backoff_min_seconds, self.cfg.backoff_max_seconds
                )
                logger.info(
                    "Lock held by another instance. Waiting %.1fs before retry...",
                    backoff,
                )
                time.sleep(backoff)

    def start_heartbeat(self) -> None:
        if not self._is_owner:
            return
        if self._hb_thread and self._hb_thread.is_alive():
            return
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, name="lock-heartbeat", daemon=True)
        self._hb_thread.start()

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self.cfg.heartbeat_interval)
            if self._stop_event.is_set():
                break
            now = self._now()
            new_expiry = now + timedelta(seconds=self.cfg.lease_seconds)
            try:
                result = self.collection.update_one(
                    {"_id": self.cfg.service_id, "owner": self.cfg.instance_id},
                    {"$set": {"expiresAt": new_expiry, "updatedAt": now}},
                    upsert=False,
                )
                if result.matched_count == 0:
                    logger.error("Lost distributed lock; terminating to avoid duplicate polling")
                    os._exit(0)
            except PyMongoError as exc:
                logger.error("Heartbeat failed: %s", exc)
                # Keep trying; a transient error shouldn't drop the lock immediately

    def release(self) -> None:
        if not self._is_owner:
            return
        self._stop_event.set()
        try:
            self.collection.delete_one(
                {"_id": self.cfg.service_id, "owner": self.cfg.instance_id}
            )
            logger.info(
                "Released distributed lock '%s' from %s",
                self.cfg.service_id,
                self.cfg.instance_id,
            )
        except Exception as exc:
            logger.warning("Failed to release lock: %s", exc)
        finally:
            self._is_owner = False

    def _handle_signal(self, signum, frame):  # noqa: D401
        # Release lock and exit promptly
        try:
            self.release()
        finally:
            raise SystemExit(0)
