# ESP32 + RC522 RFID + OLED Attendance Tracker - Hardware Wiring Guide

This guide details the exact hardware connections between your **38-Pin ESP32**, the **RC522 RFID Reader (13.56 MHz)**, **0.96" I2C OLED Display**, **3-Pin Active Buzzer**, **Capacitor**, and **Status LEDs**.

---

## ⚠️ Critical Power Note
> **IMPORTANT:** The RC522 module and OLED display operate strictly on **3.3V**. Connecting the RC522 `VCC` pin to `5V` or `VIN` will permanently burn or damage the module! Connect `VCC` only to the ESP32's **3V3** pin.

---

## 1. Complete Pinout Table

| Peripheral | Component Pin | ESP32 Pin | Notes / Description |
| :--- | :--- | :--- | :--- |
| **0.96" OLED (SSD1306)** | **VDD / VCC** | **3V3** | 3.3V Power rail |
| | **GND** | **GND** | Ground rail |
| | **SCK / SCL** | **GPIO 22** | Hardware I2C Clock |
| | **SDA** | **GPIO 21** | Hardware I2C Data |
| **RC522 RFID** | **VCC / 3.3V** | **3V3** | **Must be 3.3V** (Do NOT use 5V) |
| | **RST** | **GPIO 4** | Reset Pin (Moved from 22 to free I2C SCL) |
| | **GND** | **GND** | Ground rail |
| | **IRQ** | *Unconnected* | Leave floating / not connected |
| | **MISO** | **GPIO 19** | Hardware VSPI MISO |
| | **MOSI** | **GPIO 23** | Hardware VSPI MOSI |
| | **SCK** | **GPIO 18** | Hardware VSPI Clock |
| | **SDA / SS** | **GPIO 5** | Hardware VSPI Chip Select (CS) |
| **3-Pin Buzzer** | **VCC** | **VIN (5V)** | Connect to VIN (5V) for loud volume (or 3V3 if quiet) |
| | **GND** | **GND** | Ground rail |
| | **I/O (SIG/IN)**| **GPIO 27** | Buzzer trigger signal |
| **Green LED** | **Anode (+ long)** | **GPIO 25** | Via 220Ω - 330Ω current-limiting resistor |
| | **Cathode (- short)** | **GND** | Ground rail |
| **Red LED** | **Anode (+ long)** | **GPIO 26** | Via 220Ω - 330Ω current-limiting resistor |
| | **Cathode (- short)** | **GND** | Ground rail |
| **Decoupling Capacitor** | **Positive (+ long)** | **3V3 Rail** | 10µF - 100µF across 3.3V power line |
| | **Negative (- stripe)**| **GND Rail** | Prevents Wi-Fi/RFID brownouts |

---

## 2. Visual Breadboard Schematic Diagram

```
         +--------------------------------------------+
         |               ESP32 (38-PIN)               |
         |                                            |
         |  [3V3] ----> (+) Breadboard Power Rail     |
         |  [GND] ----> (-) Breadboard Ground Rail    |
         |                                            |
         |  [GPIO 21] ------------------------------------> OLED SDA
         |  [GPIO 22] ------------------------------------> OLED SCK / SCL
         |                                            |
         |  [GPIO 5]  ------------------------------------> RC522 SDA (SS)
         |  [GPIO 18] ------------------------------------> RC522 SCK
         |  [GPIO 19] ------------------------------------> RC522 MISO
         |  [GPIO 23] ------------------------------------> RC522 MOSI
         |  [GPIO 4]  ------------------------------------> RC522 RST
         |                                            |
         |  [GPIO 27] ------------------------------------> Buzzer I/O (SIG)
         |  [GPIO 25] --(220Ω)----------------------------> Green LED (+)
         |  [GPIO 26] --(220Ω)----------------------------> Red LED (+)
         +--------------------------------------------+

    BREADBOARD RAILS:
    (+) 3V3 Rail : ESP32 3V3 + Capacitor(+) + RC522 VCC + OLED VDD + Buzzer VCC
    (-) GND Rail : ESP32 GND + Capacitor(-) + RC522 GND + OLED GND + Buzzer GND + LEDs(-)
```

---

## 3. Resistors & Peripherals Setup

1. **LEDs**:
   - Always wire a **220Ω or 330Ω resistor** in series with each LED (between the GPIO pin and the LED's longer positive lead) to protect both the ESP32 GPIO pin and the LED.
2. **Buzzer**:
   - A small **3.3V active buzzer module** can use GPIO 27 if its input current is within the ESP32 GPIO rating. Many bare buzzers draw too much current: use an NPN transistor/MOSFET driver and suitable resistor for those. Never power a 5V buzzer from an ESP32 GPIO.
   - If using a passive buzzer, digital writes only click; use PWM/tone output for an audible tone.

---

## 4. Arduino IDE Upload Instructions

1. **Install ESP32 Board Support**:
   - Open **Arduino IDE** -> `File` -> `Preferences`.
   - Add this URL to *Additional Boards Manager URLs*:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to `Tools` -> `Board` -> `Boards Manager`, search for **esp32** by Espressif Systems and click **Install**.

2. **Install Required Libraries**:
   - Go to `Sketch` -> `Include Library` -> `Manage Libraries...`
   - Search for **MFRC522** (by GithubCommunity / Miguel Balboa) and install.
   - Search for **ArduinoJson** (by Benoit Blanchon, version 6 or 7) and install.

3. **Configure Sketch**:
   - Open `firmware/esp32_rfid_attendance/esp32_rfid_attendance.ino`.
   - Update `WIFI_SSID` and `WIFI_PASSWORD` with your 2.4GHz Wi-Fi network credentials.
   - `SERVER_URL` is currently set to this computer's LAN address: `http://192.168.0.104:8000/api/scan`. If the computer reconnects to a different network or gets a new IP, update it to the address printed by `python backend\run.py`.

4. **Flash**:
   - Select your board (`Tools` -> `Board` -> `ESP32 Dev Module`).
   - Select your COM Port (`Tools` -> `Port`).
   - Click **Upload**. (If the board gets stuck at "Connecting...", press and hold the **BOOT** button on the ESP32 until the upload starts).

---

## 5. Troubleshooting Checklist

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `Firmware Version: 0x0` or `0xFF` in Serial Monitor | Loose SPI wiring or incorrect pins | Check MISO, MOSI, SCK, SDA wiring. Verify soldered header pins on RC522. |
| ESP32 cannot connect to Wi-Fi | 5GHz Wi-Fi network selected | ESP32 only supports **2.4 GHz** Wi-Fi networks. |
| HTTP POST fails with code `-1` | Firewall blocking port 8000 or wrong IP | Check PC's local IP address and allow incoming connections on port 8000 in Windows Defender Firewall. |
| Card reads repeatedly | Card held too long on antenna | Debounce is set to 2.5s; lift card after tap. |
