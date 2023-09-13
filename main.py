import secrets
import time
import board
import busio
import adafruit_tsl2591
import adafruit_ahtx0
from adafruit_io.adafruit_io import IO_MQTT, AdafruitIO_RequestError
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import adafruit_requests
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import wifi
import socketpool
import ssl
import alarm
import microcontroller
import rtc
import struct


def main():
    my_rtc = rtc.RTC()

    sleep_memory = alarm.sleep_memory
    timeset = False

    i2c = busio.I2C(board.SCL1, board.SDA1)
    th = adafruit_ahtx0.AHTx0(i2c)
    sensor = adafruit_tsl2591.TSL2591(i2c)
    sensor.gain = adafruit_tsl2591.GAIN_LOW

    ADAFRUIT_IO_USERNAME = secrets['aio_username']
    ADAFRUIT_IO_KEY = secrets['aio_key']

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    io = IO_HTTP(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY, requests)

    #mqtt_client = MQTT.MQTT(
    #    broker="io.adafruit.com",
    #    username=secrets["aio_username"],
    #    password=secrets["aio_key"],
    #    socket_pool=pool,
    #    ssl_context=ssl.create_default_context(),
    #)

    #io = IO_MQTT(mqtt_client)

    try:
            # If Adafruit IO is not connected...
        if not io.is_connected:
            # Connect the client to the MQTT broker.
            print("Connecting to Adafruit IO...")
            io.connect()

    except Exception as e:  # pylint: disable=broad-except
        print("Failed to get or send data, or connect. Error:", e,
                "\nBoard will hard reset in 30 seconds.")
        time.sleep(30)
        microcontroller.reset()



    def message(client, topic, message):
        datetime = message
        print(message)
        timestamp_str = message

        # Split the timestamp string into components
        date_str, time_str = timestamp_str.split("T")
        time_str, milliseconds_str = time_str[:-1].split(".")

        year_str, month_str, day_str = date_str.split("-")
        hour_str, minute_str, second_str = time_str.split(":")

        # Convert components to integers
        year = int(year_str)
        month = int(month_str)
        day = int(day_str)
        hour = int(hour_str)
        minute = int(minute_str)
        second = int(second_str)

        # Create a time tuple (struct_time)
        timestamp_tuple = (year, month, day, hour, minute, second, 0, 0, 0)

        # Convert the time tuple to a time object
        timestamp_time = time.mktime(timestamp_tuple)
        new_timestamp = timestamp_time - (6 * 3600)

    # Convert the new timestamp back to a timestamp tuple
        new_time = time.localtime(new_timestamp)
        # Print the time object
        print("Converted Time:", new_time)
        my_rtc.datetime = new_time
        print(time.localtime())
        io.on_message = nothing
        timeset = True

    def nothing(client, topic, message):
        return
        

    def subscribe(mqtt_client, userdata, topic, granted_qos):
    # This method is called when the mqtt_client subscribes to a new feed.
        print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

    def unsubscribe(client, userdata, topic, pid):
        # This method is called when the client unsubscribes from a feed.
        print("Unsubscribed from {0} with PID {1}".format(topic, pid))

    io.on_subscribe = subscribe
    io.on_unsubscribe = unsubscribe
    io.on_message = message

    if my_rtc.datetime.tm_year == 2000:
        io.subscribe_to_time("ISO-8601")
        io.loop()

    global DLI

    DLI = 0

    def getConditions():
        lux = round(sensor.lux,2)
        temp = round(th.temperature * (9 / 5) + 32,2)
        humidity = round(th.relative_humidity,2)
        conditions = [("dfc.lux", lux), ("dfc.h", humidity), ("dfc.t", temp) , ("dfc.dli", round(DLI,4))]
        return conditions

    def send(conditions):
        try:
            start_time = time.monotonic()
            for feed_key, value in conditions:
                io.send_data(feed_key, value)  # Use HTTP send_data method
            end_time = time.monotonic()
            elapsed_time = end_time - start_time
            print(f"{conditions} sent in {elapsed_time} seconds")
        except Exception as e:
            print(f"Error sending data to Adafruit IO:{e}")


    def write_sleep(ts):
        ts_bytes = ts.to_bytes(4, 'big')
        dli_bytes = struct.pack('f', DLI)
        sleep_memory[0:8] = ts_bytes + dli_bytes
        # print(f"wrote dli {dli_bytes} and timestamp {ts_bytes} to sleep memory")


    def read_from_sleep():
        # Read timestamp from NVM (4 bytes)
        timestamp_bytes = bytearray(sleep_memory[0:4])
        timestamp = int.from_bytes(timestamp_bytes, 'big')
        # print(f"from memory: last time stamp {timestamp}, current timestamp {time.mktime(my_rtc.datetime)}")
        if timestamp == 0:
            timestamp = time.mktime(my_rtc.datetime)
        # print("sleep memory:", bytearray(sleep_memory[0:8]))
        # Read decimal number from NVM (4 bytes)
        decimal_bytes = bytearray(sleep_memory[4:8])
        DLI = struct.unpack('f', decimal_bytes)[0]  # Convert back to decimal
        # print(f"DLI from memory: {DLI}")
        
        return timestamp


    while True:
        ts1 = read_from_sleep()
        dt1 = time.localtime(ts1)
        start = time.monotonic()
        ppfd = sensor.lux * 0.038496
        if DLI > 0 and my_rtc.datetime.tm_hour == 0 and dt1.tm_hour == 24:
            DLI = 0

        ts2 = time.mktime(my_rtc.datetime)

        interval = abs(ts1-ts2)
        DLI += (ppfd * interval) / 10**6
        print(interval)
        # print(ppfd*interval, ppfd)
        # print(DLI)
        ts1 = ts2
        conditions = getConditions()
        send(conditions)
        write_sleep(ts1)
        end = time.monotonic()

        elapsed = abs(start-end)
        print(elapsed)

        if sensor.lux < 5:
            sleep = 15*60
        else:
            sleep = 5*60 - elapsed
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep)
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)