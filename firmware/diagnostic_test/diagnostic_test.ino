#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Pins
#define PIN_LED_GREEN 25
#define PIN_LED_RED   26
#define PIN_BUZZER    27
#define OLED_SDA      21
#define OLED_SCL      22

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n\n==========================================");
  Serial.println("  HARDWARE DIAGNOSTIC TEST (ESP32)");
  Serial.println("==========================================");

  // 1. Test Pins Setup
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  // 2. Test Buzzer
  Serial.println("-> Testing Buzzer...");
  digitalWrite(PIN_BUZZER, HIGH);
  delay(100);
  digitalWrite(PIN_BUZZER, LOW);

  // 3. I2C Scanner for OLED
  Serial.println("\n-> Scanning I2C bus on SDA=21, SCL=22...");
  Wire.begin(OLED_SDA, OLED_SCL);
  byte error, address;
  int nDevices = 0;
  byte foundAddress = 0;

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf("   [FOUND] I2C device at address 0x%02X\n", address);
      foundAddress = address;
      nDevices++;
    }
  }

  if (nDevices == 0) {
    Serial.println("   [ERROR] No I2C devices found!");
    Serial.println("   -> Check OLED VDD/GND power and SDA(21)/SCK(22) wiring.");
  } else {
    Serial.printf("   [OK] Found %d I2C device(s).\n", nDevices);
    
    // Try initializing OLED
    if (display.begin(SSD1306_SWITCHCAPVCC, foundAddress)) {
      Serial.println("   [OK] OLED display initialized successfully!");
      display.clearDisplay();
      display.setTextSize(2);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(10, 15);
      display.println("OLED OK!");
      display.setTextSize(1);
      display.setCursor(10, 42);
      display.printf("Addr: 0x%02X", foundAddress);
      display.display();
    } else {
      Serial.println("   [ERROR] display.begin() failed for found address.");
    }
  }

  Serial.println("\n-> Starting LED alternating blink loop...");
}

void loop() {
  // Blink Green
  Serial.println("LED: Green ON, Red OFF");
  digitalWrite(PIN_LED_GREEN, HIGH);
  digitalWrite(PIN_LED_RED, LOW);
  delay(1000);

  // Blink Red
  Serial.println("LED: Green OFF, Red ON");
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, HIGH);
  delay(1000);
}
