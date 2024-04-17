#!/usr/bin/env python3
#Rumble Chat Bot Module
#S.D.G.

#This program works with a popout chat window in fullscreen

import pyautogui
import requests
#import webbrowser
import time
import os
import calendar
from PIL import Image
import pytesseract as ocr

try: 
    import tomllib
    CONFIG_PATH = "config.toml"
    with open(CONFIG_PATH, "rb") as f:
        CONFIG = tomllib.load(f)

except (ImportError, FileNotFoundError):
    from config import CONFIG

with open(CONFIG["apiURLFile"]) as f:
    API_URL = f.read().strip()

def open_url(url):
    """Open a URL in the browser"""
    os.popen("midori " + url)

def map_range(val, oldmin, oldmax, newmin, newmax):
    """Map a value to a new range from an old one"""
    return (val - oldmin) / (oldmax - oldmin) * (newmax - newmin) + newmin

def clip(val, low, high):
    """Clip a value to a minimum and a maximum"""
    if val < low:
        return low
    if val > high:
        return high
    return val

class ChatBot(object):
    def __init__(self, stream_id = None, chat_id = None):
        """Open a chat popout window and bot it"""
        if stream_id: #Stream ID as provided by the API
            self.chat_id = int(stream_id, len(CONFIG["streamIDBase"]))
            if chat_id and self.chat_id != chat_id:
                raise ValueError("Stream ID and chat ID were both specified but they do not match")
        elif chat_id: #Chat ID as it appears in the popout URL
            self.chat_id = chat_id
        else:
            raise ValueError("Must specify either stream_id or chat_id")

        self.__stream_id = stream_id
        self.last_message_check_time = 0

    @property
    def stream_id(self):
        """If we don't know our stream ID, figure it out from the chat ID"""
        if self.__stream_id:
            return self.__stream_id

        print("Converting chat ID to stream ID")
        stream_id = ""
        val = self.chat_id
        base_len = len(CONFIG["streamIDBase"])
        while val:
            stream_id = CONFIG["streamIDBase"][val % base_len] + stream_id
            val //= base_len
        self.__stream_id = stream_id
        return stream_id

    def open_chat_browser(self, dark_mode = None, maximize = False):
        """Open the chat in a browser and get information on buttons and such"""
        print("Opening browser")
        open_url("https://rumble.com/chat/popup/%i" % self.chat_id)
        time.sleep(CONFIG["browserLaunchDelay"])
        
        if maximize: #Find and click the maximize button
            try:
                print("Searching for maximize button")
                pyautogui.click(pyautogui.locateCenterOnScreen("browserMaximizeButton.png"))
                time.sleep(CONFIG["browserMaximizeDelay"])
            except pyautogui.ImageNotFoundException:
                print("Could not find browser maximize button. Is the image correct?")
                raise

        ref_screenshot = pyautogui.screenshot().convert("HSV")
        
        if dark_mode == None: #Guess wether site is in dark mode based on average light level
            print("Guessing dark mode")
            self.dark_mode = ref_screenshot.resize((1, 1), resample = Image.Resampling.BILINEAR).getpixel((0, 0))[-1] < (CONFIG["lightLevel"] + CONFIG["darkLevel"]) / 2
        else:
            self.dark_mode = dark_mode
        print("Dark mode?", self.dark_mode)
        
        #Get positions to click before typing a message
        try:
            print("Searching for message field on screen")
            self.message_field_pos = self.find_message_field(ref_screenshot)
        except pyautogui.ImageNotFoundException:
            print("Failed to find necessary UI elements on screen. Are you signed in?")
            raise

    def find_message_field(self, screenshot):
        """Locate the message field on screen"""
        print("Contrasting image for better OCR")
        contrasted = self.contrast_value(screenshot, contrast_range = CONFIG[("lightValueRange", "darkValueRange")[int(self.dark_mode)]]).convert("RGB")
        #contrasted.save("test.png")

        print("OCRing and parsing")
        text_data = self.parse_ocr_data(ocr.image_to_data(contrasted))
        raw_text = " ".join([td["text"] for td in text_data])
        if CONFIG["messageFieldText"] not in raw_text:
            raise ValueError("Could not find message field text on screen.")

        #Only care about relevant words
        print("Filtering to relevant words")
        filtered_td = []
        search_words = CONFIG["messageFieldText"].split(" ")
        for row in text_data:
            if row["text"] in search_words:
                filtered_td.append(row)
        print(len(filtered_td), "words left")

        print("Finding last occurrence of", CONFIG["messageFieldText"])
        #Put the last blocks first, but otherwise keep the order
        filtered_td.reverse()
        filtered_td.sort(key = lambda x: x["block_num"])
        filtered_td.reverse()
        print(filtered_td)

        #Find the words in consecutive order
        cont = 0
        block_num = 0
        for i in range(len(filtered_td)):
            row = filtered_td[i]
            if row["block_num"] != block_num: #If we've moved on to a new text block, start over
                block_num = row["block_num"]
                cont = 0
            if search_words[cont] == row["text"]: #The next word up still matched
                cont += 1
                if cont == len(search_words): #All words were found
                    break
            elif cont != 0: #We were starting to match, but did not find all the words
                cont = 0 #Start over

        start_word = filtered_td[i - cont + 1] #Get the first word in the matchup
        print("Found:\n", start_word)
        return int(start_word["left"] + start_word["width"] / 2), int(start_word["top"] + start_word["height"] / 2)

    def parse_ocr_data(self, ocr_data):
        """Turn the human-readable OCR data table from pytesseract into a computer-readable list"""
        lines = ocr_data.splitlines()
        keys = lines.pop(0).split("\t") #The first line is the header of keys
        rows = []
        for line in lines:
            linesegs = line.split("\t")
            row = {}
            for i in range(len(keys)):
                try:
                    if keys[i] == "text":
                        row[keys[i]] = linesegs[i]
                    else:
                        row[keys[i]] = float(linesegs[i])
                except IndexError:
                    row[keys[i]] = "" #No value for this row under this column
            rows.append(row)
        return rows

    def contrast_value(self, img, contrast_range):
        """Increase the value contrast of an image so that the specified range occupies 0-255 (currently converts the image to B-W)"""
        for x in range(img.size[0]):
            for y in range(img.size[1]):
                img.putpixel((x, y), (0, 0, int(
                    clip(
                        map_range(img.getpixel((x, y))[2], contrast_range[0], contrast_range[1], 0, 255), 0, 255))))
        return img

    def send_message(self, string):
        """Type a message and send it"""
        if "\n" in string:
            raise ValueError("Messages cannot contain newlines.")

        pyautogui.click(self.message_field_pos)
        pyautogui.typewrite(string.strip() + "\n")

    def get_livestream_json(self, json):
        """Select the specific livestream the poll is supposed to run on from the API json"""
        if len(json["livestreams"]) == 0:
            raise ValueError("No livestreams found.")
            return

        for possible in json["livestreams"]:
            if possible["id"] == self.stream_id:
                return possible

        #We went through all the livestreams, and none of them matched
        raise ValueError("No livestream matches the specified ID")

    def parse_message_time(self, message):
        """Parse a message's UTC timestamp to seconds since epoch"""
        return calendar.timegm(time.strptime(message["created_on"], CONFIG["rumbleTimestampFormat"]))

    def check_messages(self, ignore_own = True):
        """Check for messages that are newer than the last check time"""
        new_messages = []
        response = requests.get(API_URL, headers = CONFIG["APIHeaders"])
        if response.status_code != 200:
            print("Error: Could not check for messages.", response)
            return new_messages

        json = response.json()

        for message in self.get_livestream_json(json)["chat"]["recent_messages"]:
            if (not ignore_own or message["username"] != json["username"]) and self.parse_message_time(message) > self.last_message_check_time: #If the message is new, and isn't ours or we are told to not ignore ours...
                new_messages.append(message)

        self.last_message_check_time = json["now"] #Go by the server timestamp on the JSON, in case there was some delay
        return new_messages

    def close_window(self):
        """Close the top window, hopefully it is the chat browser"""
        with pyautogui.hold("alt"):
            pyautogui.press("F4")

if __name__ == "__main__":
    print("Rumble Chat Bot, not meant to be run independently.")
