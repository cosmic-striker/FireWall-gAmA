#!/usr/bin/env python3
import time
import threading
from datetime import datetime, timedelta

class SessionManager:
    """
    Tracks user sessions and enforces an idle-timeout policy.
    - idle_timeout: seconds of inactivity before disconnect (default 3600s = 1h)
    - warning_before: seconds before timeout to issue a warning (default 300s = 5min)
    - check_interval: how often (in seconds) to scan sessions (default 300s = 5min)
    """
    def __init__(self, idle_timeout=3600, warning_before=300, check_interval=300):
        self.idle_timeout = timedelta(seconds=idle_timeout)
        self.warning_before = timedelta(seconds=warning_before)
        self.check_interval = check_interval

        # session_id → last_activity timestamp
        self._sessions = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        """Begin background monitoring."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join()

    def update_activity(self, session_id):
        """Call this whenever a user performs an action."""
        with self._lock:
            self._sessions[session_id] = datetime.now()
            # print(f"[DEBUG] Updated activity for session {session_id}")

    def remove_session(self, session_id):
        """Remove a session (e.g. on logout)."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def _monitor_loop(self):
        """Background thread: warn and disconnect idle sessions."""
        while self._running:
            now = datetime.now()
            with self._lock:
                for session_id, last in list(self._sessions.items()):
                    idle = now - last

                    # Issue warning if within warning window
                    if idle >= (self.idle_timeout - self.warning_before) and idle < self.idle_timeout:
                        self._warn(session_id, idle)

                    # Disconnect if fully timed out
                    if idle >= self.idle_timeout:
                        self._disconnect(session_id)

            time.sleep(self.check_interval)

    def _warn(self, session_id, idle_time):
        # TODO: hook into your alerting system instead of print()
        print(f"[WARNING] Session '{session_id}' idle for {idle_time}. "
              f"Will disconnect in {(self.idle_timeout - idle_time)}.")

    def _disconnect(self, session_id):
        # TODO: replace with actual disconnect logic (e.g. terminate socket)
        print(f"[DISCONNECT] Session '{session_id}' disconnected after {self.idle_timeout} of inactivity.")
        self._sessions.pop(session_id, None)


if __name__ == "__main__":
    # --- Simple smoke test ---
    sm = SessionManager(idle_timeout=5, warning_before=5, check_interval=2)
    sm.start()

    # Simulate two sessions
    sm.update_activity("alice")
    sm.update_activity("bob")

    print("Started session manager; 'alice' and 'bob' are active.")

    # After 6s, update alice to keep her alive past warning
    time.sleep(6)
    sm.update_activity("alice")
    print("Refreshed 'alice' at ~6s")

    # Let it run long enough to disconnect both
    time.sleep(10)
    sm.stop()
    print("Session manager stopped.")
    print("Test complete.")