/*
  esp32_firmware_dual_relay.ino
  ------------------------------
  One ESP32 watching TWO relays (two separate machines) via their NO
  contacts, reporting each independently as "Machine A" and "Machine B".

  receiver.py and the dashboard need ZERO changes for this -- they
  already key everything off the "machine" field in each message.

  WIRING (per relay, same pattern as before):
    Relay A: COM -> ESP32 GND,  NO -> ESP32 GPIO4
    Relay B: COM -> ESP32 GND,  NO -> ESP32 GPIO6

  IMPORTANT: GPIO5 caused a WiFi-related boot crash on this specific
  board (see project notes) -- GPIO6 is used here instead, but test it
  ALONE first (comment out the B channel below, or just watch the
  Serial Monitor closely on first boot) before trusting it fully.

  BEFORE UPLOADING, edit the settings below.
*/

#include <WiFi.h>
#include <HTTPClient.h>

// ---------------------------------------------------------------- SETTINGS
const char* WIFI_SSID     = "WIFINAME"; //Must be same as esp32s3Wifi
const char* WIFI_PASSWORD = "WIFIPASS*";//Must be same as esp32s3Wifi
const char* SERVER_URL    = "http://DeviceThatHostingServerIP:5000/event";  // <-- update to match receiver.py's current IP
// ---------------------------------------------------------------------------

const unsigned long DEBOUNCE_MS  = 50;
const unsigned long HEARTBEAT_MS = 30000;

struct RelayChannel {
  const char* machineName;
  int pin;
  bool lastReading;
  bool lastStableState;
  unsigned long lastDebounceTime;
};

// Add more entries here later if want add a third machine/relay.
RelayChannel channels[] = {
  { "A", 4, HIGH, HIGH, 0 },
  { "B", 6, HIGH, HIGH, 0 },
};
const int NUM_CHANNELS = sizeof(channels) / sizeof(channels[0]);

unsigned long lastHeartbeat = 0;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
}

void sendStatus(const char* machineName, String status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send.");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"machine\":\"" + String(machineName) + "\",\"status\":\"" + status + "\"}";
  int httpCode = http.POST(payload);

  Serial.println("Sent " + String(machineName) + " -> " + status + " | HTTP code: " + String(httpCode));
  http.end();
}

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < NUM_CHANNELS; i++) {
    pinMode(channels[i].pin, INPUT_PULLUP);
  }

  connectWiFi();

  // Report each channel's starting state on boot
  for (int i = 0; i < NUM_CHANNELS; i++) {
    channels[i].lastStableState = digitalRead(channels[i].pin);
    channels[i].lastReading = channels[i].lastStableState;
    sendStatus(channels[i].machineName, channels[i].lastStableState == LOW ? "ON" : "OFF");
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  for (int i = 0; i < NUM_CHANNELS; i++) {
    RelayChannel &ch = channels[i];
    bool reading = digitalRead(ch.pin);

    if (reading != ch.lastReading) {
      ch.lastDebounceTime = millis();
    }

    if ((millis() - ch.lastDebounceTime) > DEBOUNCE_MS) {
      if (reading != ch.lastStableState) {
        ch.lastStableState = reading;
        String status = (ch.lastStableState == LOW) ? "ON" : "OFF";
        Serial.println(String(ch.machineName) + " state changed -> " + status);
        sendStatus(ch.machineName, status);
      }
    }

    ch.lastReading = reading;
  }

  // Heartbeat: resend every channel's current status periodically
  if (millis() - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = millis();
    for (int i = 0; i < NUM_CHANNELS; i++) {
      String status = (channels[i].lastStableState == LOW) ? "ON" : "OFF";
      sendStatus(channels[i].machineName, status);
    }
  }
}
