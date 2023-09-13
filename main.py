import time
import board
import busio
import adafruit_tsl2591
import adafruit_ahtx0
import alarm
import microcontroller
import rtc
import struct
from setup import setup
import analogio



def main():
    vpin = analogio.AnalogIn(board.A2)
    print(get_voltage(vpin))
    io = setup()
    my_rtc = rtc.RTC()
    global DLI
    sleep_memory = alarm.sleep_memory
    timeset = False

    i2c = busio.I2C(board.SCL1, board.SDA1)
    th = adafruit_ahtx0.AHTx0(i2c)
    sensor = adafruit_tsl2591.TSL2591(i2c)
    sensor.gain = adafruit_tsl2591.GAIN_LOW


    def getConditions():
        global DLI
        v  = get_voltage(vpin)
        ts1 = getDLI()
        dt1 = time.localtime(ts1)
        ts2 = time.mktime(my_rtc.datetime)
        interval = abs(ts1-ts2)
        print(interval)
        lux = round(sensor.lux,2)
        ppfd = lux * 0.043
        print(f"prev DLI {DLI}")
        DLI += (ppfd * interval) / 10**6
        print(f"Calculated DLI {DLI}")
        ts1 = time.mktime(my_rtc.datetime)
        write_sleep(ts1)
        temp = round(th.temperature * (9 / 5) + 32,2)
        humidity = round(th.relative_humidity,2)
        conditions = [("dfc.lux", lux), ("dfc.h", humidity), ("dfc.t", temp) , ("dfc.dli", DLI), ("dfc.v", v)]
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

    def getDLI():
        global DLI
        prev = io.get_feed("dfc.dli")
        prev_time = prev["updated_at"]
        prev_time = conv_time(prev_time)
        last_value = float(prev["last_value"])

        if prev_time.tm_yday != my_rtc.datetime.tm_yday:
            DLI = 0
            print(f"Set DLI to 0: {DLI}")
            ts2 = time.mktime(my_rtc.datetime)
        else:
            ts1 = time.mktime(prev_time)
            ts2 = read_from_sleep(ts1)
            if ts1 == ts2:
                DLI = last_value
                return ts1
        return ts2
    
    def write_sleep(ts):
        global DLI
        ts_bytes = ts.to_bytes(4, 'big')
        dli_bytes = struct.pack('f', DLI)
        sleep_memory[0:8] = ts_bytes + dli_bytes
        print(f"wrote DLI to memory {DLI}")
        # print(f"wrote dli {dli_bytes} and timestamp {ts_bytes} to sleep memory")


    def read_from_sleep(ts):
        global DLI
        # Read timestamp from NVM (4 bytes)
        timestamp_bytes = bytearray(sleep_memory[0:4])
        timestamp = int.from_bytes(timestamp_bytes, 'big')
        # print(f"from memory: last time stamp {timestamp}, current timestamp {time.mktime(my_rtc.datetime)}")
        if timestamp == 0:
            timestamp = ts
        # print("sleep memory:", bytearray(sleep_memory[0:8]))
        # Read decimal number from NVM (4 bytes)
        decimal_bytes = bytearray(sleep_memory[4:8])
        
        DLI = struct.unpack('f', decimal_bytes)[0]  # Convert back to decimal
        print(f"DLI from memory: {DLI}")
        return timestamp
    
    
    while True:
        
        start = time.monotonic()
        conditions = getConditions()
        send(conditions)
        end = time.monotonic()
        elapsed = abs(start-end)
        print(f"Cycle took: {elapsed} seconds")

        if sensor.lux < 5:
            sleep = 15*60
        else:
            sleep = 5*60 - elapsed

        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep)
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)


def conv_time(sTime):
    timestamp_str = sTime
        
        # Split the timestamp string into components
    date_str, time_str = timestamp_str.split("T")
    time_str = time_str[:-1]
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
    timestamp_time = time.mktime(timestamp_tuple)
    new_timestamp = timestamp_time - (6 * 3600)

    # Convert the new timestamp back to a timestamp tuple
    ts = time.localtime(new_timestamp)
    return ts

def get_voltage(pin):
        return (pin.value / 65535) * 3.3
