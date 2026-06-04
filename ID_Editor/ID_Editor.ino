#include <SCServo.h>

#define SERVO_TX 17
#define SERVO_RX 18

#define CURRENT_ID 1
#define NEW_ID 2

SMS_STS st;

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("Quady servo ID changer");

  Serial1.begin(1000000, SERIAL_8N1, SERVO_RX, SERVO_TX);
  st.pSerial = &Serial1;
  delay(500);

  int found = st.Ping(CURRENT_ID);
  if (found == -1) {
    Serial.println("Current ID not found. Stop and rescan.");
    return;
  }

  Serial.print("Changing ID ");
  Serial.print(CURRENT_ID);
  Serial.print(" -> ");
  Serial.println(NEW_ID);

  st.unLockEprom(CURRENT_ID);
  delay(50);

  st.writeByte(CURRENT_ID, SMS_STS_ID, NEW_ID);
  delay(100);

  st.LockEprom(NEW_ID);
  delay(100);

  int check = st.Ping(NEW_ID);
  if (check != -1) {
    Serial.print("Success. New ID: ");
    Serial.println(check);
  } else {
    Serial.println("Could not confirm new ID. Run scanner.");
  }
}

void loop() {}