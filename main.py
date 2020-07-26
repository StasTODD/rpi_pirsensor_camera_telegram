#!/home/stastodd/projects/venv_37_telegram-bot/bin/python3.7
import sys
import traceback
from time import sleep
from datetime import datetime

import asyncio
import aiohttp
import yaml
from typing import List

import picamera
from gpiozero import MotionSensor, Buzzer


"""
This little program use 'gpiozero' library for work with GPIO pins. It's lib is very easy for work, but this lib isn't 
provide detail configurable properties. In the future, 'gpiozero' lib will be repplace to 'import RPi.GPIO as GPIO'. 
RPi.GPIO libraty can work with signal interruptions.
"""


def get_data_from_yaml(filename: str) -> dict:
    """
    Get data from yaml

    :param filename: 'filename.yaml'
    :return: {key: values}
    """
    with open(filename, "r") as f:
        return yaml.safe_load(f)


async def send_image_to_tbot(url: str, one_data: List[dict]) -> str:
    """
    Courutine with aiohttp lib for send request with image from RaspberryPI camera

    :param url: https://api.telegram.org/bot{tbot_api_token}/sendPhoto
    :param one_data: {"chat_id": "01010101010", "photo": b'x0x0x0x0'}
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=one_data) as response:
            return await response.text()


def create_photo(date=None) -> str:
    """
    :param date: date_time parameter. It's part of filename.jpg
    :return: /home/username/filename.jpg
    """
    if not date:
        now = datetime.now()
        now_string = now.strftime("%d-%m-%Y_%H:%M:%S")
    else:
        now_string = date.strftime("%d-%m-%Y_%H:%M:%S")

    imagename = f"{now_string}.jpg"

    camera = picamera.PiCamera()
    # TODO: Add more camera settings
    try:
        camera.capture(imagename)
    except Exception as all_exceptions:
        print("--- Start Exception Data:")
        traceback.print_exc(limit=2, file=sys.stdout)  # Exception detail via traceback
        print("--- End Exception Data:")
    finally:
        print("CleanUp")
        camera.close()
        print("End of program")
        return imagename


def main():
    # Fixme: Remove strings with BUZZER_PIN actions after correcting PIR-sensor position
    PIR_PIN = MotionSensor(4)
    BUZZER_PIN = Buzzer(17)

    tbot_data_all = get_data_from_yaml("data.yaml")

    tbot_api_token = tbot_data_all.get("api_token")
    admins_ids = tbot_data_all.get("admins_ids")
    if isinstance(admins_ids, list):
        admins_ids = [list(adm_id.values())[0] for adm_id in admins_ids]

    loop = asyncio.get_event_loop()

    # Need extended functional for set this option:
    access_flag = True

    # Url for send requests with photo:
    url = f"https://api.telegram.org/bot{tbot_api_token}/sendPhoto"

    try:
        while True:
            PIR_PIN.wait_for_motion()
            print("You moved")
            # BUZZER_PIN.on()
            sleep(1)
            # BUZZER_PIN.off()

            if access_flag:
                now = datetime.now()
                image = create_photo(date=now)
                with open(image, "rb") as b_image:
                    b_image = b_image.read()
                if isinstance(admins_ids, list):
                    all_data = [{"chat_id": str(adm), "photo": b_image} for adm in admins_ids]
                    coroutines = [send_image_to_tbot(url, one_data) for one_data in all_data]
                    loop.run_until_complete(asyncio.gather(*coroutines))

            PIR_PIN.wait_for_no_motion(timeout=10)
            # BUZZER_PIN.on()
            # sleep(0.15)
            # BUZZER_PIN.off()
            # sleep(0.2)
            # BUZZER_PIN.on()
            # sleep(0.15)
            # BUZZER_PIN.off()

    except KeyboardInterrupt:
        print("Exit pressed Ctrl+C")
    except Exception as all_exceptions:
        print("--- Start Exception Data:")
        traceback.print_exc(limit=2, file=sys.stdout)  # Exception detail via traceback
        print("--- End Exception Data:")


if __name__ == "__main__":
    main()
