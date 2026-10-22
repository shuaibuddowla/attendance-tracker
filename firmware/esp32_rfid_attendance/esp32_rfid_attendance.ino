#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ==========================================
// 1. NETWORK & CLOUD CONFIGURATION
// ==========================================
// 2.4 GHz Wi-Fi Credentials
// Replace with your local 2.4 GHz Wi-Fi network SSID and password
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ClassMate Attendance API Endpoint (Supports both LAN HTTP and Cloud HTTPS)
// 1. Direct ClassMate Cloud Integration: "https://<your-classmate-app>.vercel.app/api/scan"
// 2. Local Standalone FastAPI Dashboard: "http://<YOUR_LOCAL_PC_IP>:8000/api/scan"
const char* SERVER_URL    = "https://classmatebd.vercel.app/api/scan";
const char* DEVICE_ID     = "ESP32-READER-01";

// ==========================================
// 2. PIN DEFINITIONS (ESP32 38-Pin Layout)
// ==========================================
// RC522 SPI Pins:
// SDA (SS) -> GPIO 5
// SCK      -> GPIO 18
// MOSI     -> GPIO 23
// MISO     -> GPIO 19
// RST      -> GPIO 4   (GPIO 22 is used for OLED I2C SCL)
// 3.3V     -> 3V3
// GND      -> GND
#define SS_PIN    5
#define RST_PIN   4

// I2C OLED Display (0.96 inch SSD1306 128x64):
// SDA      -> GPIO 21
// SCK      -> GPIO 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Feedback Peripherals:
// Buzzer Signal -> GPIO 27 (Buzzer VCC must be connected to VIN 5V for maximum volume!)
// Green LED     -> GPIO 25 (via 220 ohm resistor)
// Red LED       -> GPIO 26 (via 220 ohm resistor)
#define PIN_BUZZER    27
#define PIN_LED_GREEN 25
#define PIN_LED_RED   26

// Audio Tone Mode:
#define BUZZER_USE_TONE true

// ==========================================
// 3. OBJECTS & STATE VARIABLES
// ==========================================
MFRC522 rfid(SS_PIN, RST_PIN);

String lastUid = "";
unsigned long lastScanTime = 0;
const unsigned long COOLDOWN_MS = 2000;

// Screen Modes
enum ScreenMode {
  SCREEN_SLEEP,
  SCREEN_IDLE,
  SCREEN_COURSE_ACTIVE,
  SCREEN_CARD_READ,
  SCREEN_RESULT
};

ScreenMode currentScreenMode = SCREEN_IDLE;
bool isDeviceSleeping = false;
bool screenNeedsRedraw = true;
unsigned long screenStateUntil = 0;
unsigned long lastHeartbeatTime = 0;
unsigned long lastMarqueeTime = 0;
int marqueeX = 128;

String activeCourseCode  = "CSE 2105";
String activeCourseTitle = "ClassMate Attendance Station";

// ==========================================
// 4. AUDIO HELPERS
// ==========================================
void soundBeep(int freq, int durationMs) {
#if BUZZER_USE_TONE
  tone(PIN_BUZZER, freq, durationMs);
  delay(durationMs);
  noTone(PIN_BUZZER);
#else
  digitalWrite(PIN_BUZZER, HIGH);
  delay(durationMs);
  digitalWrite(PIN_BUZZER, LOW);
#endif
}

// Instant tap chime upon card touch
void soundInstantTap() {
  soundBeep(2700, 80);
}

// Crisp 2-tone chime when validated as PRESENT
void soundPresentChime() {
  soundBeep(2600, 70);
  delay(30);
  soundBeep(3300, 110);
}

// Warning beeps for unregistered or wrong-batch cards
void soundWarningBeeps() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_LED_RED, HIGH);
    soundBeep(850, 100);
    digitalWrite(PIN_LED_RED, LOW);
    delay(60);
  }
}

// ==========================================
// 5. DISPLAY ENGINE & ANIMATIONS
// ==========================================

// Base Idle Screen (When no specific course session is active, but station is awake)
void drawBaseIdleScreen() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);

  // Top header status bar
  display.setTextSize(1);
  display.setCursor(14, 2);
  display.print("CLASSMATE STATION");
  display.drawLine(0, 12, 127, 12, SSD1306_WHITE);

  // Center RFID Card Graphic
  display.drawRoundRect(36, 17, 56, 30, 4, SSD1306_WHITE);
  display.drawCircle(46, 32, 4, SSD1306_WHITE); // Chip circle
  display.drawLine(56, 26, 82, 26, SSD1306_WHITE);
  display.drawLine(56, 32, 82, 32, SSD1306_WHITE);
  display.drawLine(56, 38, 74, 38, SSD1306_WHITE);

  // Bottom prompt bar
  display.drawLine(0, 50, 127, 50, SSD1306_WHITE);
  display.setCursor(16, 54);
  display.print("WAITING FOR SESSION");

  display.display();
}

// Active Course Screen: Big Course Code + Smooth Marquee Ticker for Subject Name
void drawActiveCourseScreen() {
  display.clearDisplay();
  display.setTextWrap(false);
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);

  // Top Line: Course Code in large bold font (TextSize 2)
  display.setTextSize(2);
  int codeX = (128 - (activeCourseCode.length() * 12)) / 2;
  if (codeX < 0) codeX = 0;
  display.setCursor(codeX, 4);
  display.print(activeCourseCode);

  display.drawLine(0, 23, 127, 23, SSD1306_WHITE);

  // Center Line: Smooth Scrolling Marquee for Course Title
  display.setTextSize(1);
  display.setCursor(marqueeX, 31);
  display.print(activeCourseTitle);

  display.drawLine(0, 47, 127, 47, SSD1306_WHITE);

  // Bottom Line: Instruction prompt
  display.setTextSize(1);
  display.setCursor(16, 52);
  display.print(">> TAP ID CARD <<");

  display.display();

  // Advance marquee ticker
  int titleWidth = activeCourseTitle.length() * 6;
  marqueeX -= 3;
  if (marqueeX < -(titleWidth + 12)) {
    marqueeX = 128;
  }
}

// Step 1: Instantly show ONLY Student ID in prominent text
void showOnlyStudentId(const char* idNum) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);

  // Top Label
  display.setTextSize(1);
  display.setCursor(32, 6);
  display.print("STUDENT ID");
  display.drawLine(14, 18, 114, 18, SSD1306_WHITE);

  // Big Centered Student Roll Number
  String idStr = String(idNum);
  display.setTextSize(2);
  int xPos = (128 - (idStr.length() * 12)) / 2;
  if (xPos < 2) xPos = 2;
  display.setCursor(xPos, 32);
  display.print(idStr);

  display.display();
}

// Step 2: Instantly transition to Present Checkmark Tick Animation
void showCheckmarkTickAnimation() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Rounded outer frame
  display.drawRoundRect(10, 6, 108, 52, 6, SSD1306_WHITE);

  // Big filled checkmark circle
  display.fillCircle(36, 32, 16, SSD1306_WHITE);

  // Black checkmark lines inside the white circle
  display.drawLine(27, 32, 33, 38, SSD1306_BLACK);
  display.drawLine(27, 33, 33, 39, SSD1306_BLACK);
  display.drawLine(28, 33, 34, 39, SSD1306_BLACK);

  display.drawLine(33, 38, 45, 25, SSD1306_BLACK);
  display.drawLine(33, 39, 45, 26, SSD1306_BLACK);
  display.drawLine(34, 39, 46, 26, SSD1306_BLACK);

  // "PRESENT" text beside the checkmark
  display.setTextSize(2);
  display.setCursor(58, 20);
  display.print("OK!");

  display.setTextSize(1);
  display.setCursor(58, 40);
  display.print("PRESENT");

  display.display();
}

// Unregistered or Wrong Batch Screen
void showWarningScreen(const char* title, const char* subtitle, String uid) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);

  display.setTextSize(1);
  display.setCursor(18, 2);
  display.println(title);
  display.drawLine(0, 12, 127, 12, SSD1306_WHITE);

  display.setCursor(2, 18);
  display.print("UID: ");
  display.println(uid);

  display.setCursor(2, 30);
  display.println(subtitle);

  display.drawLine(0, 44, 127, 44, SSD1306_WHITE);
  display.setCursor(2, 50);
  display.println("Check Admin Portal");

  display.display();
}

// ==========================================
// 6. CLOUD / SERVER COMMUNICATION
// ==========================================

// Fast Idle Heartbeat: Checks if Admin started or closed an attendance session
void checkDeviceHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  WiFiClientSecure secClient;
  WiFiClient plainClient;

  String url = String(SERVER_URL) + "?device_id=" + String(DEVICE_ID);

  if (url.startsWith("https://")) {
    secClient.setInsecure();
    http.begin(secClient, url);
  } else {
    http.begin(plainClient, url);
  }
  http.setTimeout(2500);

  int httpCode = http.GET();
  if (httpCode == 200) {
    String resString = http.getString();
    StaticJsonDocument<384> doc;
    DeserializationError err = deserializeJson(doc, resString);
    if (!err) {
      const char* status = doc["status"] | "SLEEP";
      if (strcmp(status, "ACTIVE") == 0) {
        const char* code  = doc["course_code"] | "ATTENDANCE";
        const char* title = doc["course_title"] | "ClassMate Live Session";

        bool wasSleeping = isDeviceSleeping;
        isDeviceSleeping = false;

        if (wasSleeping) {
          display.ssd1306_command(SSD1306_DISPLAYON);
        }

        if (activeCourseCode != code || activeCourseTitle != title) {
          activeCourseCode  = String(code);
          activeCourseTitle = String(title);
          marqueeX = 128;
        }

        currentScreenMode = SCREEN_COURSE_ACTIVE;
      } else {
        // Status is SLEEP -> Turn off OLED and LEDs
        if (!isDeviceSleeping) {
          isDeviceSleeping = true;
          currentScreenMode = SCREEN_SLEEP;
          display.clearDisplay();
          display.display();
          display.ssd1306_command(SSD1306_DISPLAYOFF);
          digitalWrite(PIN_LED_GREEN, LOW);
          digitalWrite(PIN_LED_RED, LOW);
        }
      }
    }
  }
  http.end();
}

// POST Card Tap to ClassMate Server
void postAttendance(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] Wi-Fi disconnected.");
    showWarningScreen("OFFLINE ERROR", "WiFi Disconnected", uid);
    soundWarningBeeps();
    delay(1500);
    currentScreenMode = SCREEN_COURSE_ACTIVE;
    marqueeX = 128;
    return;
  }

  HTTPClient http;
  WiFiClientSecure secClient;
  WiFiClient plainClient;

  if (strncmp(SERVER_URL, "https://", 8) == 0) {
    secClient.setInsecure();
    http.begin(secClient, SERVER_URL);
  } else {
    http.begin(plainClient, SERVER_URL);
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);

  StaticJsonDocument<256> reqDoc;
  reqDoc["card_uid"]  = uid;
  reqDoc["device_id"] = DEVICE_ID;
  String reqJson;
  serializeJson(reqDoc, reqJson);

  Serial.print("-> Sending Scan POST: ");
  Serial.println(reqJson);

  int httpCode = http.POST(reqJson);

  if (httpCode > 0) {
    String resString = http.getString();
    Serial.printf("-> Server HTTP %d: %s\n", httpCode, resString.c_str());

    StaticJsonDocument<512> resDoc;
    DeserializationError err = deserializeJson(resDoc, resString);

    if (!err) {
      const char* status = resDoc["status"] | "UNKNOWN";
      const char* idNum  = resDoc["identifier"] | uid.c_str();

      if (strcmp(status, "CHECK_IN") == 0 || strcmp(status, "CHECK_OUT") == 0 || strcmp(status, "COOLDOWN") == 0) {
        // 1. Instantly show ONLY Student ID
        showOnlyStudentId(idNum);
        delay(380);

        // 2. Instantly disappear ID and show PRESENT tick animation with chime
        digitalWrite(PIN_LED_GREEN, HIGH);
        showCheckmarkTickAnimation();
        soundPresentChime();
        delay(800);
        digitalWrite(PIN_LED_GREEN, LOW);

        // 3. Immediately restore Course Name & Code screen
        currentScreenMode = SCREEN_COURSE_ACTIVE;
        marqueeX = 128;
      } else if (strcmp(status, "WRONG_BATCH") == 0) {
        showWarningScreen("WRONG BATCH", "Student from other batch", uid);
        soundWarningBeeps();
        delay(1200);
        currentScreenMode = SCREEN_COURSE_ACTIVE;
        marqueeX = 128;
      } else {
        // UNREGISTERED or other status
        showWarningScreen("NOT REGISTERED", "Card UID Unknown", uid);
        soundWarningBeeps();
        delay(1200);
        currentScreenMode = SCREEN_COURSE_ACTIVE;
        marqueeX = 128;
      }
    } else {
      showWarningScreen("PARSE ERROR", "Invalid JSON from server", uid);
      soundWarningBeeps();
      delay(1200);
      currentScreenMode = SCREEN_COURSE_ACTIVE;
      marqueeX = 128;
    }
  } else {
    Serial.printf("[ERROR] HTTP failed: %s\n", http.errorToString(httpCode).c_str());
    showWarningScreen("NETWORK ERROR", "Server unreachable", uid);
    soundWarningBeeps();
    delay(1200);
    currentScreenMode = SCREEN_COURSE_ACTIVE;
    marqueeX = 128;
  }

  http.end();
}

// ==========================================
// 7. SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n==========================================");
  Serial.println("  ESP32 CLOUD ATTENDANCE STATION - READY");
  Serial.println("==========================================");

  // Initialize feedback pins
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);

  // Hardware self-test chirp
  digitalWrite(PIN_LED_GREEN, HIGH);
  digitalWrite(PIN_LED_RED, HIGH);
  soundBeep(2700, 100);
  delay(300);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);

  // Initialize I2C with Fast 400kHz Clock (Snappy display refresh)
  Wire.begin(21, 22);
  Wire.setClock(400000);

  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("[OK] OLED Display Initialized (0x3C).");
  } else if (display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
    Serial.println("[OK] OLED Display Initialized (0x3D).");
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE, SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(18, 16);
  display.println("CLASSMATE STATION");
  display.drawLine(10, 28, 117, 28, SSD1306_WHITE);
  display.setCursor(18, 38);
  display.println("Connecting WiFi...");
  display.display();

  // Initialize SPI and RC522 Reader
  SPI.begin();
  rfid.PCD_Init();
  delay(50);
  byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[RFID] VersionReg: 0x%02X\n", version);
  if (version == 0x00 || version == 0xFF) {
    Serial.println("[ERROR] RC522 is NOT communicating over SPI!");
    Serial.println("-> Check connections: SS=GPIO 5, SCK=GPIO 18, MOSI=GPIO 23, MISO=GPIO 19, RST=GPIO 4, 3V3, GND.");
  } else {
    Serial.println("[OK] RC522 Reader Initialized and Ready for Cards.");
  }

  // Wi-Fi Connection
  Serial.printf("-> Connecting to Wi-Fi '%s'...", WIFI_SSID);
  WiFi.disconnect(true);
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[OK] Wi-Fi Connected!");
    Serial.print("-> ESP32 IP: ");
    Serial.println(WiFi.localIP());
    soundInstantTap();
  } else {
    Serial.println("\n[WARN] Wi-Fi initial connection timed out. Will auto-reconnect.");
  }

  // Initial state check
  checkDeviceHeartbeat();
}

// ==========================================
// 8. MAIN LOOP
// ==========================================
void loop() {
  unsigned long now = millis();

  // Auto-reconnect Wi-Fi if dropped (Throttled every 10s to prevent spamming the ESP-IDF driver)
  static unsigned long lastWifiRetry = 0;
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiRetry > 10000) {
      lastWifiRetry = now;
      Serial.printf("\n[WIFI] Not connected. Retrying '%s'...\n", WIFI_SSID);
      WiFi.disconnect();
      WiFi.reconnect();
    }
  }

  // Fast Heartbeat polling every 2000ms
  if (currentScreenMode != SCREEN_CARD_READ && (now - lastHeartbeatTime > 2000)) {
    lastHeartbeatTime = now;
    checkDeviceHeartbeat();
  }

  // Screen Rendering
  if (currentScreenMode == SCREEN_SLEEP) {
    // Device is sleeping; OLED is OFF.
    delay(20);
  } else if (currentScreenMode == SCREEN_COURSE_ACTIVE) {
    // Animate Marquee Ticker every 35ms
    if (now - lastMarqueeTime > 35) {
      lastMarqueeTime = now;
      drawActiveCourseScreen();
    }
  } else if (currentScreenMode == SCREEN_IDLE) {
    if (screenNeedsRedraw) {
      drawBaseIdleScreen();
      screenNeedsRedraw = false;
    }
  }

  // Check for RFID card presence
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Wake display if station was sleeping
  if (isDeviceSleeping) {
    isDeviceSleeping = false;
    display.ssd1306_command(SSD1306_DISPLAYON);
    currentScreenMode = SCREEN_IDLE;
  }

  // Convert UID to clean uppercase hex string (e.g. "03E1AA05") and space-separated bytes
  String cardUid = "";
  String cardUidFormatted = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      cardUid += "0";
      cardUidFormatted += "0";
    }
    cardUid += String(rfid.uid.uidByte[i], HEX);
    cardUidFormatted += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) cardUidFormatted += " ";
  }
  cardUid.toUpperCase();
  cardUidFormatted.toUpperCase();

  // Print Card UID immediately to Serial Monitor
  Serial.println("\n==========================================");
  Serial.printf(">>> CARD TAPPED! UID: %s  [%s] <<<\n", cardUid.c_str(), cardUidFormatted.c_str());
  Serial.println("==========================================");

  // Debounce duplicate swipes within cooldown window
  if (cardUid == lastUid && (now - lastScanTime < COOLDOWN_MS)) {
    Serial.printf("[RFID] Cooldown active (%lums remaining). Duplicate tap ignored.\n", COOLDOWN_MS - (now - lastScanTime));
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return;
  }

  lastUid = cardUid;
  lastScanTime = now;

  // Instant Tap Feedback (Audible chirp + flash)
  digitalWrite(PIN_LED_GREEN, HIGH);
  soundInstantTap();
  delay(40);
  digitalWrite(PIN_LED_GREEN, LOW);

  // Mark state
  currentScreenMode = SCREEN_CARD_READ;

  // Post to ClassMate Server
  postAttendance(cardUid);

  // Complete RFID transaction
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}
