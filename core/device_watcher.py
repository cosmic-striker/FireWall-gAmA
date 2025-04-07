# #!/usr/bin/env python3
# import os
# import threading
# import time
# import platform
# import subprocess
# from datetime import datetime

# class DeviceWatcher:
#     """
#     Monitors for external Wi‑Fi devices and blocks them immediately.
#     Supports Linux (pyudev) and Windows (netsh).

#     - allowed_ifaces: set of interface names to ignore (e.g. built‑in wlan0 or Wi-Fi)
#     - scan_interval: seconds between periodic scans
#     """
#     def __init__(self, allowed_ifaces=None, scan_interval=60):
#         self.allowed_ifaces = set(allowed_ifaces or [])
#         self.scan_interval = scan_interval
#         self._running = False
#         self._monitor_thread = None
#         self._scan_thread = None
#         self.os_type = platform.system().lower()

#         if self.os_type == 'linux':
#             try:
#                 import pyudev  # noqa: F401
#             except ImportError:
#                 raise RuntimeError("pyudev is required on Linux: pip install pyudev")

#     def start(self):
#         """Start monitoring (udev on Linux, polling on Windows)."""
#         self._running = True
#         if self.os_type == 'linux':
#             self._monitor_thread = threading.Thread(target=self._udev_monitor, daemon=True)
#             self._monitor_thread.start()
#         # On both Linux and Windows, also do periodic scan
#         self._scan_thread = threading.Thread(target=self._periodic_scan, daemon=True)
#         self._scan_thread.start()
#         print(f"[DeviceWatcher] Started ({self.os_type}); allowed_ifaces={self.allowed_ifaces}")

#     def stop(self):
#         """Stop monitoring."""
#         self._running = False
#         if self._monitor_thread:
#             self._monitor_thread.join()
#         if self._scan_thread:
#             self._scan_thread.join()

#     # ─── Linux Methods ──────────────────────────────────────────────────────────

#     def _udev_monitor(self):
#         """Listen for net subsystem events via pyudev (Linux only)."""
#         import pyudev
#         context = pyudev.Context()
#         monitor = pyudev.Monitor.from_netlink(context)
#         monitor.filter_by('net')
#         for action, device in monitor:
#             if not self._running:
#                 break
#             if action == 'add':
#                 self._handle_iface(device.sys_name)

#     # ─── Common Scan Loop ────────────────────────────────────────────────────────

#     def _periodic_scan(self):
#         """Regularly scan all interfaces to catch any missed ones."""
#         while self._running:
#             if self.os_type == 'linux':
#                 for iface in os.listdir('/sys/class/net'):
#                     self._handle_iface(iface)
#             elif self.os_type == 'windows':
#                 for iface in self._get_windows_wifi_ifaces():
#                     self._handle_iface(iface)
#             time.sleep(self.scan_interval)

#     # ─── Interface Handling ─────────────────────────────────────────────────────

#     def _handle_iface(self, iface):
#         """Check if `iface` is wireless and block if unauthorized."""
#         if iface in self.allowed_ifaces:
#             return

#         if self.os_type == 'linux':
#             if os.path.isdir(f"/sys/class/net/{iface}/wireless"):
#                 self._block_iface(iface)
#         elif self.os_type == 'windows':
#             # we only scan wireless ifaces on Windows
#             self._block_iface(iface)

#     # ─── Windows Helpers ────────────────────────────────────────────────────────

#     def _get_windows_wifi_ifaces(self):
#         """Return a list of wireless interface names on Windows via netsh."""
#         try:
#             output = subprocess.check_output(
#                 ['netsh', 'wlan', 'show', 'interfaces'],
#                 text=True, stderr=subprocess.DEVNULL
#             )
#         except subprocess.CalledProcessError:
#             return []

#         ifaces = []
#         for line in output.splitlines():
#             if line.strip().startswith("Name"):
#                 # e.g. "    Name                   : Wi-Fi 2"
#                 _, val = line.split(":", 1)
#                 ifaces.append(val.strip())
#         return ifaces

#     # ─── Blocking ────────────────────────────────────────────────────────────────

#     def _block_iface(self, iface):
#         """Bring interface down (Linux) or disable it (Windows) and notify."""
#         try:
#             if self.os_type == 'linux':
#                 subprocess.run(['ip', 'link', 'set', iface, 'down'], check=True)
#             elif self.os_type == 'windows':
#                 subprocess.run(
#                     ['netsh', 'interface', 'set', 'interface', iface, 'admin=disable'],
#                     check=True, shell=True
#                 )
#             msg = f"[BLOCK] {datetime.now().isoformat()} - Blocked external Wi‑Fi device: {iface}"
#             print(msg)
#             # TODO: hook into alerting system here
#         except Exception as e:
#             print(f"[ERROR] Failed to block {iface}: {e}")


# if __name__ == "__main__":
#     # --- Simple smoke test ---
#     # Adjust allowed_ifaces for your environment:
#     allowed = ['wlan0'] if platform.system().lower()=='linux' else ['Wi-Fi']
#     watcher = DeviceWatcher(allowed_ifaces=allowed, scan_interval=15)
#     watcher.start()

#     print("DeviceWatcher is running. Plug in or enable a new Wi‑Fi adapter to test.")
#     try:
#         time.sleep(60)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         watcher.stop()
#         print("DeviceWatcher stopped.")




import os
import time
import platform
import subprocess
import threading
from datetime import datetime
from plyer import notification
from playsound import playsound
import psutil
import pystray
from PIL import Image, ImageDraw

# Global Settings
ALLOWED_INTERFACES = {'Wi-Fi'}
LOG_FILE = "blocked_devices.log"
SOUND_FILE = "assets/alert.wav"  # Replace with your custom sound path

class DeviceWatcher:
    def __init__(self, allowed_ifaces):
        self.allowed_ifaces = allowed_ifaces
        self.known_ifaces = set(self._get_wifi_interfaces())
        self.os_type = platform.system().lower()
        print(f"[DeviceWatcher] Started ({self.os_type}); allowed_ifaces={self.allowed_ifaces}")
        self._create_log_file()

    def _create_log_file(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                f.write("=== Blocked Devices Log ===\n")

    def _get_wifi_interfaces(self):
        """Detect current Wi-Fi interfaces using psutil."""
        ifaces = []
        for name, snics in psutil.net_if_addrs().items():
            if 'wi-fi' in name.lower() or 'wlan' in name.lower():
                ifaces.append(name)
        return ifaces

    def _log_blocked_device(self, iface):
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Blocked: {iface}\n")

    def _notify_user(self, iface):
        notification.notify(
            title="🚨 Firewall gAmA Alert",
            message=f"Blocked unauthorized Wi-Fi device: {iface}",
            timeout=5
        )

    def _play_sound(self):
        try:
            if os.path.exists(SOUND_FILE):
                playsound(SOUND_FILE)
        except Exception as e:
            print(f"[Sound Error] {e}")

    def _block_iface(self, iface):
        try:
            if self.os_type == 'linux':
                subprocess.run(['ip', 'link', 'set', iface, 'down'], check=True)
            elif self.os_type == 'windows':
                subprocess.run(
                    ['netsh', 'interface', 'set', 'interface', iface, 'admin=disable'],
                    check=True, shell=True
                )
            msg = f"[BLOCK] {datetime.now().isoformat()} - Blocked external Wi‑Fi device: {iface}"
            print(msg)

            self._log_blocked_device(iface)
            self._notify_user(iface)
            self._play_sound()

        except Exception as e:
            print(f"[ERROR] Failed to block {iface}: {e}")

    def monitor(self):
        print("DeviceWatcher is running. Plug in or enable a new Wi‑Fi adapter to test.")
        while True:
            current = set(self._get_wifi_interfaces())
            new = current - self.known_ifaces

            for iface in new:
                if iface not in self.allowed_ifaces:
                    self._block_iface(iface)

            self.known_ifaces = current
            time.sleep(5)

# GUI Tray Icon
def create_tray_icon():
    def on_exit(icon, item):
        print("Shutting down Firewall gAmA Device Watcher.")
        icon.stop()

    image = Image.new('RGB', (64, 64), color='red')
    d = ImageDraw.Draw(image)
    d.ellipse((10, 10, 54, 54), fill='white')
    d.text((18, 25), "FW", fill='black')

    menu = pystray.Menu(pystray.MenuItem("Exit", on_exit))
    icon = pystray.Icon("Firewall gAmA", image, "Firewall gAmA", menu)
    threading.Thread(target=icon.run, daemon=True).start()

if __name__ == "__main__":
    create_tray_icon()

    watcher = DeviceWatcher(ALLOWED_INTERFACES)
    try:
        watcher.monitor()
    except KeyboardInterrupt:
        print("Exiting Firewall gAmA.")
