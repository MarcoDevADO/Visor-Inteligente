#include <Servo.h>
int sensorIR = 12;  // Pin al que está conectado el sensor IR

unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

bool moviendoServo = false;
unsigned long tiempoInicioServo = 0;
const unsigned long duracionServo = 1000;

Servo myServo;
int servoPin = 13;
int servoPos = 0;

int ledV = 8;
int ledN = 9;

void setup() {
  Serial.begin(9600);
  myServo.attach(servoPin);
  pinMode(sensorIR, INPUT);

  pinMode(ledV, OUTPUT);
  pinMode(ledN, OUTPUT);
  myServo.write(0);
}

void loop() {
  // Control del servo
  if (moviendoServo && (millis() - tiempoInicioServo >= duracionServo)) {
    myServo.write(0);
    moviendoServo = false;
  } 

  static bool sensorDetectadoAnterior = false;
  bool sensorDetectado = (digitalRead(sensorIR) == LOW);

  if (sensorDetectado && !sensorDetectadoAnterior) {
    Serial.println("DETECCION_IR");
  }
  sensorDetectadoAnterior = sensorDetectado;

  // Comandos Serial
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();

    if (input == "SERVO_ON") {
      myServo.write(180);
      moviendoServo = true;
      tiempoInicioServo = millis();
    } else if (input == "LED_T") {
      digitalWrite(ledV, HIGH);
      digitalWrite(ledN, LOW);
    } else if (input == "LED_F") {
      digitalWrite(ledV, LOW);
      digitalWrite(ledN, HIGH);
    } else if (input == "LED_OFF") {
      digitalWrite(ledV, LOW);
      digitalWrite(ledN, LOW);
    } else {
      Serial.println(input);
    }
  }
}
