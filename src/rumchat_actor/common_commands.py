#!/usr/bin/env python3
"""Rumble chat actor common commands

Derivative classes for common chat commands.
S.D.G."""

import os
import sys
import time
import threading
from cocorum.localvars import RUMBLE_BASE_URL, DEFAULT_TIMEOUT
from browsermobproxy import Server
from moviepy.editor import VideoFileClip, concatenate_videoclips
import requests
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
import talkey
from . import ChatCommand, ExclusiveChatCommand

OP_PATH = __file__[:__file__.rfind(os.sep)] #The path of the script
BROWSERMOB_EXE = 'browsermob-proxy' #The Browsermob Proxy executable
WAIT_FOR_LIVE_REFRESH_RATE = 10 #How often to refresh while waiting for a livestream to start
CLIP_FILENAME_EXTENSION = "mp4" #The filename extension for saved clips

class TTSCommand(ChatCommand):
    """Text-to-speech command"""
    def __init__(self, *args, name = "tts", voices = {}, **kwargs):
        """Pass the same args and kwargs as ChatCommand, plus:
    voices: Dict of voice : say(text) callable"""
        super().__init__(*args, name = name, **kwargs)
        self.voices = voices
        self.default_voice = talkey.Talkey()

    def speak(self, text, voice = None):
        """Speak text with voice"""
        if not voice:
            self.default_voice.say(text)

        #Voice was not actually in our list of voices
        elif voice not in self.voices:
            self.default_voice.say(voice + " " + text)

        else:
            self.voices[voice](text)

    def run(self, message):
        """Run the TTS"""
        segs = message.text.split()

        #No args for the tts command
        if len(segs) < 2:
            return

        #Only one word for tts
        if len(segs) == 2:
            self.speak(segs[1])
            return

        #A voice was selected
        if segs[1] in self.voices:
            self.speak(" ".join(segs[2:]), segs[1])
            return

        #No voice was selected
        self.speak(" ".join(segs[1:]))

class LurkCommand(ChatCommand):
    """A user is now lurking"""
    def __init__(self, actor, name = "lurk", text = "@{username} is now lurking. Enjoy!"):
        """actor: The Rumble chat actor host
    name = lurk: the command name
    text: A message to format with a username and post"""
        super().__init__(name = name, actor = actor)
        self.text = text

    def run(self, message):
        """Run the lurk"""
        self.actor.send_message(self.text.format(username = message.user.username))

class HelpCommand(ChatCommand):
    """List available commands"""
    def __init__(self, actor, name = "help"):
        """actor: The Rumble chat actor host
    name = help: the command name"""
        super().__init__(name = name, actor = actor)

    def run(self, message):
        """Run the help command"""
        self.actor.send_message("The following commands are registered: " + ", ".join(self.actor.chat_commands))

class KillswitchCommand(ExclusiveChatCommand):
    """A killswitch for Rumchat Actor if moderators or admin need to shut it down from the chat"""
    def __init__(self, actor, name = "killswitch", allowed_badges = ["moderator"]):
        """Pass the Rumchat Actor, the command name, and the badges allowed to use it"""
        super().__init__(name = name, actor = actor, allowed_badges = allowed_badges)

    def run(self, message):
        """Shut down Rumchat Actor"""
        try:
            self.actor.send_message("Shutting down.")
            self.actor.quit()
        finally:
            sys.exit()

class ClipCommand(ChatCommand):
    """Save clips of the livestream (alpha)"""
    def __init__(self, actor, name = "clip", default_duration = 60, max_duration = 120, ts_cahce_path = "." + os.sep, clip_save_path = "." + os.sep, browsermob_exe = BROWSERMOB_EXE):
        """actor: The Rumchat Actor
    name: The name of the command
    default_duration: How long the clip will last with no duration specified
    max_duration: How long the clip can possibly be (i.e. how much of the livestream to save)
    browsermob_exe: The path to the Browsermob Proxy executable"""
        super().__init__(name = name, actor = actor, cooldown = default_duration)
        self.default_duration = default_duration
        self.max_duration = max_duration
        self.ts_cache_path = ts_cahce_path #Where to cache the TS chunks from the stream
        self.clip_save_path = clip_save_path #Where to save the completed clips
        self.browsermob_exe = browsermob_exe
        self.streamer_main_page_url = self.actor.streamer_main_page_url #Make sure we have this before we try to start recording
        self.stream_is_live = False #Wether or not the stream is live, we find this later
        self.do_deletion = True #Wether or not to delete TS that are old, use to pause deletion while assembling clips
        self.ts_duration = 0 #The analyzed duration of a single TS clip, we find this later
        self.saved_ts = [] #Filenames of saved TS
        self.discarded_ts = [] #Filenames of TS that was saved then deleted
        self.recorder_thread = threading.Thread(target = self.record_loop, daemon = True)
        self.run_recorder = True
        self.recorder_thread.start()

    def record_loop(self):
        """Start and run the recorder system"""
        #Set up the proxy for network capture to find the m3u8 URL
        print("Starting proxy server")
        proxy_server = Server(BROWSERMOB_EXE)
        proxy_server.start()
        proxy = proxy_server.create_proxy()

        #Set Selenium to use the proxy
        print("Setting proxy options")
        webdriver.DesiredCapabilities.FIREFOX['proxy'] = {
        "httpProxy": f"localhost:{proxy.port}",
        #"ftpProxy": f"localhost:{proxy.port}",
        "sslProxy": f"localhost:{proxy.port}",
        "proxyType": "manual",
        }

        #Launch the browser
        print("Starting browser")
        browser = webdriver.Firefox()

        #Wait for the stream to go live, and get its URL in the meantime
        browser.get(self.streamer_main_page_url)
        stream_griditem = browser.find_element(By.XPATH, f"//div[@class='videostream thumbnail__grid--item'][@data-video-id='{self.actor.stream_id_b10}']")
        stream_url = RUMBLE_BASE_URL + "/" + stream_griditem.find_element(By.XPATH, ".//li[@class='videostream__link link']").get_attribute("href")
        print("Waiting for stream to go live before starting clip recorder...")
        while not self.stream_is_live:
            try:
                stream_griditem.find_element(By.CLASS_NAME, "videostream__badge.videostream__status.videostream__status--live")

            #Stream is not live yet
            except selenium.common.exceptions.NoSuchElementException:
                try:
                    stream_griditem.find_element(By.CLASS_NAME, "videostream__badge.videostream__status.videostream__status--upcoming")

                #Stream is not upcoming either
                except selenium.common.exceptions.NoSuchElementException:
                    print("Stream is not live or upcoming")
                    browser.quit()
                    proxy_server.stop()
                    return

                #Stream is still upcoming
                time.sleep(WAIT_FOR_LIVE_REFRESH_RATE)
                browser.refresh()

            #Stream is live
            else:
                self.stream_is_live = True

        #Watch the network traffic for the m3u8 URL
        print("Starting traffic recorder")
        proxy.new_har("rumble_traffic_capture", options={'captureHeaders': True, 'captureContent': True})
        print("Loading livestream viewing page")
        browser.get(stream_url)
        print("Waiting for m3u8 to go by. You may have to manually click play on the stream page.")
        m3u8_url = None
        while not m3u8_url:
            for ent in proxy.har['log']['entries']:
                #The entry was a GET request to https://hugh.cdn.rumble.cloud/live/ for an m3u8 file
                if ent["request"]["method"] == "GET" and ent["request"]["url"].startswith("https://hugh.cdn.rumble.cloud/live/") and ent["request"]["url"].endswith(".m3u8"):
                    m3u8_url = ent["request"]["url"]
                    break

        #We've got the m3u8 URL, TYJ! Clean up the browser and proxy.
        proxy_server.stop()
        browser.quit()
        print(m3u8_url)

        print("Starting tape...")
        #The TS files are at the same URL as the m3u8 playlist
        ts_url_start = m3u8_url[:m3u8_url.rfind("/") + 1]

        while self.run_recorder:
            #Get and parse the m3u8 playlist, filtering out TS chunks that we already have / had
            try:
                m3u8 = requests.get(m3u8_url, timeout = DEFAULT_TIMEOUT).content.decode()
            except AttributeError:
                print("Failed to get m3u8 playlist")
                continue
            ts_list = [line for line in m3u8.splitlines() if (not line.startswith("#")) and line not in self.saved_ts + self.discarded_ts]

            #Save the unsavedTS chunks to disk
            for ts in ts_list:
                with open(self.ts_cache_path + ts, "wb") as f:
                    try:
                        f.write(requests.get(ts_url_start + ts, timeout = DEFAULT_TIMEOUT).content)
                    except AttributeError: #The request failed and has no content
                        print("Failed to save ", ts)
                        continue
                self.saved_ts.append(ts)
                if not self.ts_duration: #We don't yet know how long a TS file is
                    self.ts_duration = VideoFileClip(self.ts_cache_path + ts).duration

            #We should be deleting old clips, and we have more than enough to fill the max duration
            while self.do_deletion and (len(self.saved_ts) - 1) * self.ts_duration > self.max_duration:
                os.system(f"rm '{self.ts_cache_path + self.saved_ts[0]}'")
                self.discarded_ts.append(self.saved_ts.pop(0))

            #Wait a moment before the next m3u8 download
            time.sleep(1)

    def run(self, message):
        """Make a clip"""
        #We don't yet know the length of a TS and so are not ready for clips
        if not self.ts_duration:
            self.actor.send_message(f"@{message.user.username} Not ready for clip saving yet.")
            return

        segs = message.split()
        #Only called clip, no arguments
        if len(segs) == 1:
            self.save_clip(self.default_duration)

        #Arguments were passed
        else:
            #The first argument is a number
            if segs[1].isnumeric():
                #Invalid length passed
                if not 0 < int(segs[1]) <= self.max_duration:
                    self.actor.send_message(f"@{message.user.username} Invalid clip length.")
                    return

                #Only length was specified
                if len(segs) == 2:
                    self.save_clip(int(segs[1]))

                #A name was also specified
                else:
                    self.save_clip(int(segs[1]), "_".join(segs[2:]))

            #The first argument is not a number, treat it as a filename
            else:
                self.save_clip(self.default_duration, "_".join(segs[2:]))

    def save_clip(self, duration, filename = None):
        """Save a clip with the given duration to the filename"""
        self.do_deletion = False #Pause TS deletion

        #Not enough TS for the full clip duration
        if len(self.saved_ts) * self.ts_duration < duration:
            print("Not enough TS to fulfil full duration")
            use_ts = self.saved_ts

        #We have enough TS
        else:
            use_ts = self.saved_ts[- duration // self.ts_duration - 1:]

        #No filename specified, construct from time values
        if not filename:
            t = time.time()
            filename = f"{round(t - self.ts_duration * len(use_ts))}-{round(t)}"

        #Load the TS chunks
        chunks = [VideoFileClip(self.ts_cache_path + ts) for ts in use_ts]

        #Concatenate the chunks into a clip
        clip = concatenate_videoclips(chunks)

        #Save
        clip.write_videofile(self.clip_save_path + filename + "." + CLIP_FILENAME_EXTENSION)

        self.do_deletion = True #Resume TS deletion

        self.actor.send_message(f"Clip {filename} saved, duration of {round(self.ts_duration * len(use_ts))} seconds.")
