#!/usr/bin/env python3
"""Miscellanious classes and functions

Functions and classes that did not fit in another module
S.D.G."""

import threading
import time
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from .localvars import *

class ClipUploader():
    """Upload clips to Rumble automatically"""
    def __init__(self, actor, clip_command, **kwargs):
        """actor: The RumbleChatActor() instance
    clip_command: The clip command instance
    channel_id: The name or int ID of the channel to upload to, defaults to no channel (user page)
    profile_dir: The Firefox profile directory to use, defaults to burner profile
    username, password: The username and password to log in with, not needed if Firefox profile is signed in, otherwise defaults to manual login"""

        #Save actor
        self.actor = actor

        #Save clip command instance and assign ourself to it
        self.clip_command = clip_command
        self.clip_command.clip_uploader = self

        #Set browser profile directory if we have one
        options = webdriver.FirefoxOptions()
        if "profile_dir" in kwargs:
            options.add_argument("-profile")
            options.add_argument(kwargs["profile_dir"])

        #Start the driver
        self.driver = webdriver.Firefox(options)
        self.driver.minimize_window()

        #Load the upload page
        self.driver.get(RUMBLE_UPLOAD_URL)

        #Wait for sign in
        while "login" in self.driver.current_url:
            if "username" in kwargs:
                self.driver.find_element(By.ID, "login-username").send_keys(kwargs["username"] + Keys.RETURN)
            if "password" in kwargs:
                self.driver.find_element(By.ID, "login-password").send_keys(kwargs["password"] + Keys.RETURN)
            if "username" not in kwargs or "password" not in kwargs:
                input("Please log in, then press enter.")

        #Channel ID to use
        if "channel_id" in kwargs:
            self.channel_id = kwargs["channel_id"]
        else:
            self.channel_id = None

        #List of clip filenames to upload
        self.clips_to_upload = []

        #Thread to keep uploading clips as they arrive
        self.clip_uploader_thread = threading.Thread(target = self.clip_upload_loop, daemon = True)
        self.clip_uploader_thread.start()

    def upload_clip(self, filename):
        """Add the clip filename to the queue"""
        self.clips_to_upload.append(filename)

    def __upload_clip(self, filename):
        """Upload a clip to Rumble"""
        #Load the upload page
        self.driver.get(RUMBLE_UPLOAD_URL)

        #Select file and begin upload
        complete_filepath = self.clip_command.clip_save_path + filename + "." + CLIP_FILENAME_EXTENSION
        file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(complete_filepath)

        #Wait for upload to complete
        upload_progress_el = self.driver.find_element(By.CLASS_NAME, "green_percent")
        while (progress := int(upload_progress_el.get_attribute("style").split("width: ")[-1].split(";")[0].removesuffix("%"))) < 100:
            time.sleep(1)
            print("Upload progress:", progress)
        print("Upload complete")

        #Fill out video information
        title = f"stream {self.actor.stream_id_b10} clip {filename}"
        self.driver.find_element(By.ID, "title").send_keys(title)
        self.driver.find_element(By.ID, "description").send_keys("Automatic clip upload. Enjoy!")
        #driver.find_element(By.ID, "tags").send_keys(", ".join(TAGS_LIST))
        self.driver.find_element(By.NAME, "primary-category").send_keys(CLIP_CATEGORY_1 + Keys.RETURN)
        if CLIP_CATEGORY_2:
            self.driver.find_element(By.NAME, "secondary-category").send_keys(CLIP_CATEGORY_2 + Keys.RETURN)

        #Select channel
        channel_id_select = Select(self.driver.find_element(By.ID, "channelId"))
        try:
            if self.channel_id:
                if isinstance(self.channel_id, str):
                    channel_id_select.select_by_visible_text(self.channel_id)
                elif isinstance(self.channel_id, int):
                    channel_id_select.select_by_value(self.channel_id)
                else:
                    print("Invalid channel format")
            else:
                print("No channel ID specified. Defaulting to User ID.")
        except selenium.common.exceptions.NoSuchElementException:
            print("Channel ID specified did not exist. Defaulting to User ID.")

        #Set visibility
        vis_options_el = self.driver.find_element(By.ID, "visibility-options")
        vis_options_el.find_element(By.XPATH, "*/label[@for='visibility_unlisted']").click()

        #Submit form 1
        self.scroll_to_bottom()
        self.driver.find_element(By.ID, "submitForm").click()

        #Wait for rights checkbox, then click it
        WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//label[@for='crights']"))).click()

        #Click terms checkbox
        self.driver.find_element(By.XPATH, "//label[@for='cterms']").click()

        #Submit form 2
        self.scroll_to_bottom()
        self.driver.find_element(By.ID, "submitForm2").click()

        #Wait for form to submit
        WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//h3[text()='Video Upload Complete!']")))

        #Get link
        #video_link = self.driver.find_element(By.XPATH, f"//a[text()='View \"{TITLE}\"']").get_attribute("href")
        video_link = self.driver.find_element(By.ID, "direct").get_attribute("value")
        self.actor.send_message("Clip uploaded to " + video_link)
        print(f"Clip {filename} published.")

    def scroll_to_bottom(self):
        """Scroll all the way to the bottom of the page"""
        page = self.driver.find_element(By.TAG_NAME, "html")
        page.send_keys(Keys.END)
        #webdriver.ActionChains(self.driver).scroll_to_element(footer).perform()

    def clip_upload_loop(self):
        """Keep uploading clips while actor is alive"""
        while self.actor.keep_running:
            if self.clips_to_upload:
                self.__upload_clip(self.clips_to_upload.pop(0))
            time.sleep(1)
        self.driver.quit()

def is_staff(user):
    """Check if a user is channel staff"""
    return True in [badge in user.badges for badge in STAFF_BADGES]
