/*
 * Standalone ESP32 + RC522 check.
 * Wiring: SS/SDA=GPIO32, SCK=18, MOSI=23, MISO=19, RST=33, VCC=3V3, GND=GND.
 * Open Serial Monitor at 115200 baud. No Wi-Fi, LEDs, or buzzer are used.
 */

#include <SPI.h>
#include <MFRC522.h>

constexpr byte SS_PIN = 32;
constexpr byte RST_PIN = 33;

MFRC522 reader(SS_PIN, RST_PIN);
bool readerResponded = false;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\nRC522 standalone diagnostic");
  Serial.println("Expected wiring: SS=32 SCK=18 MOSI=23 MISO=19 RST=33 VCC=3V3 GND=GND");

  SPI.begin(18, 19, 23, SS_PIN);
  reader.PCD_Init();
  delay(50);

  byte version = reader.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("VersionReg = 0x%02X\n", version);

  if (version == 0x00 || version == 0xFF) {
    Serial.println("FAIL: ESP32 is not communicating with the RC522 over SPI.");
    Serial.println("Recheck power, GND, SS/SDA, SCK, MOSI, MISO, RST, and header soldering.");
  } else {
    Serial.println("PASS: RC522 responds over SPI. Tap a 13.56 MHz card or key fob.");
    readerResponded = true;
  }
}

void loop() {
  if (!readerResponded) {
    delay(1000);
    return;
  }

  if (!reader.PICC_IsNewCardPresent() || !reader.PICC_ReadCardSerial()) {
    delay(30);
    return;
  }

  Serial.print("CARD UID: ");
  for (byte i = 0; i < reader.uid.size; i++) {
    if (reader.uid.uidByte[i] < 0x10) Serial.print('0');
    Serial.print(reader.uid.uidByte[i], HEX);
  }
  Serial.println();
  reader.PICC_HaltA();
  reader.PCD_StopCrypto1();
}
