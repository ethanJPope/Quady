#include <Preferences.h>
#include <SCServo.h>
#include <math.h>

#define BUS1_TX 9
#define BUS1_RX 10

#define BUS2_TX 11
#define BUS2_RX 12

static const int SERVO_COUNT = 8;
static const int POS_MODULO = 4096;
static const int DEFAULT_SPEED = 800;
static const int DEFAULT_ACC = 50;
static const float DEFAULT_TEST_BUFFER_PERCENT = 10.0f;
static const int DEFAULT_TEST_CYCLES = 1;
static const unsigned long TEST_DWELL_MS = 1200;

HardwareSerial ServoBus1(1);
HardwareSerial ServoBus2(2);

SMS_STS st;
Preferences prefs;

struct ServoCal {
  uint16_t stopA;
  uint16_t stopB;
  uint8_t valid;
};

struct LearnState {
  bool active;
  int origin;
  int minDelta;
  int maxDelta;
};

ServoCal cal[SERVO_COUNT];
LearnState learn[SERVO_COUNT];
String commandLine;
unsigned long lastPrintMs = 0;
unsigned long lastAutoSaveMs = 0;
bool autoRangeDirty = false;

static bool validId(int id) {
  return id >= 1 && id <= SERVO_COUNT;
}

static void selectBus(int id) {
  st.pSerial = (id <= 4) ? &ServoBus1 : &ServoBus2;
}

static int wrapPos(int pos) {
  pos %= POS_MODULO;
  if (pos < 0) {
    pos += POS_MODULO;
  }
  return pos;
}

static int cwDistance(int from, int to) {
  return wrapPos(to - from);
}

static int signedShortestDelta(int from, int to) {
  int delta = cwDistance(from, to);
  if (delta > POS_MODULO / 2) {
    delta -= POS_MODULO;
  }
  return delta;
}

static int calibratedSpan(int id) {
  ServoCal &c = cal[id - 1];
  if (!c.valid) {
    return 0;
  }

  return abs(signedShortestDelta(c.stopA, c.stopB));
}

static int posFromStops(int stopA, int stopB, float percent) {
  int delta = signedShortestDelta(stopA, stopB);
  percent = constrain(percent, 0.0f, 100.0f);
  return wrapPos(stopA + lroundf(delta * (percent / 100.0f)));
}

static int posFromPercent(int id, float percent) {
  ServoCal &c = cal[id - 1];
  return posFromStops(c.stopA, c.stopB, percent);
}

static float percentFromStops(int stopA, int stopB, int pos, bool *outside) {
  int delta = signedShortestDelta(stopA, stopB);
  int span = abs(delta);

  if (span == 0) {
    if (outside) {
      *outside = true;
    }
    return NAN;
  }

  int fromA = (delta >= 0) ? cwDistance(stopA, pos) : cwDistance(pos, stopA);
  if (outside) {
    *outside = fromA > span;
  }

  fromA = constrain(fromA, 0, span);
  return 100.0f * fromA / span;
}

static float percentFromPos(int id, int pos, bool *outside) {
  ServoCal &c = cal[id - 1];
  if (!c.valid) {
    if (outside) {
      *outside = true;
    }
    return NAN;
  }

  return percentFromStops(c.stopA, c.stopB, pos, outside);
}

static void saveCal() {
  prefs.putBytes("servoCal", cal, sizeof(cal));
}

static void loadCal() {
  memset(cal, 0, sizeof(cal));

  if (prefs.getBytesLength("servoCal") == sizeof(cal)) {
    prefs.getBytes("servoCal", cal, sizeof(cal));
  }
}

static int readServoPos(int id) {
  selectBus(id);
  return st.ReadPos(id);
}

static void moveServoRaw(int id, int pos) {
  selectBus(id);
  st.WritePosEx(id, wrapPos(pos), DEFAULT_SPEED, DEFAULT_ACC);
}

static void initAutoRange(int id, int pos) {
  LearnState &l = learn[id - 1];
  ServoCal &c = cal[id - 1];
  l.active = true;

  if (c.valid) {
    int delta = signedShortestDelta(c.stopA, c.stopB);
    l.origin = c.stopA;
    l.minDelta = min(0, delta);
    l.maxDelta = max(0, delta);
  } else {
    l.origin = pos;
    l.minDelta = 0;
    l.maxDelta = 0;
  }
}

static bool updateAutoRange(int id, int pos) {
  LearnState &l = learn[id - 1];
  if (pos < 0) {
    return false;
  }

  if (!l.active) {
    initAutoRange(id, pos);
  }

  int oldMin = l.minDelta;
  int oldMax = l.maxDelta;
  int delta = signedShortestDelta(l.origin, pos);

  l.minDelta = min(l.minDelta, delta);
  l.maxDelta = max(l.maxDelta, delta);

  if (l.minDelta == oldMin && l.maxDelta == oldMax) {
    return false;
  }

  int span = l.maxDelta - l.minDelta;
  if (span <= 0) {
    return false;
  }

  cal[id - 1].stopA = wrapPos(l.origin + l.minDelta);
  cal[id - 1].stopB = wrapPos(l.origin + l.maxDelta);
  cal[id - 1].valid = 1;
  autoRangeDirty = true;
  return true;
}

static void maybeSaveAutoRange() {
  if (!autoRangeDirty || millis() - lastAutoSaveMs < 2000) {
    return;
  }

  saveCal();
  autoRangeDirty = false;
  lastAutoSaveMs = millis();
  Serial.println("Auto-saved expanded servo ranges.");
}

static void printHelp() {
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  help                 Show this help");
  Serial.println("  list                 Show saved auto-range values");
  Serial.println("  mark <id> a|b        Save current position as one end stop");
  Serial.println("  clear <id|all>       Clear saved calibration");
  Serial.println("  goto <id> <0-100>    Move within calibrated range");
  Serial.println("  nudge <id> <ticks>   Move relative to current raw position, wrap-aware");
  Serial.println("  test <id|all> [bufferPercent] [cycles]");
  Serial.println("                       Sweep one servo at a time inside saved range");
  Serial.println();
  Serial.println("Ranges auto-expand as you move each servo to new farthest positions.");
  Serial.println();
}

static void printCalList() {
  Serial.println("ID\tA\tB\tSPAN\tVALID");
  for (int id = 1; id <= SERVO_COUNT; id++) {
    Serial.print(id);
    Serial.print('\t');
    Serial.print(cal[id - 1].stopA);
    Serial.print('\t');
    Serial.print(cal[id - 1].stopB);
    Serial.print('\t');
    Serial.print(calibratedSpan(id));
    Serial.print('\t');
    Serial.println(cal[id - 1].valid ? "yes" : "no");
  }
}

static void handleMark(char *args) {
  if (!args) {
    Serial.println("Use: mark <id> a|b");
    return;
  }

  char *idText = strtok(args, " ");
  char *whichText = strtok(nullptr, " ");
  int id = idText ? atoi(idText) : 0;

  if (!validId(id) || !whichText || (whichText[0] != 'a' && whichText[0] != 'b')) {
    Serial.println("Use: mark <id> a|b");
    return;
  }

  int pos = readServoPos(id);
  if (pos < 0) {
    Serial.println("Read failed; calibration not changed.");
    return;
  }

  if (whichText[0] == 'a') {
    cal[id - 1].stopA = pos;
  } else {
    cal[id - 1].stopB = pos;
  }

  if (cal[id - 1].stopA != cal[id - 1].stopB) {
    cal[id - 1].valid = 1;
  }

  learn[id - 1].active = false;
  saveCal();
  Serial.print("Saved servo ");
  Serial.print(id);
  Serial.print(" stop ");
  Serial.print(whichText[0]);
  Serial.print(" = ");
  Serial.println(pos);
  printCalList();
}

static void handleClear(char *args) {
  if (!args) {
    Serial.println("Use: clear <id|all>");
    return;
  }

  char *target = strtok(args, " ");
  if (!target) {
    Serial.println("Use: clear <id|all>");
    return;
  }

  if (strcmp(target, "all") == 0) {
    memset(cal, 0, sizeof(cal));
    memset(learn, 0, sizeof(learn));
  } else {
    int id = atoi(target);
    if (!validId(id)) {
      Serial.println("Use: clear <id|all>");
      return;
    }
    memset(&cal[id - 1], 0, sizeof(ServoCal));
    memset(&learn[id - 1], 0, sizeof(LearnState));
  }

  saveCal();
  autoRangeDirty = false;
  Serial.println("Calibration cleared.");
}

static void handleGoto(char *args) {
  if (!args) {
    Serial.println("Use: goto <id> <0-100>");
    return;
  }

  char *idText = strtok(args, " ");
  char *pctText = strtok(nullptr, " ");
  int id = idText ? atoi(idText) : 0;

  if (!validId(id) || !pctText) {
    Serial.println("Use: goto <id> <0-100>");
    return;
  }

  if (!cal[id - 1].valid) {
    Serial.println("Servo is not calibrated yet.");
    return;
  }

  float percent = atof(pctText);
  int target = posFromPercent(id, percent);
  moveServoRaw(id, target);

  Serial.print("Servo ");
  Serial.print(id);
  Serial.print(" -> ");
  Serial.print(constrain(percent, 0.0f, 100.0f), 1);
  Serial.print("% raw=");
  Serial.println(target);
}

static void handleNudge(char *args) {
  if (!args) {
    Serial.println("Use: nudge <id> <ticks>");
    return;
  }

  char *idText = strtok(args, " ");
  char *ticksText = strtok(nullptr, " ");
  int id = idText ? atoi(idText) : 0;

  if (!validId(id) || !ticksText) {
    Serial.println("Use: nudge <id> <ticks>");
    return;
  }

  int pos = readServoPos(id);
  if (pos < 0) {
    Serial.println("Read failed; nudge skipped.");
    return;
  }

  int target = wrapPos(pos + atoi(ticksText));
  moveServoRaw(id, target);

  Serial.print("Servo ");
  Serial.print(id);
  Serial.print(" nudged to raw=");
  Serial.println(target);
}

static void moveServoPercent(int id, float percent, const char *label) {
  int target = posFromPercent(id, percent);
  moveServoRaw(id, target);

  Serial.print("Servo ");
  Serial.print(id);
  Serial.print(' ');
  Serial.print(label);
  Serial.print(" -> ");
  Serial.print(percent, 1);
  Serial.print("% raw=");
  Serial.println(target);
  delay(TEST_DWELL_MS);
}

static bool runServoTest(int id, float bufferPercent, int cycles) {
  if (!cal[id - 1].valid || calibratedSpan(id) <= 0) {
    Serial.print("Servo ");
    Serial.print(id);
    Serial.println(" skipped: no saved range.");
    return false;
  }

  float lowPercent = bufferPercent;
  float highPercent = 100.0f - bufferPercent;

  Serial.print("Testing servo ");
  Serial.print(id);
  Serial.print(" between ");
  Serial.print(lowPercent, 1);
  Serial.print("% and ");
  Serial.print(highPercent, 1);
  Serial.print("%, span=");
  Serial.println(calibratedSpan(id));

  for (int cycle = 1; cycle <= cycles; cycle++) {
    Serial.print("Cycle ");
    Serial.print(cycle);
    Serial.print('/');
    Serial.println(cycles);

    moveServoPercent(id, lowPercent, "low");
    moveServoPercent(id, highPercent, "high");
  }

  moveServoPercent(id, 50.0f, "center");
  return true;
}

static void handleTest(char *args) {
  if (!args) {
    Serial.println("Use: test <id|all> [bufferPercent] [cycles]");
    return;
  }

  char *targetText = strtok(args, " ");
  char *bufferText = strtok(nullptr, " ");
  char *cyclesText = strtok(nullptr, " ");

  if (!targetText) {
    Serial.println("Use: test <id|all> [bufferPercent] [cycles]");
    return;
  }

  float bufferPercent = bufferText ? atof(bufferText) : DEFAULT_TEST_BUFFER_PERCENT;
  int cycles = cyclesText ? atoi(cyclesText) : DEFAULT_TEST_CYCLES;

  bufferPercent = constrain(bufferPercent, 1.0f, 45.0f);
  cycles = constrain(cycles, 1, 10);

  Serial.print("Movement test: buffer=");
  Serial.print(bufferPercent, 1);
  Serial.print("% cycles=");
  Serial.println(cycles);

  if (strcmp(targetText, "all") == 0) {
    for (int id = 1; id <= SERVO_COUNT; id++) {
      runServoTest(id, bufferPercent, cycles);
    }
  } else {
    int id = atoi(targetText);
    if (!validId(id)) {
      Serial.println("Use: test <id|all> [bufferPercent] [cycles]");
      return;
    }
    runServoTest(id, bufferPercent, cycles);
  }

  Serial.println("Movement test complete.");
}

static void handleCommand(String line) {
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) {
    return;
  }

  char buffer[80];
  line.toCharArray(buffer, sizeof(buffer));
  char *cmd = buffer;
  char *args = strchr(buffer, ' ');
  if (args) {
    *args = '\0';
    args++;
    while (*args == ' ') {
      args++;
    }
    if (*args == '\0') {
      args = nullptr;
    }
  }

  if (strcmp(cmd, "help") == 0) {
    printHelp();
  } else if (strcmp(cmd, "list") == 0) {
    printCalList();
  } else if (strcmp(cmd, "mark") == 0) {
    handleMark(args);
  } else if (strcmp(cmd, "clear") == 0) {
    handleClear(args);
  } else if (strcmp(cmd, "goto") == 0) {
    handleGoto(args);
  } else if (strcmp(cmd, "nudge") == 0) {
    handleNudge(args);
  } else if (strcmp(cmd, "test") == 0) {
    handleTest(args);
  } else {
    Serial.println("Unknown command. Type: help");
  }
}

static void readSerialCommands() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      handleCommand(commandLine);
      commandLine = "";
    } else if (commandLine.length() < 79) {
      commandLine += ch;
    }
  }
}

static void printPositionBar(float percent, bool outside) {
  if (isnan(percent)) {
    Serial.print("----------");
    return;
  }

  int slot = constrain((int)lroundf(percent / 10.0f), 0, 10);
  for (int i = 0; i <= 10; i++) {
    Serial.print(i == slot ? '|' : '-');
  }

  if (outside) {
    Serial.print('!');
  }
}

static void printPositions() {
  Serial.println("ID\tRAW\tPCT\tSPAN\tRANGE");
  for (int id = 1; id <= SERVO_COUNT; id++) {
    int pos = readServoPos(id);
    bool expanded = updateAutoRange(id, pos);
    bool outside = false;
    float percent = percentFromPos(id, pos, &outside);

    Serial.print(id);
    Serial.print('\t');
    Serial.print(pos);
    Serial.print('\t');

    if (isnan(percent)) {
      Serial.print("n/a");
    } else {
      Serial.print(percent, 1);
      Serial.print('%');
    }

    Serial.print('\t');
    Serial.print(calibratedSpan(id));
    if (expanded) {
      Serial.print('*');
    }
    Serial.print('\t');
    printPositionBar(percent, outside);
    Serial.println();
  }
  maybeSaveAutoRange();
  Serial.println();
}

void setup() {
  Serial.begin(115200);

  ServoBus1.begin(1000000, SERIAL_8N1, BUS1_RX, BUS1_TX);
  ServoBus2.begin(1000000, SERIAL_8N1, BUS2_RX, BUS2_TX);

  prefs.begin("id-checker", false);
  loadCal();

  delay(1000);

  Serial.println("Servo range tool ready. Type: help");
  printCalList();
}

void loop() {
  readSerialCommands();

  if (millis() - lastPrintMs >= 250) {
    lastPrintMs = millis();
    printPositions();
  }
}
