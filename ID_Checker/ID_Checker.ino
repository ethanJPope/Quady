#include <SCServo.h>

#define SERVO_TX 17
#define SERVO_RX 18

SMS_STS st;

bool pingWithRetries(int id) {
  for (int attempt = 0; attempt < 3; attempt++) {
    int result = st.Ping(id);
    if (result != -1) return true;
    delay(120);
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("Quady servo ID checker");

  Serial1.begin(1000000, SERIAL_8N1, SERVO_RX, SERVO_TX);
  st.pSerial = &Serial1;
  delay(500);
}

void loop() {
  int count = 0;

  for (int id = 1; id <= 12; id++) {
    Serial.print("ID ");
    Serial.print(id