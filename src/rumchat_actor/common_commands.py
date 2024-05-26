#!/usr/bin/env python3
"""Rumble chat actor common commands

Derivative classes for common chat commands.
S.D.G."""

import os
import shutil
import sys
import tempfile
import time
import threading
from tkinter import filedialog, Tk
from cocorum.localvars import RUMBLE_BASE_URL, DEFAULT_TIMEOUT
from browsermobproxy import Server
from moviepy.editor import VideoFileClip, concatenate_videoclips
import requests
# import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
import talkey
from . import ChatCommand

OP_PATH = __file__[:__file__.rfind(os.sep)] #The path of the script
BROWSERMOB_EXE = 'browsermob-proxy' #The Browsermob Proxy executable
WAIT_FOR_LIVE_REFRESH_RATE = 10 #How often to refresh while waiting for a livestream to start
CLIP_FILENAME_EXTENSION = "mp4" #The filename extension for saved clips
CLIP_BITRATE = "4.5M" #The bitrate to use when saving clips. Deprecating
STREAM_QUALITIES = {"360p" : "1.2M", "720p" : "2.8M", "1080p" : "4.5M"} #Valid resolutions of a livestream and the bitrates they use / should be saved with
DEFAULT_CLIP_BITRATE = STREAM_QUALITIES["1080p"] #The default save quality for clips from a local recording
VALID_CLIP_RECORDING_CONTAINERS = ["ts"] #Formats that the OBS recording can be in if recording-trimmed clips are to work
TEMP_RECORDING_COPY_FILENAME = ".temp_recording_copy"
NUM_TS_DOWNLOAD_TIME_CHECKS = 5 #How many times to test a TS chunk download to get its average download time
TS_DOWNLOAD_SPEEDFACTOR_REQUIREMENT = 2 #TS chunks must be able to download this many times faster than their duration to be usable in a cache. Cannot be less than 1

class TTSCommand(ChatCommand):
    """Text-to-speech command"""
    def __init__(self, *args, name = "tts", voices = {"default" : talkey.Talkey().say}, **kwargs):
        """Pass the same args and kwargs as ChatCommand, plus:
    voices: Dict of voice : say(text) callable"""
        super().__init__(*args, name = name, **kwargs)
        self.voices = voices

        #Get the default voice
        self.default_voice = voices["default"]

    def speak(self, text, voice = None):
        """Speak text with voice"""
        if not voice:
            self.default_voice(text)

        #Voice was not actually in our list of voices
        elif voice not in self.voices:
            self.default_voice(voice + " " + text)

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

class KillswitchCommand(ChatCommand):
    """A killswitch for Rumchat Actor if moderators or admin need to shut it down from the chat"""
    def __init__(self, actor, name = "killswitch", allowed_badges = ["moderator"]):
        """Pass the Rumchat Actor, the command name, and the badges allowed to use it"""
        super().__init__(name = name, actor = actor, exclusive = True, allowed_badges = allowed_badges)

    def run(self, message):
        """Shut down Rumchat Actor"""
        try:
            self.actor.send_message("Shutting down.")
            self.actor.quit()
        finally:
            print("Killswitch thrown.")
            sys.exit()

class ClipDownloaderCommand(ChatCommand):
    """Save clips of the livestream by downloading stream chunks from Rumble, works remotely"""
    def __init__(self, actor, name = "clip", default_duration = 60, max_duration = 120, clip_save_path = "." + os.sep, browsermob_exe = BROWSERMOB_EXE):
        """actor: The Rumchat Actor
    name: The name of the command
    default_duration: How long the clip will last with no duration specified
    max_duration: How long the clip can possibly be (i.e. how much of the livestream to save)
    clip_save_path: Where to save clips to when they are made
    browsermob_exe: The path to the Browsermob Proxy executable"""
        super().__init__(name = name, actor = actor, cooldown = default_duration)
        self.default_duration = default_duration
        self.max_duration = max_duration
        self.clip_save_path = clip_save_path #Where to save the completed clips
        self.browsermob_exe = browsermob_exe
        self.ready_to_clip = False
        self.streamer_main_page_url = self.actor.streamer_main_page_url #Make sure we have this before we try to start recording
        self.stream_is_live = False #Wether or not the stream is live, we find this later
        self.running_clipsaves = 0 #How many clip save operations are running
        self.unavailable_qualities = [] #Stream qualities that are not available (cause a 404)
        self.average_ts_download_times = {} #The average time it takes to download a TS chunk of a given stream quality
        self.ts_durations = {} #The duration of a TS chunk of a given stream quality
        self.is_dvr = False #Wether the stream is a DVR or not, detected later. No TS cache is needed if it is
        self.use_quality = None #The quality of stream to use, detected later, based on download speeds
        self.ts_url_start = "" #The start of the m3u8 and TS URLs, to be formatted with the selected quality, detected later
        self.m3u8_filename = "" #The filename of the m3u8 playlist, will be either chunklist.m3u8 or chunklist_DVR.m3u8, detected later
        self.saved_ts = {} #TS filenames : Tempfile objects containing TS chunks
        self.discarded_ts = [] #TS names that were saved then deleted
        self.recorder_thread = threading.Thread(target = self.record_loop, daemon = True)
        self.run_recorder = True
        self.recorder_thread.start()

    def get_ts_list(self, quality):
        """Download an m3u8 playlist and parse it for TS filenames"""
        assert self.ts_url_start and self.m3u8_filename, "Must have the TS URL start and the m3u8 filename before this runs"
        m3u8 = requests.get(self.ts_url_start.format(quality = quality) + self.m3u8_filename, timeout = DEFAULT_TIMEOUT).content.decode()
        return [line for line in m3u8.splitlines() if not line.startswith("#")]

    def record_loop(self):
        """Start and run the recorder system"""
        #Set up the proxy for network capture to find the m3u8 URL
        print("Starting proxy server")
        proxy_server = Server(self.browsermob_exe)
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
        print("Starting browser for clip command info gathering")
        browser = webdriver.Firefox()

        #Wait for the stream to go live, and get its URL in the meantime
        browser.get(self.streamer_main_page_url)
        stream_griditem = browser.find_element(By.XPATH,
                                                "//div[@class='videostream thumbnail__grid--item']" +
                                                f"[@data-video-id='{self.actor.stream_id_b10}']"
                                                )

        stream_url = RUMBLE_BASE_URL + "/" + stream_griditem.find_element(By.CLASS_NAME, 'videostream__link.link').get_attribute("href")
        print("Waiting for stream to go live before starting clip recorder...")
        while not self.stream_is_live:
            self.stream_is_live = bool(stream_griditem.find_elements(By.CLASS_NAME, "videostream__badge.videostream__status.videostream__status--live"))

            #Stream is now live, stop the loop by going back to the top to re-evaluate
            if self.stream_is_live:
                continue

            #Stream is upcoming
            if stream_griditem.find_elements(By.CLASS_NAME, "videostream__badge.videostream__status.videostream__status--upcoming"):
                # print("Stream is still upcoming.")
                pass

            #Stream is showing as DVR
            elif stream_griditem.find_elements(By.CLASS_NAME, "videostream__badge.videostream__status.videostream__status--dvr"):
                print("Stream is showing as DVR, but may be starting. See https://github.com/thelabcat/rumble-chat-actor/issues/5.")

            #Stream is not live or upcoming
            else:
                print("Stream is not live or upcoming! Critical error.")
                self.actor.quit()
                return

            #Stream is still upcoming
            time.sleep(WAIT_FOR_LIVE_REFRESH_RATE)
            browser.refresh()
            stream_griditem = browser.find_element(By.XPATH,
                                                    "//div[@class='videostream thumbnail__grid--item']" +
                                                    f"[@data-video-id='{self.actor.stream_id_b10}']"
                                                        )

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

        #Is this a DVR stream?
        self.is_dvr = m3u8_url.endswith("DVR.m3u8")

        #The TS files are at the same URL as the m3u8 playlist
        ts_url_start = m3u8_url[:m3u8_url.rfind("/") + 1]

        #Create an m3u8 URL formattable with the quality we are going to use
        self.ts_url_start = ts_url_start[:ts_url_start.rfind("_") + 1] + "{quality}" + "/"
        print(self.ts_url_start)
        self.m3u8_filename = m3u8_url[m3u8_url.rfind("/"):]

        self.get_quality_info()

        if self.is_dvr:
            self.use_quality = [q for q in STREAM_QUALITIES if q not in self.unavailable_qualities][-1]
            print("Not using TS cache for clips since stream is DVR. Ready to clip.")
            self.run_recorder = False
            self.ready_to_clip = True
            return

        #Find the best quality we can use
        for quality in STREAM_QUALITIES:
            if quality in self.unavailable_qualities:
                continue
            if self.average_ts_download_times[quality] > self.ts_durations[quality] / TS_DOWNLOAD_SPEEDFACTOR_REQUIREMENT:
                continue
            self.use_quality = quality

        if not self.use_quality:
            print("No available TS qualities for cache")
            return

        self.ready_to_clip = True
        print("Starting ring buffer TS cache...")
        while self.run_recorder:
            #Get the list of TS chunks, filtering out TS chunks that we already have / had
            try:
                new_ts_list = [ts for ts in self.get_ts_list(self.use_quality) if ts not in self.saved_ts.values() and ts not in self.discarded_ts]
            except (AttributeError, requests.exceptions.ReadTimeout):
                print("Failed to get m3u8 playlist")
                continue

            #We just started recording, only download the latest TS
            if not self.saved_ts:
                self.discarded_ts = new_ts_list[:-1]
                new_ts_list = new_ts_list[-1:]

            #Save the unsaved TS chunks to temporary files
            for ts_name in new_ts_list:
                try:
                    data = requests.get(ts_url_start.format(quality = self.use_quality) + ts_name, timeout = DEFAULT_TIMEOUT).content
                except (AttributeError, requests.exceptions.ReadTimeout): #The request failed or has no content
                    print("Failed to save ", ts_name)
                    continue
                f = tempfile.NamedTemporaryFile()
                f.write(data)
                f.file.close()
                self.saved_ts[ts_name] = f

            #We should be deleting old clips, and we have more than enough to fill the max duration
            while not self.running_clipsaves and (len(self.saved_ts) - 1) * self.ts_durations[self.use_quality] > self.max_duration:
                oldest_ts = list(self.saved_ts.keys())[0]
                self.saved_ts[oldest_ts].close() #close the tempfile
                del self.saved_ts[oldest_ts]
                self.discarded_ts.append(oldest_ts)

            #Wait a moment before the next m3u8 download
            time.sleep(1)

    def get_quality_info(self):
        """Get information on the stream quality options: Download time, TS length, availability"""
        print("Getting info on stream qualities")
        assert self.ts_url_start, "Must have the TS URL start before this runs"
        for quality in STREAM_QUALITIES:
            download_times = []
            chunk_content = None #The content of a successful chunk download. used for duration checking
            for _ in range(NUM_TS_DOWNLOAD_TIME_CHECKS):
                r1 = None
                try:
                    r1 = requests.get(self.ts_url_start.format(quality = quality) + self.m3u8_filename, timeout = DEFAULT_TIMEOUT)
                except requests.exceptions.ReadTimeout:
                    print("Timeout for m3u8 playlist download")
                    download_times.append(DEFAULT_TIMEOUT + 1)
                    continue

                if r1.status_code == 404:
                    print("404 for", self.ts_url_start.format(quality = quality) + self.m3u8_filename, "so assuming", quality, "quality is not available.")
                    self.unavailable_qualities.append(quality)
                    break

                #Download a chunk and time it
                ts_chunk_names = [l for l in r1.content.decode().splitlines() if not l.startswith("#")]
                start_time = time.time()
                r2 = None
                try:
                    r2 = requests.get(self.ts_url_start.format(quality = quality) + ts_chunk_names[-1], timeout = DEFAULT_TIMEOUT)
                except requests.exceptions.ReadTimeout:
                    print("Timeout for TS chunk download")
                    download_times.append(DEFAULT_TIMEOUT + 1)
                    continue
                if r2.status_code != 200 or not r2.content:
                    print("TS chunk download unsuccessful:", r2.status_code)
                    continue
                download_times.append(time.time() - start_time)
                chunk_content = r2.content

            if not download_times and quality not in self.unavailable_qualities:
                print("No successful chunk downloads for", quality, "so setting it as unavailable")
                self.unavailable_qualities.append(quality)
                continue

            #Get chunk duration
            ts = tempfile.NamedTemporaryFile()
            ts.write(chunk_content)
            ts.file.close()
            self.ts_durations[quality] = VideoFileClip(ts.name).duration
            ts.close()

            #Calculate average download time
            self.average_ts_download_times[quality] = sum(download_times) / len(download_times)

    def run(self, message):
        """Make a clip"""
        #We are not ready for clipping
        if not self.ready_to_clip or not (self.is_dvr or self.saved_ts):
            self.actor.send_message(f"@{message.user.username} Not ready for clip saving yet.")
            return

        segs = message.text.split()
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
                self.save_clip(self.default_duration, "_".join(segs[1:]))

    def save_clip(self, duration, filename = None):
        """Save a clip with the given duration to the filename"""
        self.running_clipsaves += 1

        #This is a DVR stream
        if self.is_dvr:
            available_chunks = self.get_ts_list(self.use_quality)

        #this is a passthrough stream
        else:
            available_chunks = list(self.saved_ts.keys())

        #Not enough TS for the full clip duration
        if len(available_chunks) * self.ts_durations[self.use_quality] < duration:
            print("Not enough TS to fulfil full duration")
            use_ts = available_chunks

        #We have enough TS
        else:
            use_ts = available_chunks[- int(duration / self.ts_durations[self.use_quality] + 0.5):]

        #No filename specified, construct from time values
        if not filename:
            t = time.time()
            filename = f"{round(t - self.ts_durations[self.use_quality] * len(use_ts))}-{round(t)}"

        self.actor.send_message(f"Saving clip {filename}, duration of {round(self.ts_durations[self.use_quality] * len(use_ts))} seconds.")
        saveclip_thread = threading.Thread(target = self.form_ts_into_clip, args = (filename, use_ts), daemon = True)
        saveclip_thread.start()

    def form_ts_into_clip(self, filename, use_ts):
        """Do the actual TS [down]loading and processing, and save the video clip"""
        #Download the TS chunks if this is a DVR stream
        if self.is_dvr:
            print("Downloading TS for clip")
            tempfiles = []
            for ts_name in use_ts:
                try:
                    data = requests.get(self.ts_url_start.format(quality = self.use_quality) + ts_name, timeout = DEFAULT_TIMEOUT).content
                    if not data:
                        raise ValueError
                except (ValueError, requests.exceptions.ReadTimeout): #The request failed or has no content
                    print("Failed to get", ts_name)
                    continue
                tf = tempfile.NamedTemporaryFile()
                tf.write(data)
                tf.file.close()
                tempfiles.append(tf)

        #Select the tempfiles from the TS cache
        else:
            tempfiles = [self.saved_ts[ts_name] for ts_name in use_ts]

        #Load the TS chunks
        chunks = [VideoFileClip(tf.name) for tf in tempfiles]

        #Concatenate the chunks into a clip
        clip = concatenate_videoclips(chunks)

        #Save
        print("Saving clip")
        clip.write_videofile(self.clip_save_path + filename + "." + CLIP_FILENAME_EXTENSION, bitrate = STREAM_QUALITIES[self.use_quality], logger = None)

        self.running_clipsaves -= 1
        if self.running_clipsaves < 0:
            print("ERROR: Running clipsaves is now negative. Resetting it to zero, but this should not happen.")
            self.running_clipsaves = 0

        #We are responsible for DVR tempfile closing
        if self.is_dvr:
            for tf in tempfiles:
                tf.close()
        print("Complete")

class ClipRecordingCommand(ChatCommand):
    """Save clips of the livestream by duplicating then trimming an in-progress TS recording by OBS"""
    def __init__(self, actor, name = "clip", default_duration = 60, max_duration = 120, recording_load_path = ".", clip_save_path = "." + os.sep):
        """actor: The Rumchat Actor
    name: The name of the command
    default_duration: How long the clip will last with no duration specified
    max_duration: How long the clip can possibly be
    recording_load_path: Where recordings from OBS are stored, used for filedialog init
    clip_save_path: Where to save clips to when they are made"""
        super().__init__(name = name, actor = actor, cooldown = default_duration)
        self.default_duration = default_duration
        self.max_duration = max_duration
        self.recording_load_path = recording_load_path
        self.clip_save_path = clip_save_path #Where to save the completed clips
        self.running_clipsaves = 0 #How many clip save operations are running
        self.__recording_filename = None #The filename of the running OBS recording, asked later
        print(self.recording_filename) #...now is later

    @property
    def recording_filename(self):
        """The filename of the running OBS recording"""
        #We do not know the filename yet
        while not self.__recording_filename:
            #Make and hide a background Tk window to allow filedialogs to appear
            root = Tk()
            root.withdraw()

            #Ask for the OBS recording in progress
            self.__recording_filename = filedialog.askopenfilename(
                title = "Select OBS recording in progress",
                initialdir = self.recording_load_path,
                filetypes=(("Freezable video files", ";".join("*." + container for container in VALID_CLIP_RECORDING_CONTAINERS)),
                                       ("All files", "*.*") ),
                )

            #Destroy the background window
            root.destroy()

        return self.__recording_filename

    @property
    def recording_container(self):
        """The container format of the recording"""
        return self.recording_filename.split(".")[-1]

    @property
    def recording_copy_fn(self):
        """The filename of the temporary recording copy"""
        return TEMP_RECORDING_COPY_FILENAME + "." + self.recording_container

    def run(self, message):
        """Make a clip. TODO mostly identical to ClipDownloaderCommand().run()"""
        segs = message.text.split()
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
                self.save_clip(self.default_duration, "_".join(segs[1:]))

    def save_clip(self, duration, filename = None):
        """Save a clip with the given duration to the filename"""
        #No filename specified, construct from time values
        if not filename:
            t = time.time()
            filename = f"{round(t - duration)}-{round(t)}"

        #Report clip save
        self.actor.send_message(f"Saving clip {filename}, duration of {duration} seconds.")

        #Run the clip save in a thread
        saveclip_thread = threading.Thread(target = self.form_recording_into_clip, args = (duration, filename), daemon = True)
        saveclip_thread.start()

    def form_recording_into_clip(self, duration, filename):
        """Do the actual file operations to save a clip"""
        #Keep a counter of running clipsaves, may not be needed
        self.running_clipsaves += 1

        print("Making frozen copy of recording")
        shutil.copy(self.recording_filename, self.recording_copy_fn)
        print("Loading copy")
        recording = VideoFileClip(self.recording_copy_fn)
        print("Trimming")
        clip = recording.subclip(max((recording.duration - duration, 0)), recording.duration)
        print("Saving clip")
        clip.write_videofile(self.clip_save_path + os.sep + filename + "." + CLIP_FILENAME_EXTENSION, logger = None)
        print("Closing and deleting frozen copy")
        recording.close()
        os.system("rm " + self.recording_copy_fn)
        print("Done.")

        #Make note that the clipsave has finished
        self.running_clipsaves -= 1
        if self.running_clipsaves < 0:
            print("ERROR: Running clipsaves is now negative. Resetting it to zero, but this should not happen.")
            self.running_clipsaves = 0
