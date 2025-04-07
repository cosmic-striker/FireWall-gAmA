#!/usr/bin/env python3
import os
import threading
import time
from datetime import datetime, timedelta

class Logger:
    """
    Per‑user daily logs with retention and size‑cap enforcement.

    - log_dir: directory to store logs
    - retention_days: how many days to keep log files
    - max_size_gb: max bytes per user‑per‑day log before rotation
    - warning_threshold: fraction of max_size to warn at (e.g. 0.9 = 90%)
    """
    def __init__(self,
                 log_dir="logs",
                 retention_days=5,
                 max_size_gb=1,
                 warning_threshold=0.9):
        self.log_dir = log_dir
        self.retention_days = retention_days
        self.max_size = max_size_gb * 1024**3
        self.warning_threshold = warning_threshold
        self._lock = threading.Lock()

        os.makedirs(self.log_dir, exist_ok=True)

    def log(self, user: str, action: str):
        """Log an action for `user`, prune old files, enforce size cap."""
        with self._lock:
            self._prune_old_logs()

            path = self._user_log_path(user)
            size = os.path.getsize(path) if os.path.exists(path) else 0

            # Warning
            if size >= self.max_size * self.warning_threshold:
                self._warn_size(user, size)

            # Rotate if over cap
            if size >= self.max_size:
                self._rotate(path)

            # Append new entry
            timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
            with open(path, "a") as f:
                f.write(f"{timestamp} | {user} | {action}\n")

    def _user_log_path(self, user: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{user}_{date_str}.log"
        return os.path.join(self.log_dir, filename)

    def _prune_old_logs(self):
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for fname in os.listdir(self.log_dir):
            try:
                # Expect filenames like user_YYYY‑MM‑DD.log
                date_part = fname.rsplit("_", 1)[1].rsplit(".",1)[0]
                file_date = datetime.strptime(date_part, "%Y-%m-%d")
            except Exception:
                continue
            if file_date < cutoff:
                os.remove(os.path.join(self.log_dir, fname))
                print(f"[PRUNE] Removed old log: {fname}")

    def _warn_size(self, user: str, size: int):
        gb = size / 1024**3
        print(f"[WARNING] {user}'s log is at {gb:.2f} GB (≥{self.warning_threshold*100:.0f}% of quota)")

    def _rotate(self, path: str):
        rotated = path + ".1"
        # remove previous rotated if exists
        if os.path.exists(rotated):
            os.remove(rotated)
        os.rename(path, rotated)
        print(f"[ROTATE] Rotated log file: {os.path.basename(path)} → {os.path.basename(rotated)}")


if __name__ == "__main__":
    # --- Simple smoke test ---
    lg = Logger(log_dir="logs_test", retention_days=1, max_size_gb=0.000001)  # tiny cap
    users = ["alice", "bob"]

    # write enough entries to trigger rotate for alice
    for i in range(10):
        for u in users:
            lg.log(u, f"action_{i}")
        time.sleep(0.1)

    # Check that prune runs (we only keep today's files, but if you create older dated files in logs_test/)
    print("Done smoke test. Inspect logs_test/ for .log and .log.1 files.")
