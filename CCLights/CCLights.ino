#define PIN_RED    2   // D2
#define PIN_YELLOW 3   // D3
#define PIN_GREEN  4  // D4

void setup() {
    pinMode(PIN_RED, OUTPUT);
    pinMode(PIN_YELLOW, OUTPUT);
    pinMode(PIN_GREEN, OUTPUT);
    Serial.begin(9600);
    setGreen(); // 默认空闲绿灯
}

void loop() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        switch (cmd) {
            case 'R': setRed(); break;
            case 'Y': setYellow(); break;
            case 'G': setGreen(); break;
            case 'O': allOff(); break;
        }
    }
}

void setRed()    { digitalWrite(PIN_RED, HIGH); digitalWrite(PIN_YELLOW, LOW); digitalWrite(PIN_GREEN, LOW); }
void setYellow() { digitalWrite(PIN_RED, LOW);  digitalWrite(PIN_YELLOW, HIGH); digitalWrite(PIN_GREEN, LOW); }
void setGreen()  { digitalWrite(PIN_RED, LOW);  digitalWrite(PIN_YELLOW, LOW); digitalWrite(PIN_GREEN, HIGH); }
void allOff()    { digitalWrite(PIN_RED, LOW);  digitalWrite(PIN_YELLOW, LOW); digitalWrite(PIN_GREEN, LOW); }