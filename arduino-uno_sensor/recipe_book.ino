#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "OBLIGAMEPRRO1";
const char* password = "Trump123_";

String serverUrl = "http://200.100.10.50:3000/sensor/insert/lectura";
const int fsrPin = A0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Conectando a WiFi...");
  }

  Serial.println("Conectado a WiFi");
}

void loop() {
  int valorFSR = analogRead(fsrPin);
  float pesoActual = map(valorFSR, 0, 1023, 0, 1000); // Ajusta el rango si es necesario

  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverUrl);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String payload = "sensor_id=1&valor=" + String(pesoActual);
    int httpCode = http.POST(payload);

    if (httpCode > 0) {
      Serial.printf("POST code: %d\n", httpCode);
      String response = http.getString();
      Serial.println("Server response:");
      Serial.println(response);
    } else {
      Serial.printf("POST failed: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();

  }

  delay(300); // Espera 3 segundos entre lecturas
}
