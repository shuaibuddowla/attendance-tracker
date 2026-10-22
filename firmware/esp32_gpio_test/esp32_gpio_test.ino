/*
 * ESP32 GPIO32/GPIO33 jumper test for the RC522 diagnostic's SS and RST pins.
 * Disconnect other hardware. Connect GPIO32 directly to GPIO33 with one jumper.
 * Open Serial Monitor at 115200 baud.
 */

constexpr uint8_t PIN_A = 32;
constexpr uint8_t PIN_B = 33;

bool testDirection(uint8_t outputPin, uint8_t inputPin, const char *label) {
  pinMode(outputPin, OUTPUT);
  pinMode(inputPin, INPUT_PULLDOWN);
  bool passed = true;

  digitalWrite(outputPin, LOW);
  delay(10);
  bool lowOK = digitalRead(inputPin) == LOW;
  Serial.printf("%s LOW readback: %s\n", label, lowOK ? "PASS" : "FAIL");

  digitalWrite(outputPin, HIGH);
  delay(10);
  bool highOK = digitalRead(inputPin) == HIGH;
  Serial.printf("%s HIGH readback: %s\n", label, highOK ? "PASS" : "FAIL");

  digitalWrite(outputPin, LOW);
  pinMode(outputPin, INPUT);
  pinMode(inputPin, INPUT);
  return passed && lowOK && highOK;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 GPIO32/GPIO33 test");
  Serial.println("With GPIO32 jumpered to GPIO33, each direction should pass LOW and HIGH.");

  bool aToB = testDirection(PIN_A, PIN_B, "GPIO32 -> GPIO33");
  bool bToA = testDirection(PIN_B, PIN_A, "GPIO33 -> GPIO32");
  Serial.println(aToB && bToA ? "GPIO TEST PASS" : "GPIO TEST FAIL");
}

void loop() {}
