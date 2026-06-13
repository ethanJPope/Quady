#include <SCServo.h>

// ESP32-S3 wiring:
// Bus 1: RX 18, TX 17
// Bus 2: RX 16, TX 15
// Change these if your board uses different free GPIOs.
constexpr uint8_t BUS1_RX_PIN = 18;
constexpr uint8_t BUS1_TX_PIN = 17;
constexpr uint8_t BUS2_RX_PIN = 16;
constexpr uint8_t BUS2_TX_PIN = 15;

constexpr uint32_t CONSOLE_BAUD = 115200;
constexpr uint32_t SERVO_BAUD = 1000000;
constexpr unsigned long SERVO_IO_TIMEOUT_MS = 60;
constexpr uint8_t MIN_SERVO_ID = 0;
constexpr uint8_t MAX_SERVO_ID = 253;
constexpr uint8_t BROADCAST_ID = 0xFE;

constexpr int PING_RETRIES = 3;
constexpr uint16_t PING_RETRY_DELAY_MS = 35;
constexpr uint16_t POST_WRITE_DELAY_MS = 100;
constexpr int PING_CONFIRM_HITS = 2;

struct ServoBus {
  const char* label;
  HardwareSerial* serial;
  SMS_STS* driver;
  uint8_t rxPin;
  uint8_t txPin;
};

SMS_STS bus1Driver;
SMS_STS bus2Driver;

ServoBus buses[] = {
  {"bus 1", &Serial1, &bus1Driver, BUS1_RX_PIN, BUS1_TX_PIN},
  {"bus 2", &Serial2, &bus2Driver, BUS2_RX_PIN, BUS2_TX_PIN},
};

constexpr size_t BUS_COUNT = sizeof(buses) / sizeof(buses[0]);

ServoBus* getBus(int busNumber) {
  if (busNumber < 1 || busNumber > static_cast<int>(BUS_COUNT)) {
    return nullptr;
  }
  return &buses[busNumber - 1];
}

bool isValidServoId(int id) {
  return id >= MIN_SERVO_ID && id <= MAX_SERVO_ID;
}

void setupBus(ServoBus& bus) {
  bus.serial->begin(SERVO_BAUD, SERIAL_8N1, bus.rxPin, bus.txPin);
  bus.driver->pSerial = bus.serial;
  bus.driver->IOTimeOut = SERVO_IO_TIMEOUT_MS;
  delay(50);
}

bool pingOnce(ServoBus& bus, int id) {
  return bus.driver->Ping(static_cast<uint8_t>(id)) != -1;
}

bool pingConfirmed(ServoBus& bus, int id) {
  int hits = 0;
  for (int attempt = 0; attempt < PING_RETRIES; ++attempt) {
    if (pingOnce(bus, id)) {
      ++hits;
    }
    delay(PING_RETRY_DELAY_MS);
  }
  return hits >= PING_CONFIRM_HITS;
}

bool pingWithRetries(ServoBus& bus, int id) {
  for (int attempt = 0; attempt < PING_RETRIES; ++attempt) {
    if (pingOnce(bus, id)) {
      return true;
    }
    delay(PING_RETRY_DELAY_MS);
  }
  return false;
}

void printBanner() {
  Serial.println();
  Serial.println("Quady servo ID recovery");
  Serial.println("------------------------");
  Serial.println("Two independent servo buses are available.");
  Serial.println("Leave both controllers plugged in, then use the commands below.");
  Serial.println();
  Serial.println("Important:");
  Serial.println("- If two servos on the same bus share the same ID, the bus cannot tell them apart.");
  Serial.println("- In that case, software alone may not be enough to repair both.");
  Serial.println();
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  help");
  Serial.println("  scan <bus|all> [startId endId]");
  Serial.println("  scanraw <bus|all> [startId endId]");
  Serial.println("    example: scan 1");
  Serial.println("    example: scan all 0 253");
  Serial.println("  ping <bus> <id>");
  Serial.println("    example: ping 2 7");
  Serial.println("  set <bus> <currentId> <newId>");
  Serial.println("    example: set 1 12 3");
  Serial.println("  wizard <bus>");
  Serial.println("    example: wizard 1");
  Serial.println();
}

void printPrompt() {
  Serial.print("quady-id> ");
}

int normalizeRangeStart(int value) {
  if (value < MIN_SERVO_ID) return MIN_SERVO_ID;
  if (value > MAX_SERVO_ID) return MAX_SERVO_ID;
  return value;
}

int normalizeRangeEnd(int value) {
  if (value < MIN_SERVO_ID) return MIN_SERVO_ID;
  if (value > MAX_SERVO_ID) return MAX_SERVO_ID;
  return value;
}

void printScanResult(ServoBus& bus, int id) {
  Serial.print("  ");
  Serial.print(bus.label);
  Serial.print(" ID ");
  Serial.print(id);
  Serial.println(" FOUND");
}

int scanRange(ServoBus& bus, int startId, int endId, bool stableMode) {
  if (startId > endId) {
    int tmp = startId;
    startId = endId;
    endId = tmp;
  }

  startId = normalizeRangeStart(startId);
  endId = normalizeRangeEnd(endId);

  Serial.print("Scanning ");
  Serial.print(bus.label);
  Serial.print(" from ");
  Serial.print(startId);
  Serial.print(" to ");
  Serial.println(endId);

  int foundCount = 0;
  for (int id = startId; id <= endId; ++id) {
    bool found = stableMode ? pingConfirmed(bus, id) : pingWithRetries(bus, id);
    if (found) {
      printScanResult(bus, id);
      ++foundCount;
    }
  }

  Serial.print("Scan complete on ");
  Serial.print(bus.label);
  Serial.print(": ");
  Serial.print(foundCount);
  Serial.println(" servo(s) found.");
  if (foundCount == 0) {
    Serial.println("Check power, wiring, and bus selection.");
  }
  Serial.println();
  return foundCount;
}

void scanAll(int startId, int endId) {
  for (size_t i = 0; i < BUS_COUNT; ++i) {
    scanRange(buses[i], startId, endId, true);
  }
}

void scanAllLoose(int startId, int endId) {
  for (size_t i = 0; i < BUS_COUNT; ++i) {
    scanRange(buses[i], startId, endId, false);
  }
}

bool changeServoId(ServoBus& bus, int currentId, int newId) {
  if (!isValidServoId(currentId) || !isValidServoId(newId)) {
    Serial.println("ID out of range. Use 0..253.");
    return false;
  }

  if (currentId == newId) {
    Serial.println("Current ID and new ID are the same.");
    return false;
  }

  if (newId == BROADCAST_ID) {
    Serial.println("New ID cannot be 254 (broadcast).");
    return false;
  }

  Serial.print("Bus ");
  Serial.print(bus.label);
  Serial.print(": changing ");
  Serial.print(currentId);
  Serial.print(" -> ");
  Serial.println(newId);

  if (!pingWithRetries(bus, currentId)) {
    Serial.println("Current ID not found on this bus.");
    return false;
  }

  if (pingWithRetries(bus, newId)) {
    Serial.println("Target ID already responds on this bus.");
    Serial.println("Pick a different new ID first.");
    return false;
  }

  int unlockResult = bus.driver->unLockEprom(static_cast<uint8_t>(currentId));
  if (unlockResult == 0) {
    Serial.println("Warning: EEPROM unlock did not ack.");
  }
  delay(20);

  int writeResult = bus.driver->writeByte(static_cast<uint8_t>(currentId), SMS_STS_ID, static_cast<uint8_t>(newId));
  if (writeResult == 0) {
    Serial.println("Warning: ID write did not ack.");
  }
  delay(POST_WRITE_DELAY_MS);

  int lockResult = bus.driver->LockEprom(static_cast<uint8_t>(newId));
  if (lockResult == 0) {
    Serial.println("Warning: EEPROM lock did not ack.");
  }
  delay(POST_WRITE_DELAY_MS);

  if (pingWithRetries(bus, newId)) {
    Serial.print("Verified new ID on ");
    Serial.print(bus.label);
    Serial.print(": ");
    Serial.println(newId);
    Serial.println();
    return true;
  }

  Serial.println("Could not confirm the new ID.");
  Serial.println("Rescan this bus to verify what responded.");
  Serial.println();
  return false;
}

void runWizard(ServoBus& bus) {
  Serial.println();
  Serial.print("Wizard mode on ");
  Serial.println(bus.label);
  Serial.println("Type: <currentId> <newId>");
  Serial.println("Other commands: scan, help, exit");
  Serial.println();

  while (true) {
    Serial.print(bus.label);
    Serial.print(" wizard> ");

    while (!Serial.available()) {
      delay(10);
    }

    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      continue;
    }

    line.toLowerCase();

    if (line == "exit" || line == "quit" || line == "q") {
      Serial.println("Leaving wizard mode.");
      Serial.println();
      return;
    }

    if (line == "help" || line == "?") {
      Serial.println("Wizard commands:");
      Serial.println("  <currentId> <newId>");
      Serial.println("  scan");
      Serial.println("  scanraw");
      Serial.println("  exit");
      continue;
    }

      if (line == "scan") {
        scanRange(bus, MIN_SERVO_ID, MAX_SERVO_ID, true);
        continue;
      }

      if (line == "scanraw") {
        scanRange(bus, MIN_SERVO_ID, MAX_SERVO_ID, false);
        continue;
      }

    int currentId = -1;
    int newId = -1;
    if (sscanf(line.c_str(), "%d %d", &currentId, &newId) == 2) {
      changeServoId(bus, currentId, newId);
      continue;
    }

    Serial.println("Unrecognized wizard input.");
  }
}

void handleScanCommand(char* arg1, char* arg2, char* arg3, int tokenCount) {
  int startId = MIN_SERVO_ID;
  int endId = MAX_SERVO_ID;
  if (tokenCount >= 3) {
    startId = atoi(arg2);
  }
  if (tokenCount >= 4) {
    endId = atoi(arg3);
  }

  if (strcmp(arg1, "all") == 0) {
    scanAll(startId, endId);
    return;
  }

  int busNumber = atoi(arg1);
  ServoBus* bus = getBus(busNumber);
  if (!bus) {
    Serial.println("Invalid bus. Use 1 or 2, or 'all'.");
    return;
  }
  scanRange(*bus, startId, endId, true);
}

void handlePingCommand(char* arg1, char* arg2) {
  int busNumber = atoi(arg1);
  int id = atoi(arg2);
  ServoBus* bus = getBus(busNumber);
  if (!bus) {
    Serial.println("Invalid bus. Use 1 or 2.");
    return;
  }
  if (!isValidServoId(id)) {
    Serial.println("ID out of range. Use 0..253.");
    return;
  }

  Serial.print("Pinging ");
  Serial.print(bus->label);
  Serial.print(" ID ");
  Serial.print(id);
  Serial.print(": ");
  if (pingWithRetries(*bus, id)) {
    Serial.println("FOUND");
  } else {
    Serial.println("missing");
  }
}

void handleSetCommand(char* arg1, char* arg2, char* arg3) {
  int busNumber = atoi(arg1);
  int currentId = atoi(arg2);
  int newId = atoi(arg3);
  ServoBus* bus = getBus(busNumber);
  if (!bus) {
    Serial.println("Invalid bus. Use 1 or 2.");
    return;
  }
  changeServoId(*bus, currentId, newId);
}

void processCommand(String line) {
  line.trim();
  if (line.length() == 0) {
    return;
  }

  line.toLowerCase();

  char cmd[16] = {0};
  char arg1[16] = {0};
  char arg2[16] = {0};
  char arg3[16] = {0};
  int tokenCount = sscanf(line.c_str(), "%15s %15s %15s %15s", cmd, arg1, arg2, arg3);

  if (tokenCount <= 0) {
    return;
  }

  if (strcmp(cmd, "help") == 0 || strcmp(cmd, "?") == 0) {
    printHelp();
    return;
  }

  if (strcmp(cmd, "scan") == 0) {
    if (tokenCount < 2) {
      Serial.println("Usage: scan <bus|all> [startId endId]");
      return;
    }
    handleScanCommand(arg1, arg2, arg3, tokenCount);
    return;
  }

  if (strcmp(cmd, "scanraw") == 0) {
    if (tokenCount < 2) {
      Serial.println("Usage: scanraw <bus|all> [startId endId]");
      return;
    }

    int startId = MIN_SERVO_ID;
    int endId = MAX_SERVO_ID;
    if (tokenCount >= 3) {
      startId = atoi(arg2);
    }
    if (tokenCount >= 4) {
      endId = atoi(arg3);
    }

    if (strcmp(arg1, "all") == 0) {
      scanAllLoose(startId, endId);
      return;
    }

    int busNumber = atoi(arg1);
    ServoBus* bus = getBus(busNumber);
    if (!bus) {
      Serial.println("Invalid bus. Use 1 or 2, or 'all'.");
      return;
    }
    scanRange(*bus, startId, endId, false);
    return;
  }

  if (strcmp(cmd, "ping") == 0) {
    if (tokenCount < 3) {
      Serial.println("Usage: ping <bus> <id>");
      return;
    }
    handlePingCommand(arg1, arg2);
    return;
  }

  if (strcmp(cmd, "set") == 0 || strcmp(cmd, "change") == 0) {
    if (tokenCount < 4) {
      Serial.println("Usage: set <bus> <currentId> <newId>");
      return;
    }
    handleSetCommand(arg1, arg2, arg3);
    return;
  }

  if (strcmp(cmd, "wizard") == 0) {
    if (tokenCount < 2) {
      Serial.println("Usage: wizard <bus>");
      return;
    }
    int busNumber = atoi(arg1);
    ServoBus* bus = getBus(busNumber);
    if (!bus) {
      Serial.println("Invalid bus. Use 1 or 2.");
      return;
    }
    runWizard(*bus);
    return;
  }

  Serial.println("Unknown command. Type 'help'.");
}

void setup() {
  Serial.begin(CONSOLE_BAUD);
  Serial.setTimeout(50);
  delay(1500);

  setupBus(buses[0]);
  setupBus(buses[1]);

  printBanner();
  printHelp();
  printPrompt();
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    processCommand(line);
    printPrompt();
  }
}
