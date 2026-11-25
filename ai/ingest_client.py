"""Background poster so inference does not wait on the backend.

``requests.post`` used to run inside the frame loop with a 1 second timeout.
A slow or down API stalled detection. This client queues payloads and drops
the oldest entry when the queue is full.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)


class AsyncIngestClient:
    def __init__(
        self,
        url: str,
        timeout: float = 2.0,
        max_queue: int = 4,
        session_factory: Optional[Callable[[], object]] = None,
    ):
        self.url = url
        self.timeout = timeout
        self.max_queue = max(1, int(max_queue))
        self._queue: queue.Queue = queue.Queue(maxsize=self.max_queue)
        self._stop = threading.Event()
        self.sent = 0
        self.failed = 0
        self.dropped = 0
        self._session_factory = session_factory or requests.Session
        self._thread = threading.Thread(target=self._run, name="ingest-client", daemon=True)
        self._thread.start()

    def submit(self, payload: dict) -> None:
        """Enqueue ``payload``. Returns immediately."""
        try:
            self._queue.put_nowait(payload)
            return
        except queue.Full:
            pass
        try:
            self._queue.get_nowait()
            self.dropped += 1
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            self.dropped += 1

    def _run(self) -> None:
        session = self._session_factory()
        while not self._stop.is_set():
            try:
                payload = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                response = session.post(self.url, json=payload, timeout=self.timeout)
                status = getattr(response, "status_code", 0)
                if status == 200:
                    self.sent += 1
                else:
                    self.failed += 1
                    logger.warning("Ingest HTTP %s", status)
            except Exception as exc:
                self.failed += 1
                logger.warning("Ingest failed: %s", exc)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.5)
