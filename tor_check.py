from stem import Signal
from stem.control import Controller
import requests

def get_ip():
    proxies = {
        "http": "socks5h://127.0.0.1:9050",
        "https": "socks5h://127.0.0.1:9050",
    }

    print(
        requests.get(
            "https://api.ipify.org",
            proxies=proxies,
        ).text
    )

print("Before:")
get_ip()

with Controller.from_port(port=9051) as c:
    c.authenticate(password="mypassword123")
    c.signal(Signal.NEWNYM)

print("Waiting...")
import time
time.sleep(10)

print("After:")
get_ip()