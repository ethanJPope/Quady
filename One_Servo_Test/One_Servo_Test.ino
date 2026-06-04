#include <SCServo.h>

#define SERVO_TX 17
#define SERVO_RX 18
#define SERVO_ID 1

SMS_STS st;

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("Quady safe movement test");

  Serial1.begin(1000000, SERIAL_8N1, SERVO_RX, SERVO_TX);
  st.pSerial = &Serial1;
  delay(500);

  int found = st.Ping(SERVO_ID);
  if (found == -1) {
    Serial.println("Servo not found. Stop and check wiring/power.");
    return;
  }

  int pos = st.ReadPos(SERVO_ID);

  Serial.print("Current position: ");
  Serial.println(pos);

  if (pos == -1) {
    Serial.println("Could not read position. Stopping.");
    return;
  }

  int posA = constrain(pos - 100, 0, 4095);
  int posB = constrain(pos + 100, 0, 4095);

  Serial.print("Moving gently to: ");
  Serial.println(posA);
  st.WritePosEx(SERVO_ID, posA, 800, 50);
  delay(1500);

  Serial.print("Moving gently to: ");
  Serial.println(posB);
  st.WritePosEx(SERVO_ID, posB, 800, 50);
  delay(1500);

  Serial.print("Returning to start: ");
  Serial.println(pos);
  st.WritePosEx(SERVO_ID, pos, 800, 50);
  delay(1500);

  Serial.println("Movement test complete.");
}

void loop() {
  int pos = st.ReadPos(SERVO_ID);
  Serial.print("Position: ");
  Serial.println(pos);
  delay(1000);
}