#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

#from os.path import join as pjoin
#from pathlib import Path
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
        close_button = driver.find_element(By.CSS_SELECTOR, "[data-js='premium-popup__close-button'][aria-label='Close']")
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

# def calc_password_hashes(password, salts):
#     """Hash a password given the salts"""
#     with open(pjoin(Path(__file__).parent, pjoin("dom_scripts", "md5Ex.js")), 'r') as f:
#         js = f.read()
#
#     return eval_js(js)(password, salts)
