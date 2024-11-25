#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

import os
from cocorum.utils import *
#from js2py import eval_js
import selenium
from selenium.webdriver.common.by import By
from . import static

def is_staff(user):
    """Check if a user is channel staff"""
    return True in [badge in user.badges for badge in static.Moderation.staff_badges]

def close_premium_banner(driver):
    """If the premium banner is visible in a driver, close it"""
    print("Looking to close Premium banner")
    try:
        close_button = driver.find_element(
            By.CSS_SELECTOR,
            "[data-js='premium-popup__close-button'][aria-label='Close']",
        )
        print("Close button found.")

    except selenium.common.exceptions.NoSuchElementException:
        print("Close button not present, premium banner presumed already closed.")
        return

    print("Egg timer for premium banner to display")
    time.sleep(static.Driver.premium_banner_delay)

    try:
        close_button.click()
        print("Clicked close button. Egg timer for banner to hide")
        time.sleep(static.Driver.premium_banner_delay)
        print("Premium banner closed.")
    except selenium.common.exceptions.WebDriverException as e:
        print(e)
        print("Close button not clickable after wait, premium banner presumed already closed.")

def get_safe_filename(clip_save_path, filename, extension = static.Clip.save_extension):
    """Make a filename that will not overwrite other clips"""    
    increment = 0
    safe_filename = filename
    while os.path.exists(os.path.join(clip_save_path, safe_filename + "." + extension)):
        increment += 1
        safe_filename = filename + f"({increment})"
    return safe_filename

def calc_password_hashes(password, salts):
    """Hash a password given the salts using custom MD5 implementation"""
    md5 = MD5Ex()
    stretched1 = md5.hash_stretch(password, salts[0], 128)
    stretched2 = md5.hash_stretch(password, salts[2], 128)
    final_hash1 = md5.hash(stretched1 + salts[1])
    return [final_hash1, stretched2, salts[1]]

class MD5Ex:
    def __init__(self):
        self.hex = list("0123456789abcdef")

    def hash(self, message: str) -> str:
        if isinstance(message, str):
            message = message.encode('utf-8')
        return hashlib.md5(message).hexdigest()

    def hash_stretch(self, password: str, salt: str, iterations: int = 1024) -> str:
        message = (salt + password).encode('utf-8')
        current = self.hash(message)
        for _ in range(iterations):
            current = self.hash(current + password)
        return current
