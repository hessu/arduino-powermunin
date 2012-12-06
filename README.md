
arduino-powermunin
==================

This is a very simple but working project to monitor the blinking led on
common electricity meters (power meters) installed by utility companies.

Required hardware:
------------------

1. An Arduino (I used a Duemilanove, but Uno, or anything else goes)
2. At least one phototransistor sensitive to visible light (many are only
   sensitive to infrared, and I don't know how much infrared a normal
   red LED produces). Osram SFH 300 seems to work fine. I used 5
   phototransistors since I'm monitoring 5 power meters!
3. 2 wires to connect the phototransistor to the Arduino (I used 5-wire
   phone cable, 3-wire telephone cable would work too, or just about
   anything else)
4. Header pins to stick in the Arduino's header for soldering the wires
5. USB cable to connect the Arduino to a computer

Installation instructions (short version)
-----------------------------------------

1. Install a single phototransistor (i used Osram SFH 300) to an IO pin
   of the Arduino. Used pins defined in the arduino source code.
2. Tape the phototransistor tightly in front of the red blinking led
   of the electricity meter.
3. Install the blinkcount Arduino code (found in the blinkcount
   subdirectory) on the Arduino
4. Observe accumulated counters printed on the USB serial port
5. Run src/powermunind which collects counter increments and dumps them
   to a state file
6. Install src/power_munin munin plugin which gives out the state file
   to munin. Optionally, set some configuration within the script.

Adjustments for different power meters
--------------------------------------

On my power meter the led blinks 1000 times per kWh, meaning 1 blink is 1 Wh
(1 watt consumed in 1 hour).  Munin, by default, prints the amount of blinks
per second - it divides the amount of blinks by the amount of seconds in the
5-minute plotting interval (roughly 300 seconds).

I wished to plot the average power consumption within the 5 minute polling
interval instead (in Watts), so I multiply Munin's blinks/s (watthours/s) value
by 3600, resulting in a displayed value of watthours/hour, i.e. watts.

The multiplication is done by RPN math in rrdtool, configured in the
power_munin script's configuration section for each port:

    port0.cdef port0,3600,*

This takes port0's current value, and multiplies it by 3600. If your power
meter would only blink 500 times per kWh, you'd have to multiply it by 7200
to display watts.

