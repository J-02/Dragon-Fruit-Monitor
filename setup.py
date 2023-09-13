import socketpool
import ssl
import wifi
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from secrets import secrets
import rtc
import time
import microcontroller

def setup(IO = True):
    my_rtc = rtc.RTC()
    ADAFRUIT_IO_USERNAME = secrets['aio_username']
    ADAFRUIT_IO_KEY = secrets['aio_key']
    """
    Sets up and returns the Adafruit IO HTTP object.
    """
    try:
        # Create a socket pool
        pool = socketpool.SocketPool(wifi.radio)

        # Create a requests session
        requests = adafruit_requests.Session(pool, ssl.create_default_context())

        if IO:
                
            # Initialize Adafruit IO HTTP API object
            io = IO_HTTP(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY, requests)

            print("Connected to Adafruit IO!")
            current_time = io.receive_time()
            my_rtc.datetime = current_time
            print(f"Current Date and Time: {my_rtc.datetime.tm_year}-{my_rtc.datetime.tm_mon:02d}-{my_rtc.datetime.tm_mday:02d} {my_rtc.datetime.tm_hour:02d}:{my_rtc.datetime.tm_min:02d}:{my_rtc.datetime.tm_sec:02d}")
        
            return io

        else:    
            return requests

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Failed to get or send data, or connect. Error:", e,
        "\nBoard will hard reset in 30 seconds.")
        time.sleep(30)
        microcontroller.reset()
        return None