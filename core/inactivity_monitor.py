#!/usr/bin/env python3
import os
import time
import threading
import subprocess
import platform
import re
from datetime import datetime, timedelta

from scapy.all import sniff, conf, IP
from plyer import notification
from playsound import playsound
import pystray
from PIL import Image, ImageDraw

# ─── Configuration ────────────────────────────────────────────────────────────

IDLE_TIMEOUT    = 10          # seconds for testing (set to 3600 for 1 hour)
CHECK_INTERVAL  = 5           # seconds between idle‐checks
LOG_FILE        = "inactivity_log.log"
SOUND_FILE      = "assets/idle_alert.wav"
AGGRESSIVE_MODE = True        # True to block at host‐firewall, False = safe mode

# ─── Globals ──────────────────────────────────────────────────────────────────

last_activity = {}   # IP → datetime of last seen packet or seed time
blocked_ips   = set()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().isoformat(sep=' ', timespec='seconds')
    line = f"[{ts}] {msg}"
    print(line)
    # write in UTF-8 so emojis don’t error on Windows
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def notify(title: str, message: str):
    notification.notify(title=title, message=message, timeout=5)

def play_sound():
    if os.path.exists(SOUND_FILE):
        try:
            playsound(SOUND_FILE)
        except Exception as e:
            print(f"[Sound Error] {e}")

def block_ip(ip: str):
    """Block `ip` at the host firewall."""
    os_type = platform.system().lower()
    try:
        if os_type == "windows":
            # inbound
            subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=Firewall gAmA block {ip}",
                "dir=in", "action=block", f"remoteip={ip}"
            ], check=True, shell=True)
            # outbound
            subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=Firewall gAmA block {ip}",
                "dir=out", "action=block", f"remoteip={ip}"
            ], check=True, shell=True)

        elif os_type == "linux":
            subprocess.run(["iptables", "-I", "INPUT",  "-s", ip, "-j", "DROP"],  check=True)
            subprocess.run(["iptables", "-I", "OUTPUT", "-d", ip, "-j", "DROP"],  check=True)

        log(f"🔒 Blocked IP {ip} at host firewall")
    except Exception as e:
        log(f"[ERROR] Failed to block {ip}: {e}")

# ─── Packet Sniffer ───────────────────────────────────────────────────────────

def packet_handler(pkt):
    if IP in pkt:
        now = datetime.now()
        for addr in (pkt[IP].src, pkt[IP].dst):
            last_activity[addr] = now

def start_sniffer():
    iface = conf.iface
    log(f"Starting packet sniffer on interface: {iface}")
    sniff(prn=packet_handler, store=False, filter="ip", iface=iface)

# ─── ARP Discovery & Idle Checker ─────────────────────────────────────────────

def discover_devices():
    """Return a set of IPs discovered via ARP table (cross‐platform)."""
    ips = set()
    os_type = platform.system().lower()

    try:
        if os_type == "windows":
            out = subprocess.check_output(["arp", "-a"], text=True)
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith("Interface") or line.startswith("Internet"):
                    continue
                parts = line.split()
                ip = parts[0]
                if re.match(r"\d+\.\d+\.\d+\.\d+", ip):
                    ips.add(ip)
        else:  # linux / mac
            out = subprocess.check_output(["arp", "-n"], text=True)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 1 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
                    ips.add(parts[0])
    except Exception as e:
        log(f"[ERROR] ARP discovery failed: {e}")

    return ips

def idle_checker():
    while True:
        now = datetime.now()
        ips = discover_devices()

        for ip in ips:
            # skip broadcast
            if ip == "255.255.255.255":
                continue

            # seed new devices
            if ip not in last_activity:
                last_activity[ip] = now
                log(f"Discovered device {ip}, seeding timer")

        for ip, last in list(last_activity.items()):
            if ip == "255.255.255.255":
                continue

            idle = (now - last).total_seconds()
            if idle >= IDLE_TIMEOUT and ip not in blocked_ips:
                log(f"Idle detected: {ip} (idle ≥ {IDLE_TIMEOUT}s)")
                notify("Firewall gAmA", f"Device {ip} idle for ≥{IDLE_TIMEOUT}s")
                play_sound()
                if AGGRESSIVE_MODE:
                    block_ip(ip)
                blocked_ips.add(ip)

        time.sleep(CHECK_INTERVAL)

# ─── Tray Icon ────────────────────────────────────────────────────────────────

def create_tray_icon():
    def on_exit(icon, item):
        log("Shutting down Inactivity Monitor.")
        icon.stop()
        os._exit(0)

    img = Image.new('RGB', (64, 64), color='red')
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill='white')
    d.text((18, 25), "ID", fill='black')

    menu = pystray.Menu(pystray.MenuItem("Exit", on_exit))
    icon = pystray.Icon("InactivityMonitor", img, "Firewall gAmA", menu)
    threading.Thread(target=icon.run, daemon=True).start()

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("=== Inactivity Log ===\n")

    create_tray_icon()
    threading.Thread(target=start_sniffer, daemon=True).start()
    idle_checker()

