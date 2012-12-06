
/*
 * Arduino code to count blinks on fototransistors connected
 * to digital IO pins.
 *
 * Osram SFH 300 Silicon NPN Phototransistor appears to work fine.
 * Connect the short lead (collector) to the IO pin and
 * the long lead (emitter) to a ground pin of the Arduino.
 *
 * This little program counts how many blinks the transistor
 * has detected, and reports the counters over USB serial every
 * 5 seconds.
 *
 * The green led on the Arduino also blinks every time a blink
 * is detected on any of the sensors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of either:
 *
 * a) the GNU General Public License as published by the Free Software
 * Foundation; either version 1, or (at your option) any later version, or
 * b) the "Artistic License".
 *
 */

// LED pin
#define LED   13

// How many sensors?
#define SENSORS 5

// Arduino pin numbers for each sensor,
// port 0 ... port 4, for 5 sensors:
int pins[SENSORS] = { 8, 9, 10, 11, 12 };

// the current state of each sensor (light or no light seen?)
int state[SENSORS];

// how many blinks have been counted on each sensor
int blinks[SENSORS];

// Serial port speed
#define SERIAL_SPEED 115200

// Reporting interval on serial port, in milliseconds
#define REPORT_INTERVAL 5000

void setup()
{
    Serial.begin(SERIAL_SPEED);
    Serial.println("blinkcount start");

    /* initialize each sensor */ 
    for (int i = 0; i < SENSORS; i++) {
        /* Set the pin to input, and enable internal pull-up by
         * writing a 1. This way we won't need any other components.
         */
        pinMode(pins[i], INPUT);
        digitalWrite(pins[i], 1); // pull up
        state[i] = HIGH;
        blinks[i] = 0;
    }
}

void loop()
{
    int i;
    int t;
    int ledloops = 0;
    int led = LOW;
    unsigned long loops = 0;
    unsigned long next_print = millis() + REPORT_INTERVAL;
    
    // busy loop eternally
    while (1) {
        // go through each sensor
        for (i = 0; i < SENSORS; i++) {
            
            // read current value
            t = digitalRead(pins[i]);
            
            // check if state changed:
            if (t != state[i]) {
                state[i] = t;
                // no light to light shows as HIGH to LOW change on the pin,
                // as the photodiode starts to conduct
                if (t == LOW) {
                    blinks[i] += 1;
                    
                    // trigger arduino's own led up to indicate we have detected
                    // a blink
                    led = HIGH;
                    ledloops = 0;
                }
            }
        }
        
        // control my own led - keep it up for 4000 rounds (short blink)
        if (led == HIGH) {
             if (ledloops == 0)
                 digitalWrite(LED, HIGH);
             ledloops++;
             if (ledloops == 4000) {
                 digitalWrite(LED, LOW);
                 led = LOW;
             }
        }
        
        // Every 10000 rounds (quite often), check current uptime
        // and if REPORT_INTERVAL has passed, print out current values.
        // If this would take too long time (slow serial speed) or happen
        // very often, we could miss some blinks while doing this.
        loops++;
        if (loops == 10000) {
            loops = 0;
            
            if (millis() >= next_print) {
                next_print += REPORT_INTERVAL;
                Serial.println("+"); // start marker
                for (int i = 0; i < SENSORS; i++) {
                    Serial.print(i, DEC);
                    Serial.print(" ");
                    Serial.println(blinks[i], DEC);
                    blinks[i] = 0;
                }
                Serial.println("-"); // end marker
            }
        }
    }
}

