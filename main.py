#!/home/stastodd/projects/rpi_pirsensor_camera_telegram/venv/bin/python

import sys
import traceback
from time import sleep
from datetime import datetime
import asyncio
import aiohttp
import yaml
from typing import Union
import sqlite3
import os
import picamera
from gpiozero import MotionSensor, Buzzer, OutputDevice


# TODO: need import this def from '../smart_house/db/create_db.py'
def create_connection(db_file: str) -> Union[type(sqlite3.connect), None]:
    """
    Create a database connection to the SQLite database specified by db_file

    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as er:
        print(er)
    return


def check_owner_status(smart_home_db_path="") -> int:
    """
    Connect to the smart_house_db.db and get data from table.

    :param smart_home_db_path: "/home/stastodd/projects/smart_house/db/smart_house_db.db"
    :return 1 | 0
    """
    if smart_home_db_path:
        conn = create_connection(smart_home_db_path)
    else:
        return 0

    query = "SELECT at_home from OwnerStatus;"
    data = 0
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute(query)
            data = c.fetchall()
            # db return data only in format: [(1,)]
            data = data[0][0]
        except sqlite3.Error as e:
            print(e)
    else:
        print("ERROR: Can't create the database connection")
    conn.close()
    return data


def get_data_from_yaml(filename: str) -> dict:
    """
    Get data from yaml

    :param filename: 'filename.yaml'
    :return: {key: values}
    """
    with open(filename, "r") as f:
        return yaml.safe_load(f)


async def send_image_to_tbot(url: str, one_data: dict) -> str:
    """
    Courutine with aiohttp lib for send request with image from RaspberryPI camera

    :param url: https://api.telegram.org/bot{tbot_api_token}/sendPhoto
    :param one_data: {"chat_id": "01010101010", "photo": b'x0x0x0x0'}
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=one_data) as response:
            return await response.text()


def create_photo(filename=None, path="") -> str:
    """
    :param filename: name of the photo
    :param path: "/home/stastodd/projects/rpi_pirsensor_camera_telegram/images"
    :return: "/home/stastodd/projects/rpi_pirsensor_camera_telegram/images/20-02-2023_02:33:03.jpg"
    """
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    if filename:
        if isinstance(filename, datetime):
            filename = filename.strftime("%Y-%m-%d_%H:%M:%S")
        else:
            filename = current_datetime

    if not path:
        imagename = f"images/{filename}.jpg"
    else:
        imagename = f"{path}/{filename}.jpg"

    camera = picamera.PiCamera()
    # Picture timestamp:
    camera.annotate_text_size = 40
    camera.annotate_text = " " * 42 + " ".join(current_datetime.split("_"))
    # TODO: Add more camera settings
    try:
        camera.capture(imagename)
    except Exception as all_exceptions:
        traceback.print_exc(limit=2, file=sys.stdout)  # Exception detail via traceback
    finally:
        camera.close()
        return imagename


def main(config_data):
    """
    :param config_data: {
        'admins_ids': [{'stastodd': 1}, {'username': 2}],
        'api_telegram_token': '3',
        'rpi_pirsensor_camera_telegram_params': {
            'enable_status': True,
            'save_photo_image_to_file': False,
            'photo_storage_path': '/home/stastodd/projects/rpi_pirsensor_camera_telegram/images'
            'motion_sensor_1_pin': 4,
            'pause_between_photo_sec': 10
            'use_extra_highlight': True,
            'extra_highlight_1_pin': 26,
            'use_buzzer_notification': False,
            'buzzer_notification_pin': 17,
            'use_smart_home_db': True,
            'smart_home_db': '/home/stastodd/projects/smart_house/db/smart_house_db.db'}}
    """
    # Get all config params:
    api_telegram_token = config_data.get("api_telegram_token")
    admins_ids = config_data.get("admins_ids", list())

    rpi_pirsensor_camera_telegram_data = config_data.get("rpi_pirsensor_camera_telegram_params", dict())

    # Config params:
    enable_status = rpi_pirsensor_camera_telegram_data.get("enable_status", True)
    save_photo_image_to_file = rpi_pirsensor_camera_telegram_data.get("save_photo_image_to_file", False)
    photo_storage_path = rpi_pirsensor_camera_telegram_data.get("photo_storage_path", str())
    motion_sensor_1_pin = rpi_pirsensor_camera_telegram_data.get("motion_sensor_1_pin")
    pause_between_photo_sec = rpi_pirsensor_camera_telegram_data.get("pause_between_photo_sec", 10)
    use_extra_highlight = rpi_pirsensor_camera_telegram_data.get("use_extra_highlight", False)
    extra_highlight_1_pin = rpi_pirsensor_camera_telegram_data.get("extra_highlight_1_pin")
    use_buzzer_notification = rpi_pirsensor_camera_telegram_data.get("use_buzzer_notification", False)
    buzzer_notification_pin = rpi_pirsensor_camera_telegram_data.get("buzzer_notification_pin")
    use_smart_home_db = rpi_pirsensor_camera_telegram_data.get("use_smart_home_db", False)
    smart_home_db_path = rpi_pirsensor_camera_telegram_data.get("smart_home_db_path", str())

    # Url for send requests with photomessage:
    url_photomessage = f"https://api.telegram.org/bot{api_telegram_token}/sendPhoto"

    if not enable_status:
        return

    loop = asyncio.get_event_loop()

    if isinstance(admins_ids, list):
        admins_ids = [list(adm_id.values())[0] for adm_id in admins_ids]

    # Extra highlight for noIR camera:
    highlight_1 = None
    if use_extra_highlight and extra_highlight_1_pin:
        highlight_1 = OutputDevice(extra_highlight_1_pin, active_high=True, initial_value=False)
    # Motion sensor:
    motion_sensor_1 = None
    if motion_sensor_1_pin:
        motion_sensor_1 = MotionSensor(motion_sensor_1_pin)
    # Buzzer speaker for sounds notifications:
    buzzer_device = None
    if use_buzzer_notification and buzzer_notification_pin:
        buzzer_device = Buzzer(buzzer_notification_pin)

    try:
        while True:
            # Waiting for motion from PIR sensor. When motion is detected, program goes further:
            if motion_sensor_1_pin:
                motion_sensor_1.wait_for_motion()

            sleep(1)

            make_photo_status = True
            # Check permission to use smart_home_db.db:
            if use_smart_home_db:
                if check_owner_status(smart_home_db_path=smart_home_db_path):
                    make_photo_status = False

            if make_photo_status:
                # Enable extra highlight:
                if use_extra_highlight:
                    highlight_1.on()
                    sleep(0.1)

                current_datetime = datetime.now()

                # Take a photo and transform it into binary file:
                image = create_photo(filename=current_datetime, path=photo_storage_path)
                with open(image, "rb") as b_image:
                    b_image = b_image.read()

                # Disable extra highlight:
                if use_extra_highlight:
                    highlight_1.off()

                # async photo sending to telegram bot:
                data_to_send_list = [{"chat_id": str(adm), "photo": b_image} for adm in admins_ids]
                coroutines = [send_image_to_tbot(url_photomessage, one_data) for one_data in data_to_send_list]
                loop.run_until_complete(asyncio.gather(*coroutines))

                # Remove photo image from storage:
                if not save_photo_image_to_file:
                    try:
                        os.remove(image)
                    except OSError:
                        print(f"FAIL: '{image}' file can't be deleted")

                # Pause between photo:
                motion_sensor_1.wait_for_no_motion(timeout=int(pause_between_photo_sec))
    except KeyboardInterrupt:
        print("Exit pressed Ctrl+C")
    except Exception as all_exceptions:
        print("--- Start Global Exception")
        traceback.print_exc(limit=2, file=sys.stdout)  # Exception detail via traceback
        print("--- End Global Exception")


if __name__ == "__main__":
    config_data = get_data_from_yaml("data.yaml")
    main(config_data)
