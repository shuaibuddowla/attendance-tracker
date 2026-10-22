/*
 * ESP32 SPI-pin loopback test. Disconnect the RC522 first.
 * Connect ESP32 GPIO23 (MOSI) directly to GPIO19 (MISO) with one jumper.
 * Open Serial Monitor at 115200 baud.
 */

#include <SPI.h>

constexpr int SCK_PIN = 18;
constexpr int MISO_PIN = 19;
constexpr int MOSI_PIN = 23;
constexpr int SS_PIN = 5;

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(SS_PIN, OUTPUT);
  digitalWrite(SS_PIN, HIGH);
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);

  const uint8_t patterns[] = {0x55, 0xAA, 0x00, 0xFF};
  bool passed = true;
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  for (uint8_t sent : patterns) {
    uint8_t received = SPI.transfer(sent);
    Serial.printf("sent 0x%02X, received 0x%02X %s\n",
                  sent, received, sent == received ? "PASS" : "FAIL");
    if (sent != received) passed = false;
  }
  SPI.endTransaction();

  Serial.println(passed
    ? "LOOPBACK PASS: ESP32 MOSI/SCK/MISO SPI path works."
    : "LOOPBACK FAIL: check GPIO labels, jumper, and ESP32 SPI pins.");
}

void loop() {}
