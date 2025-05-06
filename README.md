
# 🔥 Firewall gAmA - Inactivity Monitor Module

This module is a part of the **Firewall gAmA** project and is responsible for monitoring **inactivity** across all devices connected to the local network. It determines which devices have been idle (low or no network activity) for a specific time window and flags them.

## 📌 Features

- ✅ Scans and lists all connected devices on the local network.
- ✅ Tracks upload/download network activity per device.
- ✅ Flags devices as **inactive** if bandwidth usage is below a threshold over a defined time interval.
- ✅ Logs inactive devices with IP, MAC address, and duration of inactivity.

## 🚀 Technologies Used

- Python 3
- `psutil` (for network usage)
- `scapy` (for ARP scan)
- Standard libraries (`time`, `threading`, `collections`, `datetime`)

## 📂 Project Structure

```

inactivity\_monitor/
├── inactivity\_monitor.py
├── requirements.txt
└── logs/
└── inactive\_devices.log

````

## ⚙️ How It Works

1. **ARP Scan** is used to discover all devices connected to the local subnet.
2. For each detected IP/MAC address, the system monitors **data sent and received**.
3. If a device does not cross the minimum threshold (e.g., 1 KB/s) over a user-defined time (e.g., 5 minutes), it is flagged as **inactive**.
4. Inactive devices are written to a log file with a timestamp.

## 📥 Installation

```bash
git clone https://github.com/yourusername/firewall-gama.git
cd firewall-gama/inactivity_monitor
pip install -r requirements.txt
````

## 🖥️ Usage

```bash
python3 inactivity_monitor.py
```

> Make sure to run the script with sudo privileges for ARP scanning and network interface access.

## 📝 Configuration

You can modify the following settings in `inactivity_monitor.py`:

* `CHECK_INTERVAL` – how often to check usage (in seconds)
* `INACTIVITY_THRESHOLD` – how little traffic qualifies as inactivity
* `INACTIVITY_TIME_LIMIT` – how long the device must be idle to be flagged

## 📄 Sample Output (Console)

```
[Inactive] 192.168.1.5 (MAC: AA:BB:CC:DD:EE:FF) - 7 mins idle
[Inactive] 192.168.1.9 (MAC: FF:EE:DD:CC:BB:AA) - 12 mins idle
```

## 🧪 Future Work

* GUI dashboard with charts and device control
* Export logs to CSV or integrate with SQLite
* Real-time alert system via email or push notifications
* Integration with other Firewall gAmA modules

## 👨‍💻 Authors

* Developed by: \[Your Name]

## 📜 License

MIT License

```

