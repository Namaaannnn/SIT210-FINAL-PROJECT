#include <SPI.h>
#include <MFRC522.h>
#include <LiquidCrystal.h>

#include <WiFiNINA.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "Naman's iPhone";
const char* password = "Naman123";

// MQTT broker details
const char* mqttServer = "broker.emqx.io"; 
const int mqttPort = 1883;                      // Default port for MQTT
const char* mqttUser = "RF_SMART_CARD_0192";    // Leave blank if no authentication
const char* mqttPassword = "RF_SMART_CARD_11"; // Leave blank if no authentication

const char* publish_topic = "RF_SMART_CART_DTS";

WiFiClient wifiClient;
PubSubClient client(wifiClient);


#define RST_PIN 9
#define SS_PIN 10

#define SW 8

#define RS 2
#define EN 3
#define D4 4
#define D5 5
#define D6 6
#define D7 7

LiquidCrystal lcd(RS, EN, D4, D5, D6, D7);

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance

// Define the UID for the 10 cards
byte cardUIDs[10][4] = {
  {0x93, 0xD8, 0x5F, 0x03}, // UID A
  {0x43, 0xFA, 0x25, 0xFB}, // UID B
  {0x03, 0xCB, 0x84, 0xA1}, // UID C
  {0xD9, 0xCA, 0xC7, 0xD4}, // UID D
  {0x69, 0x44, 0xB4, 0xC2}, // UID E
  {0x33, 0x45, 0xC4, 0x02}, // UID F
  {0x93, 0xA6, 0x6C, 0x30}, // UID G
  {0x43, 0x2B, 0x6F, 0x30}, // UID H
  {0x63, 0x80, 0x80, 0xFA}, // UID I
  {0x43, 0x00, 0x8B, 0xFA}  // UID J
};


// Define names corresponding to the cards
String cardNames[10] = {
  "Inventory",
  "Kiwi",
  "Apple",
  "Orange",
  "Kurkure",
  "Lays",
  "Maggei",
  "Oreo",
  "Dettol",
  "KitKat"
};

void setup() {
  Serial.begin(9600);

  lcd.clear();
  lcd.setCursor(0, 1);
  lcd.print("Connecting to WiFi..");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  delay(500);
  Serial.println("Connected to WiFi");
  lcd.clear();
  lcd.setCursor(0, 1);
  lcd.print("Connected to WiFi");
  // Set MQTT server
  client.setServer(mqttServer, mqttPort);

  // Connect to MQTT broker
  connectToMqtt();

  pinMode(SW, INPUT_PULLUP);

  lcd.begin(20, 4);
  SPI.begin();
  mfrc522.PCD_Init();
  delay(1000);
  lcd.clear();
}

void loop() {
  // Ensure the client stays connected to the broker
  if (!client.connected()) {
    connectToMqtt();
  }
  client.loop();

  initial_lcd();
  if (digitalRead(SW) == LOW) {
    remove_item();
  }
  else {
    add_item();
  }


  delay(500);  // Display the name for 2 seconds before clearing
}

void initial_lcd() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("RF BASED SMART CART ");
  lcd.setCursor(0, 1);
  lcd.print("--------------------");
  lcd.setCursor(0, 2);
  lcd.print("Waiting for item....");
  lcd.setCursor(0, 3);
  lcd.print("PRESS BTN TO REMOVE ");
  delay(200);
}

void add_item_lcd(String item) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("RF BASED SMART CART ");
  lcd.setCursor(0, 1);
  lcd.print("--------------------");
  lcd.setCursor(0, 2);
  lcd.print(item);
  lcd.setCursor(0, 3);
  lcd.print("Successfully Added");

  String pkt = "+,"+String(item);
  // Send a message to the MQTT broker
  publishMessage(publish_topic, pkt.c_str());
  
  delay(1500);
}

void remove_item_lcd(String item) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("RF BASED SMART CART ");
  lcd.setCursor(0, 1);
  lcd.print("--------------------");
  lcd.setCursor(0, 2);
  lcd.print(item);
  lcd.setCursor(0, 3);
  lcd.print("Successfully Removed");
  String pkt = "-,"+String(item);
  // Send a message to the MQTT broker
  publishMessage(publish_topic, pkt.c_str());
  
  delay(1500);
}

void add_item() {
  // Reset the loop if no new card present on the sensor/reader
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Print UID
  Serial.print("UID: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(i < mfrc522.uid.size - 1 ? ":" : "");
  }
  Serial.println();

  // Compare the UID with the stored cards
  String cardName = "Unknown"; // Default name if no match found
  for (int i = 0; i < 10; i++) {
    boolean match = true;
    for (byte j = 0; j < 4; j++) {
      if (mfrc522.uid.uidByte[j] != cardUIDs[i][j]) {
        match = false;
        break;
      }
    }
    if (match) {
      cardName = cardNames[i];
      break;
    }
  }

  add_item_lcd(cardName);

  // Halt PICC to be ready for the next read
  mfrc522.PICC_HaltA();
}

void remove_item() {
  // Reset the loop if no new card present on the sensor/reader
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Print UID
  Serial.print("UID: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(i < mfrc522.uid.size - 1 ? ":" : "");
  }
  Serial.println();

  // Compare the UID with the stored cards
  String cardName = "Unknown"; // Default name if no match found
  for (int i = 0; i < 10; i++) {
    boolean match = true;
    for (byte j = 0; j < 4; j++) {
      if (mfrc522.uid.uidByte[j] != cardUIDs[i][j]) {
        match = false;
        break;
      }
    }
    if (match) {
      cardName = cardNames[i];
      break;
    }
  }

  remove_item_lcd(cardName);

  // Halt PICC to be ready for the next read
  mfrc522.PICC_HaltA();
}

void connectToMqtt() {
  while (!client.connected()) {
    Serial.println("Connecting to MQTT...");

    // Connect to the broker with optional username/password
    if (client.connect("ArduinoNano33IoTClient", mqttUser, mqttPassword)) {
      Serial.println("Connected to MQTT broker");
    } else {
      Serial.print("Failed with state ");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void publishMessage(const char* topic, const char* message) {
  if (client.publish(topic, message)) {
    Serial.print("Message sent to topic ");
    Serial.print(topic);
    Serial.print(": ");
    Serial.println(message);
  } else {
    Serial.println("Failed to send message");
  }
}