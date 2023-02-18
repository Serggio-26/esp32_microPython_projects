import network
import ntptime
import time
import json

def network_scan():
    print(f"\nScan WIFI network")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    apn_list = wlan.scan()
    ssid_list = []
    for apnssid, bssi, channel, rssi, authmode, hidden in apn_list:
        apnssid = apnssid.decode("utf-8")
        ssid_list.append(apnssid)
        print(f"SSID: \"{apnssid}\", \tRSSI = {rssi}, \tHidden: {hidden}")
    return ssid_list


def network_connect(ssid='', password='', wifi_list=None):
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected() and ssid == wlan.config('essid'):
        return True

    exist_ssid = network_scan()
    if ssid and ssid not in exist_ssid:
        print(f"SSID \"{ssid}\" not accessible")
        return False

    if wifi_list:
        with open(wifi_list, "r") as apn_file:
            apns = json.loads(apn_file.read())
            apn_list = apns.get("access_points")

        for apn in apn_list:
            if apn.get("ssid") in exist_ssid:
                ssid = apn.get("ssid")
                password = apn.get("password")
                break

    if not ssid:
        print("There are no known SSIDs")
        return False

    print(f'connecting to \"{ssid}\"...')
    wlan.active(True)
    start = time.ticks_ms()
    wlan.connect(ssid, password)
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < 10000:
        pass
    if not wlan.isconnected():
        print("Network connection is timed out")
        return False
    print('network config:', wlan.ifconfig())
    return True

def daylight_correct(timestamp):
    if timestamp.get("month") > 3 and timestamp.get("month") < 10:
        summer = True
    elif timestamp.get("month") == 3 and timestamp.get("day") + 6 - timestamp.get("weekday") > 31:
        summer = True
    elif timestamp.get("month") == 9 and timestamp.get("day") + 6 - timestamp.get("weekday") <= 31:
        summer = True
    else:
        summer = False

    if summer:
        timestamp.update({"hour": timestamp.get("hour") + 1})
        if timestamp.get("hour") > 23:
            timestamp.update({"hour": 0})
            timestamp.update({"day": timestamp.get("day") + 1})

            if timestamp.get("day") > 31:
                timestamp.update({"day": 1})
                timestamp.update({"month": timestamp.get("month") + 1})

            timestamp.update({"weekday": timestamp.get("weekday") + 1})
            if timestamp.get("weekday") > 6:
                timestamp.update({"weekday": 0})

def get_lockal_time(timezone=0, day_light_save=False):

    keys = ["year", "month", "day", "hour", "minute", "second", "weekday", "yearday"]
    timestamp = {key:value for key, value in zip(keys, time.localtime())}
    timestamp.update({"hour": timestamp.get("hour") + timezone})
    if (day_light_save):
        daylight_correct(timestamp)
    return timestamp
