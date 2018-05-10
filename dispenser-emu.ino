const byte ledPin = 13;
const byte strobePin = 2;
const byte busyPin = 4;

volatile byte go = 0;

void do_start(void) {
  go = 1;  
}

void setup() {
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  
  pinMode(strobePin, INPUT_PULLUP);
  pinMode(busyPin, INPUT);    // actually an output, but Hi-Z when not active

  attachInterrupt(digitalPinToInterrupt(strobePin), do_start, RISING);
  
}

void loop() {
  if (go) {
    digitalWrite(busyPin, LOW);
    pinMode(busyPin, OUTPUT);

    // activate the LED so we can see it happening
    digitalWrite(ledPin, HIGH);

    delay(12000);    // 12 seconds to simulate dispenser actuation

    digitalWrite(ledPin, LOW);
    pinMode(busyPin, INPUT);    // Hi-Z

    go = 0;
  }

}
