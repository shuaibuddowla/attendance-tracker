# 🎴 ClassMate IoT Attendance Station (ESP32 + RC522)

[![ClassMate Ecosystem](https://img.shields.io/badge/Companion-ClassMate%20App-6366f1?style=for-the-badge&logo=android)](https://github.com/shuaibuddowla/ClassMate)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Hardware: ESP32](https://img.shields.io/badge/Hardware-ESP32%20%7C%20RC522-blue?style=for-the-badge&logo=espressif)](firmware/WIRING_GUIDE.md)

An open-source, dual-mode IoT hardware attendance station built with an **ESP32 microcontroller**, **RC522 13.56 MHz RFID Reader**, **0.96" SSD1306 OLED Display**, active buzzer, and dual status LEDs.

Designed as the dedicated hardware scanner companion for **[ClassMate](https://github.com/shuaibuddowla/ClassMate)** (with live cloud session synchronization, course marquee ticker, and instant push notifications), while also including a **standalone Python FastAPI Web Dashboard** for independent laboratory or office deployments.

---

## 🚀 Key Capabilities

### 🎓 1. Native ClassMate Cloud Integration
- **Live Classroom Marquee**: Polls ClassMate `/api/scan?device_id=...` heartbeat. When an admin or CR opens an attendance session, the OLED automatically powers on and scrolls the active course code & title (e.g. `CSE 2114 - Software Development Project`).
- **Instant Student Verification**: Checks card UIDs against student profiles, verifies batch isolation, marks attendance idempotently, and fires student notifications in real time.
- **Auto-Sleep Power Saving**: When no session is active, the station puts its OLED display to sleep to prevent burn-in and save energy.

### 🏢 2. Standalone Local FastAPI Mode
- **Zero-Cloud Local Logging**: Works in isolated LAN environments with a bundled Python FastAPI backend and SQLite database.
- **Smart Check-In / Check-Out Toggle**: Automatically computes daily scan history to toggle status.
- **Real-Time WebSocket Feed**: Instant live event syncing in the browser without manual refreshing.
- **1-Click Card Enrollment & CSV Export**: Triage unknown cards directly from the web dashboard.

### 🔊 3. Multi-Sensory Hardware Feedback
- **Attendance Marked**: Clean high-pitch double chime + Green LED pulse.
- **Warning / Unregistered Card**: 3 warning beeps + Red LED alert.
- **Cooldown Debounce**: 2000 ms hardware debounce prevents accidental duplicate card swipes.

---

## 📁 Repository Structure

```text
attendance-tracker/
├── firmware/
│   ├── esp32_rfid_attendance/
│   │   └── esp32_rfid_attendance.ino  # ESP32 C++ Arduino firmware (OLED + RFID + Cloud/Local API)
│   ├── diagnostic_test/               # Hardware verification suite
│   ├── rc522_diagnostic/              # SPI and version register inspector
│   ├── esp32_gpio_test/               # LED & Buzzer testing sketch
│   ├── spi_loopback/                  # Hardware bus integrity validator
│   └── WIRING_GUIDE.md                # Pinout tables, schematics & connection guide
├── backend/
│   ├── app/
│   │   ├── crud.py                    # Attendance records, debounce & user management
│   │   ├── database.py                # SQLite database session engine
│   │   ├── main.py                    # FastAPI server & WebSocket manager
│   │   ├── models.py                  # SQLAlchemy models
│   │   └── schemas.py                 # Pydantic schemas
│   ├── static/                        # Live dashboard UI & WebSocket client
│   ├── templates/                     # Responsive Tailwind CSS dashboard
│   ├── requirements.txt               # Python dependencies
│   └── run.py                         # Local server launcher with auto-IP resolution
├── cp2102_setup_exe/                  # CP2102 USB drivers for ESP32 DevKit
├── driver_cp210x/                     # Direct driver installer scripts
├── build_enclosure.py                 # Parametric 3D printable enclosure generator
└── README.md
```

---

## 🔌 Hardware Setup & Wiring

Refer to [`firmware/WIRING_GUIDE.md`](firmware/WIRING_GUIDE.md) for complete circuit schematics.

### ESP32 38-Pin Layout Table:

| Peripheral | Component Pin | ESP32 GPIO | Notes |
| :--- | :--- | :--- | :--- |
| **RC522 RFID** | VCC | **3V3** | **Do NOT connect to 5V!** |
| | RST | **GPIO 4** | Configured in firmware |
| | GND | **GND** | Common ground |
| | MISO | **GPIO 19** | SPI Master In Slave Out |
| | MOSI | **GPIO 23** | SPI Master Out Slave In |
| | SCK | **GPIO 18** | SPI Serial Clock |
| | SDA (SS) | **GPIO 5** | SPI Slave Select |
| **SSD1306 OLED** | VCC | **3V3** | 0.96" I2C Display (128x64) |
| | GND | **GND** | Common ground |
| | SCL | **GPIO 22** | I2C Clock |
| | SDA | **GPIO 21** | I2C Data |
| **Indicators** | Buzzer (+) | **GPIO 27** | Active Piezo Buzzer |
| | Green LED (+) | **GPIO 25** | via 220Ω resistor |
| | Red LED (+) | **GPIO 26** | via 220Ω resistor |
| | All (-) | **GND** | Common ground |

---

## ⚡ Quick Start: Firmware Flashing

1. Open Arduino IDE and install required libraries via Library Manager:
   - **MFRC522** (by GithubCommunity)
   - **Adafruit SSD1306** & **Adafruit GFX Library**
   - **ArduinoJson** (v6 or v7)
2. Open [`firmware/esp32_rfid_attendance/esp32_rfid_attendance.ino`](firmware/esp32_rfid_attendance/esp32_rfid_attendance.ino).
3. Configure your network credentials and target endpoint:
   ```cpp
   // Replace with your local 2.4 GHz Wi-Fi credentials
   const char* WIFI_SSID     = "YOUR_2_4_GHZ_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

   // Target API Endpoint:
   // Option A (ClassMate Cloud): "https://<your-classmate-deployment>.vercel.app/api/scan"
   // Option B (Local FastAPI):   "http://<YOUR_PC_LAN_IP>:8000/api/scan"
   const char* SERVER_URL    = "https://classmatebd.vercel.app/api/scan";
   const char* DEVICE_ID     = "ESP32-READER-01";
   ```
4. Connect your ESP32 via micro-USB, select **ESP32 Dev Module**, and click **Upload**.

---

## 💻 Standalone Local FastAPI Backend

If deploying independently without the ClassMate cloud app:

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch server with automatic LAN IP broadcast
python run.py
```

Access the dashboard:
- **Local Browser**: `http://localhost:8000`
- **LAN Dashboard**: `http://<YOUR_PC_IP>:8000`
- **Scanner Endpoint**: `http://<YOUR_PC_IP>:8000/api/scan`

---

## 🔒 Security Best Practices
- Never commit real Wi-Fi passwords, server secrets, or private tokens to public repositories.
- Keep firmware credentials parameterized or use ESP32 `WiFiManager` for dynamic runtime captive portal setup if desired.
- All communications with ClassMate Cloud use secure TLS/HTTPS.

---

## 🤝 Contributing & License
Distributed under the **MIT License**. Part of the **[ClassMate](https://github.com/shuaibuddowla/ClassMate)** ecosystem developed for the Department of Computer Science & Engineering, MBSTU.
