#include <SCServo.h>

// Quadi final wiring (ESP32-S3-WROOM-1 -> Waveshare Bus Servo Adapter (A)).
// Waveshare's UART labels connect same-name: ESP32 RX -> adapter RX,
// ESP32 TX -> adapter TX. Put each adapter's jumper in position A.
constexpr uint8_t RIGHT_TX_PIN = 11;
constexpr uint8_t RIGHT_RX_PIN = 12;
constexpr uint8_t LEFT_TX_PIN = 13;
constexpr uint8_t LEFT_RX_PIN = 14;

constexpr uint32_t CONSOLE_BAUD = 115200;
constexpr uint32_t SERVO_BAUD = 1000000;
constexpr unsigned long SERVO_IO_TIMEOUT_MS = 20;

constexpr uint8_t MIN_SERVO_ID = 0;
constexpr uint8_t MAX_SERVO_ID = 253;
constexpr uint8_t DEFAULT_SCAN_MAX_ID = 20;
constexpr size_t MAX_TRACKED_SERVOS = 16;

// About 5.3 degrees on a 4096-tick revolution. Two readings must cross this
// threshold before a servo is selected.
constexpr int MOVE_THRESHOLD_TICKS = 60;
constexpr uint8_t MOVE_CONFIRM_READS = 2;
constexpr unsigned long POLL_INTERVAL_MS = 20;
constexpr unsigned long READ_FAILURE_REPORT_MS = 2000;
constexpr unsigned long POST_WRITE_DELAY_MS = 120;
constexpr unsigned long ISOLATION_CONFIRMATION_WINDOW_MS = 60000;

HardwareSerial rightSerial(1);
HardwareSerial leftSerial(2);
SMS_STS rightDriver;
SMS_STS leftDriver;

struct ServoBus {
  const char *name;
  HardwareSerial *serial;
  SMS_STS *driver;
  uint8_t rxPin;
  uint8_t txPin;
  uint8_t allowedIdMin;
  uint8_t allowedIdMax;
};

ServoBus rightBus = {
  "RIGHT", &rightSerial, &rightDriver,
  RIGHT_RX_PIN, RIGHT_TX_PIN, 1, 4
};

ServoBus leftBus = {
  "LEFT", &leftSerial, &leftDriver,
  LEFT_RX_PIN, LEFT_TX_PIN, 5, 8
};

ServoBus *buses[] = {&rightBus, &leftBus};
constexpr size_t BUS_COUNT = sizeof(buses) / sizeof(buses[0]);

struct TrackedServo {
  ServoBus *bus;
  uint8_t id;
  int baselinePosition;
  int lastPosition;
  uint8_t movementHits;
  bool positionReadable;
  bool torqueDisabled;
};

TrackedServo tracked[MAX_TRACKED_SERVOS];
size_t trackedCount = 0;
size_t pollIndex = 0;
unsigned long lastPollMs = 0;
unsigned long lastReadFailureReportMs = 0;
uint8_t lastScanMaxId = DEFAULT_SCAN_MAX_ID;

enum class PairingState {
  WATCHING,
  AWAITING_TARGET_ID,
  AWAITING_ISOLATION,
  AWAITING_CONFIRMATION
};

PairingState state = PairingState::WATCHING;
TrackedServo *selectedServo = nullptr;
int requestedNewId = -1;
bool isolationVerified = false;
unsigned long isolationVerifiedAtMs = 0;

static bool isValidServoId(int id) {
  return id >= MIN_SERVO_ID && id <= MAX_SERVO_ID;
}

static bool isAllowedTargetForBus(const ServoBus &bus, int id) {
  return id >= bus.allowedIdMin && id <= bus.allowedIdMax;
}

static int circularDistance(int a, int b) {
  int distance = abs(a - b) % 4096;
  return min(distance, 4096 - distance);
}

static bool pingOnce(ServoBus &bus, int id) {
  return bus.driver->Ping(static_cast<uint8_t>(id)) == id;
}

static bool pingStable(ServoBus &bus, int id) {
  if (!pingOnce(bus, id)) {
    return false;
  }
  delay(3);
  return pingOnce(bus, id);
}

static bool pingWithRetries(ServoBus &bus, int id) {
  for (int attempt = 0; attempt < 3; ++attempt) {
    if (pingOnce(bus, id)) {
      return true;
    }
    delay(10);
  }
  return false;
}

static bool writeAcknowledgedWithoutError(ServoBus &bus, int result) {
  return result == 1 && bus.driver->Error == 0;
}

static void setupBus(ServoBus &bus) {
  bus.serial->begin(SERVO_BAUD, SERIAL_8N1, bus.rxPin, bus.txPin);
  bus.driver->pSerial = bus.serial;
  bus.driver->IOTimeOut = SERVO_IO_TIMEOUT_MS;
  delay(50);
}

static void printHelp() {
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  scan        Scan IDs 0..20, disable torque, then watch for movement");
  Serial.println("  scan full   Scan IDs 0..253 (slower)");
  Serial.println("  list        Show the currently detected servo addresses");
  Serial.println("  watch       Reset position baselines and resume movement detection");
  Serial.println("  cancel      Cancel the selected servo or pending ID change");
  Serial.println("  isolated    Continue only after every other servo on that side is disconnected");
  Serial.println("  help        Show these instructions");
  Serial.println();
  Serial.println("Pairing flow:");
  Serial.println("  1. Move ONE joint by hand and hold it there.");
  Serial.println("  2. When it is detected, type its intended ID and press Enter.");
  Serial.println("  3. Isolate that servo when prompted; the tool verifies one address.");
  Serial.println("  4. Check the old/new IDs, then type yes within 60 seconds.");
  Serial.println();
  Serial.println("Expected final mapping: RIGHT IDs 1..4, LEFT IDs 5..8.");
  Serial.println("No position commands are sent by this sketch.");
  Serial.println();
}

static void printSafetyBanner() {
  Serial.println();
  Serial.println("Quadi STS3215 ID pairing tool - FIRST DRAFT");
  Serial.println("-------------------------------------------");
  Serial.println("Support the robot so every leg can move freely.");
  Serial.println("Both Waveshare adapters: UART jumper must be at A.");
  Serial.println("Use a servo-matched 12 V supply and share ground with the ESP32.");
  Serial.println();
  Serial.println("IMPORTANT: servos sharing one ID on the same bus cannot be");
  Serial.println("reliably distinguished. This tool will not write an ID until you");
  Serial.println("disconnect every other servo from the selected side and it verifies");
  Serial.println("that exactly one address responds on that bus.");
}

static void printTrackedServos() {
  Serial.println();
  Serial.println("SIDE\tID\tPOSITION\tTORQUE");
  if (trackedCount == 0) {
    Serial.println("(none detected)");
    return;
  }

  for (size_t i = 0; i < trackedCount; ++i) {
    const TrackedServo &servo = tracked[i];
    Serial.print(servo.bus->name);
    Serial.print('\t');
    Serial.print(servo.id);
    Serial.print('\t');
    if (servo.positionReadable) {
      Serial.print(servo.lastPosition);
    } else {
      Serial.print("read failed");
    }
    Serial.println(servo.torqueDisabled ? "\toff acknowledged" : "\tBLOCKED");
  }
  Serial.println();
}

static void resetSelection() {
  selectedServo = nullptr;
  requestedNewId = -1;
  isolationVerified = false;
  isolationVerifiedAtMs = 0;
  state = PairingState::WATCHING;
}

static void resetWatchBaselines() {
  resetSelection();
  pollIndex = 0;

  size_t readableCount = 0;
  for (size_t i = 0; i < trackedCount; ++i) {
    TrackedServo &servo = tracked[i];
    if (!servo.torqueDisabled) {
      continue;
    }
    int position = servo.bus->driver->ReadPos(servo.id);
    servo.positionReadable = position >= 0;
    servo.baselinePosition = position;
    servo.lastPosition = position;
    servo.movementHits = 0;
    if (servo.positionReadable) {
      ++readableCount;
    }
  }

  if (readableCount == 0) {
    Serial.println("No readable servo positions. Check power, UART wiring, and IDs.");
    return;
  }

  Serial.print("Watching ");
  Serial.print(readableCount);
  Serial.println(" servo address(es). Move ONE joint by hand and hold it.");
}

static void addTrackedServo(ServoBus &bus, int id, bool torqueDisabled) {
  if (trackedCount >= MAX_TRACKED_SERVOS) {
    return;
  }

  TrackedServo &servo = tracked[trackedCount++];
  servo.bus = &bus;
  servo.id = static_cast<uint8_t>(id);
  servo.baselinePosition = -1;
  servo.lastPosition = -1;
  servo.movementHits = 0;
  servo.positionReadable = false;
  servo.torqueDisabled = torqueDisabled;
}

static void scanBus(ServoBus &bus, uint8_t maxId) {
  Serial.print("Scanning ");
  Serial.print(bus.name);
  Serial.print(" bus, IDs 0..");
  Serial.print(maxId);
  Serial.println(" ...");

  size_t beforeCount = trackedCount;
  for (int id = MIN_SERVO_ID; id <= maxId; ++id) {
    if (!pingStable(bus, id)) {
      continue;
    }

    Serial.print("  Found ");
    Serial.print(bus.name);
    Serial.print(" ID ");
    Serial.println(id);

    int torqueResult = bus.driver->EnableTorque(static_cast<uint8_t>(id), 0);
    bool torqueDisabled = writeAcknowledgedWithoutError(bus, torqueResult);
    if (!torqueDisabled) {
      Serial.print("    BLOCKED: torque-off was not safely acknowledged (status ");
      Serial.print(bus.driver->Error);
      Serial.println("). This address will not be watched or paired.");
      continue;
    }

    addTrackedServo(bus, id, true);
  }

  Serial.print("  ");
  Serial.print(trackedCount - beforeCount);
  Serial.println(" address(es) found.");
}

static void scanAllBuses(uint8_t maxId) {
  resetSelection();
  trackedCount = 0;
  lastScanMaxId = maxId;

  Serial.println();
  for (size_t i = 0; i < BUS_COUNT; ++i) {
    scanBus(*buses[i], maxId);
  }

  if (trackedCount >= MAX_TRACKED_SERVOS) {
    Serial.println("Warning: tracking list is full; unexpected extra IDs may exist.");
  }

  printTrackedServos();
  if (trackedCount == 0 && maxId < MAX_SERVO_ID) {
    Serial.println("Nothing found in the quick range. Try: scan full");
    return;
  }

  if (trackedCount != 8) {
    Serial.print("Warning: expected 8 physical servos, but detected ");
    Serial.print(trackedCount);
    Serial.println(" unique bus/ID addresses.");
    Serial.println("Duplicate IDs on one side may appear as one address or fail to reply.");
  }

  resetWatchBaselines();
}

static void selectMovedServo(TrackedServo &servo, int position) {
  if (!servo.torqueDisabled) {
    return;
  }
  selectedServo = &servo;
  state = PairingState::AWAITING_TARGET_ID;

  Serial.println();
  Serial.println("Movement detected:");
  Serial.print("  Side: ");
  Serial.println(servo.bus->name);
  Serial.print("  Current ID: ");
  Serial.println(servo.id);
  Serial.print("  Start -> current: ");
  Serial.print(servo.baselinePosition);
  Serial.print(" -> ");
  Serial.println(position);
  Serial.print("Enter intended ID (");
  Serial.print(servo.bus->allowedIdMin);
  Serial.print("..");
  Serial.print(servo.bus->allowedIdMax);
  Serial.println(") or type cancel:");
}

static void pollForMovement() {
  if (state != PairingState::WATCHING || trackedCount == 0) {
    return;
  }
  if (millis() - lastPollMs < POLL_INTERVAL_MS) {
    return;
  }
  lastPollMs = millis();

  TrackedServo &servo = tracked[pollIndex];
  pollIndex = (pollIndex + 1) % trackedCount;

  int position = servo.bus->driver->ReadPos(servo.id);
  if (position < 0) {
    servo.positionReadable = false;
    servo.movementHits = 0;
    if (millis() - lastReadFailureReportMs >= READ_FAILURE_REPORT_MS) {
      Serial.println("A position read failed; watching continues. Type list for details.");
      lastReadFailureReportMs = millis();
    }
    return;
  }

  servo.positionReadable = true;
  servo.lastPosition = position;
  if (servo.baselinePosition < 0) {
    servo.baselinePosition = position;
    return;
  }

  int movement = circularDistance(servo.baselinePosition, position);
  if (movement >= MOVE_THRESHOLD_TICKS) {
    ++servo.movementHits;
    if (servo.movementHits >= MOVE_CONFIRM_READS) {
      selectMovedServo(servo, position);
    }
  } else {
    servo.movementHits = 0;
  }
}

static void requestIdChange(int newId) {
  if (!selectedServo) {
    resetWatchBaselines();
    return;
  }
  if (!isValidServoId(newId)) {
    Serial.println("Invalid ID. Servo IDs must be 0..253.");
    return;
  }
  if (!isAllowedTargetForBus(*selectedServo->bus, newId)) {
    Serial.print("That ID is on the wrong side. ");
    Serial.print(selectedServo->bus->name);
    Serial.print(" must use IDs ");
    Serial.print(selectedServo->bus->allowedIdMin);
    Serial.print("..");
    Serial.println(selectedServo->bus->allowedIdMax);
    return;
  }
  if (newId == selectedServo->id) {
    Serial.println("This servo already has that ID. Resuming watch mode.");
    resetWatchBaselines();
    return;
  }
  if (pingWithRetries(*selectedServo->bus, newId)) {
    Serial.println("REFUSED: the target ID already responds on this same bus.");
    Serial.println("Choose a free target ID. No EEPROM write was attempted.");
    return;
  }

  requestedNewId = newId;
  state = PairingState::AWAITING_ISOLATION;
  Serial.println();
  Serial.println("ID choice recorded, but EEPROM writing is still LOCKED:");
  Serial.print("  Side: ");
  Serial.println(selectedServo->bus->name);
  Serial.print("  Current ID: ");
  Serial.println(selectedServo->id);
  Serial.print("  New ID: ");
  Serial.println(requestedNewId);
  Serial.println();
  Serial.println("Required isolation step:");
  Serial.println("  1. Turn OFF the 12 V servo supply.");
  Serial.println("  2. Disconnect every other servo from this selected side/bus.");
  Serial.println("  3. Leave only the selected physical servo connected.");
  Serial.println("  4. Turn the 12 V servo supply back ON.");
  Serial.println("  5. Type isolated (or cancel). A full bus scan will verify one address.");
}

static void verifySelectedServoIsIsolated() {
  if (!selectedServo || requestedNewId < 0) {
    Serial.println("No selected servo is waiting for isolation.");
    resetWatchBaselines();
    return;
  }

  ServoBus &bus = *selectedServo->bus;
  int respondingCount = 0;
  int respondingId = -1;

  Serial.print("Full isolation scan on ");
  Serial.print(bus.name);
  Serial.println(" bus (IDs 0..253)...");

  for (int id = MIN_SERVO_ID; id <= MAX_SERVO_ID; ++id) {
    if (pingStable(bus, id)) {
      ++respondingCount;
      respondingId = id;
      Serial.print("  Responding ID: ");
      Serial.println(id);
    }
  }

  if (respondingCount != 1 || respondingId != selectedServo->id) {
    Serial.println("ISOLATION NOT VERIFIED. No write is allowed.");
    Serial.print("Expected only current ID ");
    Serial.print(selectedServo->id);
    Serial.print(", but found ");
    Serial.print(respondingCount);
    Serial.println(" stable address(es).");
    Serial.println("Power off, correct the isolation, power on, then type isolated again.");
    return;
  }

  int torqueResult = bus.driver->EnableTorque(selectedServo->id, 0);
  if (!writeAcknowledgedWithoutError(bus, torqueResult)) {
    selectedServo->torqueDisabled = false;
    Serial.println("ISOLATION FOUND, BUT TORQUE-OFF FAILED. No write is allowed.");
    return;
  }

  selectedServo->torqueDisabled = true;
  isolationVerified = true;
  isolationVerifiedAtMs = millis();
  state = PairingState::AWAITING_CONFIRMATION;

  Serial.println("ISOLATION VERIFIED: exactly one address responds and torque-off was acknowledged.");
  Serial.print("Final change: ");
  Serial.print(bus.name);
  Serial.print(" ID ");
  Serial.print(selectedServo->id);
  Serial.print(" -> ");
  Serial.println(requestedNewId);
  Serial.println("Type yes within 60 seconds to write once, or cancel.");
}

static void performConfirmedIdChange() {
  if (!selectedServo || requestedNewId < 0) {
    Serial.println("No complete ID change is pending.");
    resetWatchBaselines();
    return;
  }

  ServoBus &bus = *selectedServo->bus;
  const uint8_t oldId = selectedServo->id;
  const uint8_t newId = static_cast<uint8_t>(requestedNewId);

  if (!isolationVerified || millis() - isolationVerifiedAtMs > ISOLATION_CONFIRMATION_WINDOW_MS) {
    isolationVerified = false;
    state = PairingState::AWAITING_ISOLATION;
    Serial.println("STOPPED: isolation confirmation is missing or expired.");
    Serial.println("Keep one servo connected and type isolated again.");
    return;
  }

  int torqueResult = bus.driver->EnableTorque(oldId, 0);
  if (!writeAcknowledgedWithoutError(bus, torqueResult)) {
    Serial.println("STOPPED: final torque-off check failed. No EEPROM write was attempted.");
    state = PairingState::AWAITING_ISOLATION;
    isolationVerified = false;
    return;
  }

  if (!pingWithRetries(bus, oldId)) {
    Serial.println("STOPPED: the selected current ID no longer responds.");
    Serial.println("No EEPROM write was attempted. Rescan before continuing.");
    resetSelection();
    return;
  }
  if (pingWithRetries(bus, newId)) {
    Serial.println("STOPPED: the target ID began responding before the write.");
    Serial.println("No EEPROM write was attempted. Rescan before continuing.");
    resetSelection();
    return;
  }

  Serial.println("Writing ID once...");
  int unlockResult = bus.driver->unLockEprom(oldId);
  if (!writeAcknowledgedWithoutError(bus, unlockResult)) {
    Serial.println("STOPPED: EEPROM unlock was not safely acknowledged.");
    Serial.println("No ID write was sent. Check for duplicate IDs or flaky wiring.");
    resetSelection();
    return;
  }

  int writeResult = bus.driver->writeByte(oldId, SMS_STS_ID, newId);
  delay(POST_WRITE_DELAY_MS);

  // The write acknowledgement can be missed while the servo changes address,
  // so the new-address ping below is the deciding verification.
  if (!writeAcknowledgedWithoutError(bus, writeResult)) {
    Serial.println("Note: clean ID-write acknowledgement was not received; verifying addresses.");
  }

  bool newIdResponds = pingWithRetries(bus, newId);
  bool oldIdResponds = pingWithRetries(bus, oldId);

  if (newIdResponds && oldIdResponds) {
    int newLockResult = bus.driver->LockEprom(newId);
    bool newLockConfirmed = writeAcknowledgedWithoutError(bus, newLockResult);
    int oldLockResult = bus.driver->LockEprom(oldId);
    bool oldLockConfirmed = writeAcknowledgedWithoutError(bus, oldLockResult);
    Serial.println("STOPPED: both old and new IDs respond after the write.");
    Serial.println("Isolation was not valid. Keep the bus isolated and do not retry blindly.");
    Serial.print("Emergency lock status - old ID: ");
    Serial.print(oldLockConfirmed ? "confirmed" : "UNKNOWN");
    Serial.print(", new ID: ");
    Serial.println(newLockConfirmed ? "confirmed" : "UNKNOWN");
    trackedCount = 0;
    resetSelection();
    return;
  }

  if (!newIdResponds) {
    Serial.println("ID CHANGE NOT CONFIRMED.");
    if (oldIdResponds) {
      int recoveryLock = bus.driver->LockEprom(oldId);
      if (writeAcknowledgedWithoutError(bus, recoveryLock)) {
        Serial.println("The old ID still responds and its EEPROM was re-locked.");
      } else {
        Serial.println("The old ID responds, but EEPROM re-lock was NOT confirmed.");
      }
    } else {
      Serial.println("Neither address responds; EEPROM lock state is unknown.");
    }
    Serial.println("Keep this servo isolated, power-cycle it, then run scan full.");
    trackedCount = 0;
    resetSelection();
    return;
  }

  int lockResult = bus.driver->LockEprom(newId);
  delay(POST_WRITE_DELAY_MS);
  if (!writeAcknowledgedWithoutError(bus, lockResult)) {
    Serial.println("ID CHANGED, BUT EEPROM RE-LOCK WAS NOT CONFIRMED.");
    Serial.println("Keep this servo isolated. Power-cycle it, then ping the new ID before continuing.");
    trackedCount = 0;
    resetSelection();
    return;
  }

  int finalTorqueResult = bus.driver->EnableTorque(newId, 0);
  if (!writeAcknowledgedWithoutError(bus, finalTorqueResult)) {
    Serial.println("ID and EEPROM lock confirmed, but final torque-off was not confirmed.");
    Serial.println("Power off the 12 V supply before reconnecting the other servos.");
  }

  Serial.print("CONFIRMED AND LOCKED: ");
  Serial.print(bus.name);
  Serial.print(" servo now responds as ID ");
  Serial.println(newId);
  Serial.println("Turn OFF 12 V, reconnect the other servos, turn power on, then type scan.");
  trackedCount = 0;
  resetSelection();
}

static void handleLine(String line) {
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) {
    return;
  }

  if (line == "help" || line == "?") {
    printHelp();
    return;
  }
  if (line == "list") {
    printTrackedServos();
    return;
  }
  if (line == "scan") {
    scanAllBuses(DEFAULT_SCAN_MAX_ID);
    return;
  }
  if (line == "scan full") {
    scanAllBuses(MAX_SERVO_ID);
    return;
  }
  if (line == "watch") {
    resetWatchBaselines();
    return;
  }
  if (line == "cancel") {
    Serial.println("Pending selection cancelled.");
    resetWatchBaselines();
    return;
  }

  if (state == PairingState::AWAITING_TARGET_ID) {
    char *end = nullptr;
    long value = strtol(line.c_str(), &end, 10);
    if (end == line.c_str() || *end != '\0') {
      Serial.println("Enter only the intended numeric ID, or type cancel.");
      return;
    }
    requestIdChange(static_cast<int>(value));
    return;
  }

  if (state == PairingState::AWAITING_ISOLATION) {
    if (line == "isolated") {
      verifySelectedServoIsIsolated();
    } else {
      Serial.println("Type isolated after the physical isolation steps, or cancel.");
    }
    return;
  }

  if (state == PairingState::AWAITING_CONFIRMATION) {
    if (line == "yes") {
      performConfirmedIdChange();
    } else {
      Serial.println("Type yes to write, or cancel to stop.");
    }
    return;
  }

  Serial.println("Unknown command. Type help.");
}

void setup() {
  Serial.begin(CONSOLE_BAUD);
  Serial.setTimeout(50);
  delay(1500);

  setupBus(rightBus);
  setupBus(leftBus);

  printSafetyBanner();
  printHelp();
  Serial.println("Starting quick scan automatically...");
  scanAllBuses(DEFAULT_SCAN_MAX_ID);
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    handleLine(line);
  }
  pollForMovement();
}
