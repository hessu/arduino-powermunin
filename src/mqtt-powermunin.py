#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

__author__ = "Kyle Gordon"
__copyright__ = "Copyright (C) Kyle Gordon"

import os
import logging
import signal
import socket
import time
import sys
import serial

import mosquitto
import ConfigParser
import setproctitle

# Read the config file
config = ConfigParser.RawConfigParser()
config.read("mqtt-powermunin.cfg")

# Use ConfigParser to pick out the settings
DEBUG = config.getboolean("global", "debug")
LOGFILE = config.get("global", "logfile")
MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")
MQTT_SUBTOPIC = config.get("global", "MQTT_SUBTOPIC")
MQTT_TOPIC = "raw/" + socket.getfqdn() + MQTT_SUBTOPIC

SENDINTERVAL = config.getint("global", "sendinterval")
DEVICESFILE = config.get("global", "devicesfile")

last_send = time.time()


owserver = ""

APPNAME = "mqtt-powermunin"
PRESENCETOPIC = "clients/" + socket.getfqdn() + "/" + APPNAME + "/state"
setproctitle.setproctitle(APPNAME)
client_id = APPNAME + "_%d" % os.getpid()
mqttc = mosquitto.Mosquitto(client_id)

LOGFORMAT = '%(asctime)-15s %(message)s'

if DEBUG:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.DEBUG,
                        format=LOGFORMAT)
else:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.INFO,
                        format=LOGFORMAT)

logging.info("Starting " + APPNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

class SampleStore:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.samples = 0
        self.sum = 0.0
        self.max = None
        self.min = None
    
    def add(self, value):
        self.samples += 1
        self.sum += value
        
        if self.max == None or value > self.max:
            self.max = value
        
        if self.min == None or value < self.min:
            self.min = value
    
    def average(self):
        if self.samples < 1:
            return None
            
        return self.sum / self.samples
        
    def deviation(self):
        return abs(self.max - self.min)


# All the MQTT callbacks start here

def on_publish(mosq, obj, mid):
    """
    What to do when a message is published
    """
    logging.debug("MID " + str(mid) + " published.")


def on_subscribe(mosq, obj, mid, qos_list):
    """
    What to do in the event of subscribing to a topic"
    """
    logging.debug("Subscribe with mid " + str(mid) + " received.")


def on_unsubscribe(mosq, obj, mid):
    """
    What to do in the event of unsubscribing from a topic
    """
    logging.debug("Unsubscribe with mid " + str(mid) + " received.")


def on_connect(mosq, obj, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().
    The parameter rc is an integer giving the return code:

    0: Success
    1: Refused – unacceptable protocol version
    2: Refused – identifier rejected
    3: Refused – server unavailable
    4: Refused – bad user name or password (MQTT v3.1 broker only)
    5: Refused – not authorised (MQTT v3.1 broker only)
    """
    logging.debug("on_connect RC: " + str(result_code))
    if result_code == 0:
        logging.info("Connected to %s:%s", MQTT_HOST, MQTT_PORT)
        # Publish retained LWT as per
        # http://stackoverflow.com/q/97694
        # See also the will_set function in connect() below
        mqttc.publish(PRESENCETOPIC, "1", retain=True)
        process_connection()
    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
        cleanup()
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
        cleanup()
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
        logging.info("Retrying in 30 seconds")
        time.sleep(30)
    elif result_code == 4:
        logging.info("Connection refused - bad user name or password")
        cleanup()
    elif result_code == 5:
        logging.info("Connection refused - not authorised")
        cleanup()
    else:
        logging.warning("Something went wrong. RC:" + str(result_code))
        cleanup()


def on_disconnect(mosq, obj, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logging.info("Clean disconnection")
        sys.exit(0)
    else:
        logging.info("Unexpected disconnection! Reconnecting in 5 seconds")
        logging.debug("Result code: %s", result_code)
        time.sleep(5)


def on_message(mosq, obj, msg):
    """
    What to do when the client recieves a message from the broker
    """
    logging.debug("Received: " + msg.payload +
                  " received on topic " + msg.topic +
                  " with QoS " + str(msg.qos))
    process_message(msg)


def on_log(mosq, obj, level, string):
    """
    What to do with debug log output from the MQTT library
    """
    logging.debug(string)

# End of MQTT callbacks


def cleanup(signum, frame):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """
    logging.info("Disconnecting from broker")
    # Publish a retained message to state that this client is offline
    mqttc.publish(PRESENCETOPIC, "0", retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()
    logging.info("Exiting on signal %d", signum)
    sys.exit(signum)

def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    This will also set the Last Will and Testament (LWT)
    The LWT will be published in the event of an unclean or
    unexpected disconnection.
    """
    logging.debug("Connecting to %s:%s", MQTT_HOST, MQTT_PORT)
    # Set the Last Will and Testament (LWT) *before* connecting
    mqttc.will_set(PRESENCETOPIC, "0", qos=0, retain=True)
    result = mqttc.connect(MQTT_HOST, MQTT_PORT, 60, True)
    if result != 0:
        logging.info("Connection failed with error code %s. Retrying", result)
        time.sleep(10)
        connect()

    # Define the callbacks
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_unsubscribe = on_unsubscribe
    mqttc.on_message = on_message
    if DEBUG:
        mqttc.on_log = on_log

    mqttc.loop_start()

def process_connection():
    """
    What to do when a new connection is established
    """
    logging.debug("Processing connection")


def process_message(mosq, obj, msg):
    """
    What to do with the message that's arrived
    """
    logging.debug("Received: %s", msg.topic)


def find_in_sublists(lst, value):
    for sub_i, sublist in enumerate(lst):
        try:
            return (sub_i, sublist.index(value))
        except ValueError:
            pass

    raise ValueError("%s is not in lists" % value)

class DevicesList():
    """
    Read the list of devices, and expand to include publishing state and current value
    """
    import csv
    datafile = open(DEVICESFILE, "r")
    datareader = csv.reader(datafile)
    data = {}
    store = {}

    for row in datareader:
        input = int(row[0])
        name = row[1]
        blinks_per_kwh = row[2]
        data[input] = (name, int(blinks_per_kwh))
        store[input] = SampleStore()
        
    logging.info("read devices: %r" % data)

def process(buf):
    plus = buf.find("+\r\n")
    if plus < 0:
        return
    
    buf = buf[plus+3:]
    for l in buf.split("\r\n"):
        if l.startswith('-'):
            break
        
        try:
            a = l.split(' ')
            
            if len(a) != 4:
                logging.error("Wrong number of entries on line: %r", l)
                return
            
            input = int(a[0])
            pulses = int(a[1])
            last_pulse_interval = int(a[2])
            checksum = int(a[3])
        except ValueError, e:
            logging.error("Parsing exception: %r", e)
            logging.error("Problematic line: %r", l)
            return
        
        if input ^ pulses ^ last_pulse_interval != checksum:
            logging.error("Checksum mismatch: %r", l)
            return
        
        c = DevicesList.data.get(input)
        store = DevicesList.store.get(input)
        
        #print "data: %r" % DevicesList.data
        #print "input: %r: %r" % (input, c)
        name = c[0]
        pulses_per_kwh = c[1]
        #print "input name: %s" % name
        
        watthours = float(pulses) / float(pulses_per_kwh) * 1000.0
        
        if last_pulse_interval >= 1.0:
            instant_power = (3600.0*10000.0)/last_pulse_interval
        else:
            instant_power = 0
        
        if instant_power < 0 or instant_power > 25000:
            logging.info("suspicious instant power, ignoring")
            break
        
        store.add(instant_power)
        
        logging.info("input %d [%s]: %.0f pulses: %.1f Wh %.0f W (avg %.0f W)", input, name, pulses, watthours, instant_power, store.average())
        
        global last_send
        
        now = time.time()
        if now - last_send >= SENDINTERVAL or now < last_send:
            last_send = now
            
            mqttc.publish(MQTT_TOPIC + name + "/watthours", watthours)
            mqttc.publish(MQTT_TOPIC + name + "/watts", round(store.average()))
            
            store.reset()

def main_loop():
    """
    The main loop in which we stay connected to the broker
    """
    while True:
        try:
            ser = serial.Serial('/dev/ttyACM1', 115200, timeout=10)
        except serial.serialutil.SerialException, e:
            logging.error("Serial opening exception: %r", e)
            time.sleep(10)
            continue
        
        logging.info("opened serial")
        buf = ''
        going = True
        
        while going:
            try:
                line = ser.readline()   # read a '\n' terminated line
            except Exception, e:
                logging.error("Serial exception: %r" % e)
                going = False
            
            logging.debug("read: %r" % line)
            buf += line
            
            if line == "-\r\n":
                process(buf)
                buf = ''
                   
        time.sleep(4)
        
    
# Use the signal module to handle signals
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# Connect to the broker and enter the main loop
connect()

# Try to start the main loop
try:
    main_loop()
except KeyboardInterrupt:
    logging.info("Interrupted by keypress")
    sys.exit(0)

