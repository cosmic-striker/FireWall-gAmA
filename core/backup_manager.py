#!/usr/bin/env python3
import os
import threading
import time
from datetime import datetime, timedelta
import tarfile

class BackupManager:
    """
    Automates periodic backups of a directory and prunes old backups.

    - source_dir: directory to back up (e.g. "logs")
    - backup_dir: where to store archives (e.g. "backups")
    - retention_days: how many days to keep backups
    - interval_hours: how often to run a backup (default: 24h)
    """
    def __init__(self,
                 source_dir="logs",
                 backup_dir="backups",
                 retention_days=5,
                 interval_hours=24):
        self.source_dir = source_dir
        self.backup_dir = backup_dir
        self.retention_days = retention_days
        self.interval = interval_hours * 3600  # in seconds

        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        """Begin background backup loop."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._backup_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop background backup loop."""
        self._running = False
        if self._thread:
            self._thread.join()

    def _backup_loop(self):
        """Internal loop: backup + prune, then sleep."""
        while self._running:
            self.backup_once()
            time.sleep(self.interval)

    def backup_once(self):
        """Perform a single backup + prune old archives."""
        with self._lock:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_name = f"backup-{timestamp}.tar.gz"
            archive_path = os.path.join(self.backup_dir, archive_name)

            # Create tar.gz archive of source_dir
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(self.source_dir, arcname=os.path.basename(self.source_dir))
            print(f"[BACKUP] Created archive: {archive_name}")

            # Prune old backups
            self._prune_old_backups()

    def _prune_old_backups(self):
        """Delete backup files older than retention_days."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for fname in os.listdir(self.backup_dir):
            if not fname.startswith("backup-") or not fname.endswith(".tar.gz"):
                continue
            date_part = fname[len("backup-"):-len(".tar.gz")]
            try:
                file_date = datetime.strptime(date_part, "%Y%m%d-%H%M%S")
            except ValueError:
                continue

            if file_date < cutoff:
                path = os.path.join(self.backup_dir, fname)
                os.remove(path)
                print(f"[PRUNE] Removed old backup: {fname}")


if __name__ == "__main__":
    # --- Simple smoke test ---
    # Set a short interval and retention for quick testing
    bm = BackupManager(source_dir="logs_test",
                       backup_dir="backups_test",
                       retention_days=0,    # prune everything older than now
                       interval_hours=0.001)  # ~3.6s
    bm.start()

    # Simulate some log files
    os.makedirs("logs_test", exist_ok=True)
    for i in range(3):
        with open(f"logs_test/dummy_{i}.txt", "w") as f:
            f.write("test\n")
        time.sleep(1)

    # Let it run two backups
    time.sleep(8)
    bm.stop()
    print("Smoke test complete. Check backups_test/ for archives and prunes.")
