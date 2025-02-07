#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = 
  "wifi-robot"; // WiFi in the Lab (public)
//  "ZeroYear"; // WiFi at home

//const char *pass = "olar1234"; //password for home WiFi

const char* mqtt_server = "192.168.0.107"; // Rasperry Pi IP

// MQTT Broker for testing
/*const char *mqtt_broker = "broker.emqx.io";
const char *topic = "emqx/esp32";
const char *mqtt_username = "emqx";
const char *mqtt_password = "public";
const int mqtt_port = 1883;*/

WiFiClient espClient;
PubSubClient client(espClient);

int analogPin = A3;
int photodiode_measure = 0; // store value we read from photo diode
#define MSG_SIZE 50

int photodiode_measures[MSG_SIZE];
//char measures_msg[6*MSG_SIZE];
int measures_cnt = 0;

int dir, wait_time;

// defines pins
#define stepPin 2
#define dirPin 13

void setup() {
  Serial.begin(9600);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  //client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);

  // Sets the two pins as Outputs
  pinMode(stepPin, OUTPUT); 
  pinMode(dirPin, OUTPUT);
  digitalWrite(dirPin, HIGH);
}

void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid);
  //WiFi.begin(ssid, pass);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  if (strcmp(topic, "motor") == 0) {
    //format for our Raspberry Pi message
    // DIR,WAIT_TIME
    // DIR is equal to 0 for LOW and 1 for HIGH (-1)
    // WAIT_TIME is an integer
    
    // Parse message into DIR and WAIT_TIME
    if (sscanf(messageTemp.c_str(), "%d,%d", &dir, &wait_time) == 2) {
      Serial.print("Direction: ");
      Serial.print(dir);
      Serial.print(", Wait Time: ");
      Serial.println(wait_time);
    } else {
      Serial.println("Invalid motor command format!");
    }
  }

}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
      // Subscribe
      client.subscribe("testTopic");
      client.subscribe("motor");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  //char *testmsg = "BATMAN";
  //client.publish("testTopic", testmsg);

  photodiode_measure = analogRead(analogPin);  // read the input from photodiode

  if(measures_cnt < MSG_SIZE){
    photodiode_measures[measures_cnt] = photodiode_measure;
    measures_cnt += 1;
  }else{
    // we need to onvert integer array to char array (mqtt message!)
    Serial.println(photodiode_measures[0]);  
    client.publish("measures", (uint8_t*)photodiode_measures, (sizeof(photodiode_measures)/sizeof(photodiode_measures[0])) * sizeof(int));
    measures_cnt = 0;

    /*
    measures_msg[0] = '\0';  // Clear the buffer
    for (int i = 0; i < MSG_SIZE; i++) {
        char buffer[6];  // buffer has integer and a comma
        snprintf(buffer, sizeof(buffer), "%d,", photodiode_measures[i]);
        strncat(measures_msg, buffer, sizeof(measures_msg) - strlen(measures_msg) - 1);
    }

    // Remove the last comma to insert string terminator \0
    int len = strlen(measures_msg);
    if (len > 0) {
        measures_msg[len - 1] = '\0';
    }
    Serial.println(measures_msg);
    client.publish("measures", measures_msg);
    measures_cnt = 0;*/
  }
  if(dir == 0){
    digitalWrite(stepPin, LOW);
    
  }else if(dir==-1){
    digitalWrite(dirPin, LOW);

    digitalWrite(stepPin, HIGH); 
    delayMicroseconds(wait_time);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(wait_time);
  }else{
    digitalWrite(dirPin, HIGH);

    digitalWrite(stepPin, HIGH); 
    delayMicroseconds(wait_time);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(wait_time);
  }
  delay(1);
}