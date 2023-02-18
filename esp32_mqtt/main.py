from umqtt.robust import MQTTClient
import time
import random
import machine
import json
import ntptime
import onewire, ds18x20

from esp32_tools import network_connect, get_lockal_time

pin = machine.Pin(2)  #blinking is optional, check your LED pin

#Place these two certs at same folder level as your MicroPython program

CERT_FILE = "/certs/certificate.pem.crt"  #the ".crt" may be hidden that’s ok
KEY_FILE = "/certs/private.pem.key"
MQTT_HOST_FILE = "/certs/mqtt_host.txt"

MQTT_CLIENT_ID = "myESP32"
MQTT_PORT = 8883 #MQTT secured

PUB_TOPIC = "iot/outTopic" #coming out of device
SUB_TOPIC = "iot/inTopic"  #coming into device

#Change the following three settings to match your environment
#IoT Core-->Settings or > aws iot describe-endpoint --endpoint-type iot:Data-ATS
# MQTT_HOST = "ag70ix3de6ld7-ats.iot.eu-central-1.amazonaws.com"  #Your AWS IoT endpoint
with open(MQTT_HOST_FILE, "r") as mqtt_host_fd:
    MQTT_HOST = mqtt_host_fd.read()
# WIFI_SSID = "Dobro.."
# WIFI_PW = "dobrodobro"

MQTT_CLIENT = None

print("starting program")

def device_connect():    
    global MQTT_CLIENT

    try:  #all this below runs once, equivalent to Arduino's "setup" function)
        with open(KEY_FILE, "r") as f: 
            key = f.read()
        print("Got Key")
       
        with open(CERT_FILE, "r") as f: 
            cert = f.read()
        print("Got Cert")

        MQTT_CLIENT = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_HOST, port=MQTT_PORT, keepalive=5000, ssl=True, ssl_params={"cert":cert, "key":key, "server_side":False})
        MQTT_CLIENT.connect()
        print('MQTT Connected')
        MQTT_CLIENT.set_callback(sub_cb)
        MQTT_CLIENT.subscribe(SUB_TOPIC)
        MQTT_CLIENT.subscribe(PUB_TOPIC)
        print('Subscribed to %s as the incoming topic' % (SUB_TOPIC))
        return MQTT_CLIENT
    except Exception as e:
        print('Cannot connect MQTT: ' + str(e))
        raise

def pub_msg(msg):  #publish is synchronous so we poll and publish
    global MQTT_CLIENT
    try:    
        MQTT_CLIENT.publish(PUB_TOPIC, msg)
        print("Sent: " + msg)
    except Exception as e:
        print("Exception publish: " + str(e))
        raise

def sub_cb(topic, msg):
    print('Device received a Message: ')
    payload = json.loads(msg.decode("utf-8"))
    print(topic.decode("utf-8") + ":")
    print(json.dumps(payload))
    # print((topic, msg))  #print incoming message, waits for loop below
    pin.value(0)         #blink if incoming message by toggle off

def ds_init(pin):
    ow = onewire.OneWire(machine.Pin(15)) # create a OneWire bus on GPIO12
    ds = ds18x20.DS18X20(ow)
    return ds

def get_temperature(ds):    
    roms = ds.scan()
    ds.convert_temp()
    time.sleep_ms(750)
    rom = roms[0]
    return ds.read_temp(rom)

try:
    print("Connecting WIFI")
    if not network_connect(wifi_list="known_wifi.json"):
        exit 
    print("Connecting MQTT")
    device_connect()
    print("Getting time from Internet")
    ntptime.settime()
    print("Local time is " + str(time.localtime()))
    get_lockal_time(timezone=2)

    th_sensor = ds_init(15)

    while True: #loop forever
            pin.value(1)
            pending_message = MQTT_CLIENT.check_msg()  # check for new subscription payload incoming
            if pending_message != 'None':  #check if we have a message 
                payload = {}
                temp =  random.randint(0, 130)
                humid = random.randint(0, 100)
                timestamp = get_lockal_time(timezone=2, day_light_save=True)
                payload.update({"temperature": round(get_temperature(th_sensor), 1)})
                payload.update({"humidity": humid})
                payload.update({"time": str(timestamp.get("hour")) + ":" + str(timestamp.get("minute")) + ":" + str(timestamp.get("second"))})
                print("Publishing")
                pub_msg(json.dumps(payload)) 
                print("published payload")
                time.sleep(5)  #A 5 second delay between publishing, adjust as you like

except Exception as e:
    print(str(e))
