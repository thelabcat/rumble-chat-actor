#!/usr/bin/env python3
"""Chat commands

The base ChatCommand abstract class, and some commonly used derivatives
S.D.G."""

import glob
import os
import random
import shutil
import sys
import tempfile
import time
import threading
from tkinter import filedialog, Tk
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
try:
    import pyautogui
except Exception as e:
    print("Could not import PyAutoGUI:", e)
    pyautogui = None
import requests
import talkey
from . import utils, static

class ChatCommand():
    """Chat command abstract class"""
    def __init__(self, name, actor, cooldown = static.Message.send_cooldown, amount_cents = 0, exclusive = False, allowed_badges = ["subscriber"], free_badges = ["moderator"], target = None):
        """Instance a derivative of this object, then pass it to RumbleChatActor().register_command().
    name: The !name of the command
    actor: The RumleChatActor host object
    amount_cents: The minimum cost of the command
    exclusive: If this command can only be run by users with allowed badges
    allowed_badges: Badges that are allowed to run this command (if it is exclusive),
        "admin" is added internally.
    free_badges: Badges which if borne give the user free-of-charge command access
    target: The command function(message, actor) to call. Defaults to self.run"""
        assert " " not in name, "Name cannot contain spaces"
        self.name = name
        self.actor = actor
        assert cooldown >= static.Message.send_cooldown, \
            f"Cannot set a cooldown shorter than {static.Message.send_cooldown}"

        self.cooldown = cooldown
        self.amount_cents = amount_cents #Cost of the command
        self.exclusive = exclusive
        self.allowed_badges = ["admin"] + allowed_badges #Admin can always run any command
        self.free_badges = ["admin"] + free_badges #Admin always has free-of-charge usage
        self.last_use_time = 0 #Last time the command was called
        self.target = target
        self.__set_help_message = None

    @property
    def help_message(self):
        """The help message for this command"""
        if self.__set_help_message:
            return self.__set_help_message

    @help_message.setter
    def help_message(self, new):
        """Set the help message for this command externally"""
        self.__set_help_message = str(new)

    def call(self, message, act_props: dict):
        """The command was called"""
        #this command is exclusive, and the user does not have the required badge
        if self.exclusive and \
            not (True in [badge.slug in self.allowed_badges for badge in message.user.badges]):

            self.actor.send_message(f"@{message.user.username} That command is exclusive to: " +
                                    ", ".join(self.allowed_badges)
                                    )

            return

        #The command is still on cooldown
        if (curtime := time.time()) - self.last_use_time < self.cooldown:
            self.actor.send_message(
                f"@{message.user.username} That command is still on cooldown. " +
                f"Try again in {int(self.last_use_time + self.cooldown - curtime + 0.5)} seconds."
                )

            return

        #the user did not pay enough for the command and they do not have a free pass
        if message.rant_price_cents < self.amount_cents and \
            not (True in [badge.slug in self.free_badges for badge in message.user.badges]):

            self.actor.send_message("@" + message.user.username +
                                    f" That command costs ${self.amount_cents/100:.2f}."
                                    )
            return

        #the command was called successfully
        self.run(message, act_props)

        #Mark the last use time for cooldown
        self.last_use_time = time.time()

    def run(self, message, act_props: dict):
        """Dummy run method"""
        if self.target:
            self.target(message, self.actor)
            return

        #Run method was never defined
        self.actor.send_message("@" + message.user.username +
                                "Hello, this command never had a target defined. :-)"
                                )

class TTSCommand(ChatCommand):
    """Text-to-speech command"""
    def __init__(self, *args, name = "tts", no_double_sound = True, voices = {}, **kwargs):
        """Instance this object, then pass it to RumbleChatActor().register_command().
    actor: The RumleChatActor host object
    name: The !name of the command
    amount_cents: The minimum cost of the command. Defaults to free
    exclusive: If this command can only be run by users with allowed badges. Defaults to False
    allowed_badges: Badges that are allowed to run this command (if it is exclusive),
        defaults to ["moderator"], "admin" is added internally.
    free_badges: Badges which if borne give the user free-of-charge command access
    target: The command function(message, actor) to call. Defaults to self.run
    no_double_sound: Do not play if act_props["sound"] is True
    voices: Dict of voice_name : say(text) callable
    """
        super().__init__(*args, name = name, **kwargs)

        self.no_double_sound = no_double_sound
        self.voices = voices

        #Make sure we have a default voice
        if "default" not in self.voices:
            self.voices["default"] = talkey.Talkey().say

    @property
    def help_message(self):
        """The help message for this command"""
        return f"Speak your message{f" for ${self.amount_cents/100: .2%}" if self.amount_cents else ""}." + \
            f"Use {static.Message.command_prefix}{self.name} [voice] Your message. Available voices are: " + ", ".join(self.voices)

    @property
    def default_voice(self):
        """The default TTS voice as a say(text) callable"""
        return self.voices["default"]

    def speak(self, text, voice = None):
        """Speak text with voice"""
        if not voice:
            self.default_voice(text)

        #Voice was not actually in our list of voices
        elif voice not in self.voices:
            self.default_voice(voice + " " + text)

        else:
            self.voices[voice](text)

    def run(self, message, act_props: dict):
        """Run the TTS"""

        #Do not create more sound if a message action already made some
        if self.no_double_sound and act_props.get("sound"):
            return

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

class MessageCommand(ChatCommand):
    """Post a single message in chat"""
    def __init__(self, actor, name, text, help_message = None):
        """Instance this object, then pass it to RumbleChatActor().register_command().
    actor: The Rumble chat actor host
    name: the command name
    text: A message to format with the commander's username
    help_message: The message that the help command will display"""
        super().__init__(name = name, actor = actor)
        self.text = text
        if help_message:
            self.help_message = help_message

    def run(self, message, act_props: dict):
        """Run the lurk"""
        self.actor.send_message(self.text.format(message.user.username))

class HelpCommand(ChatCommand):
    """List available commands, or show help for a specific command"""
    def __init__(self, actor, name = "help"):
        """Instance this object, then pass it to RumbleChatActor().register_command().
    actor: The Rumble chat actor host
    name: the command name"""
        super().__init__(name = name, actor = actor)

    @property
    def help_message(self):
        """The help message for this command"""
        return "Run alone to list all available commands, or get " + \
            "help on a specific command with " + \
            f"{static.Message.command_prefix}{self.name} [command_name]"

    def run(self, message, act_props: dict):
        """Run the help command"""
        segs = message.text.split()

        #Command was run without arguments
        if len(segs) == 1:
            self.actor.send_message(
                "The following commands are registered: " + \
                ", ".join(self.actor.chat_commands)
            )

        #Command had one argument
        elif len(segs) == 2:
            #Argument is a valid command
            if segs[-1] in self.actor.chat_commands:
                hm = self.actor.chat_commands[segs[-1]].help_message
                if not hm:
                    hm = "No specific help for this command."
                self.actor.send_message(segs[-1] + " command: " + hm)

            #Argument is something else
            else:
                self.actor.send_message(f"Cannot provide help for '{segs[-1]}' as it is not a registered command.")

        #Command has more than one argument
        else:
            self.actor.send_message("Invalid number of arguments for help command.")

class KillswitchCommand(ChatCommand):
    """A killswitch for Rumchat Actor if moderators or admin need to shut it down from the chat"""
    def __init__(self, actor, name = "killswitch", allowed_badges = ["moderator"]):
        """Instance this object, then pass it to RumbleChatActor().register_command().
    actor: The RumleChatActor host object
    name: The !name of the command
    allowed_badges: Badges that are allowed to run this command"""
        super().__init__(name = name, actor = actor, exclusive = True, allowed_badges = allowed_badges)

    @property
    def help_message(self):
        """The help message for this command"""
        return "Shut down RumChat Actor."

    def run(self, message, act_props: dict):
        """Shut down Rumchat Actor"""
        try:
            self.actor.send_message("Shutting down.")
            self.actor.quit()
        finally:
            print("Killswitch thrown.")
            sys.exit()

class ClipDownloadingCommand(ChatCommand):
    """Save clips of the livestream by downloading stream chunks from Rumble, works remotely"""
    def __init__(self, actor, name = "clip", default_duration = 60, max_duration = 120, clip_save_path = "." + os.sep):
        """Instance this object, optionally pass it to a ClipUploader, then pass it to RumbleChatActor().register_command().
    actor: The Rumchat Actor
    name: The name of the command
    default_duration: How long the clip will last with no duration specified
    max_duration: How long the clip can possibly be (i.e. how much of the livestream to save)
    clip_save_path: Where to save clips to when they are made
    browsermob_exe: The path to the Browsermob Proxy executable"""
        super().__init__(name = name, actor = actor, cooldown = default_duration)
        self.default_duration = default_duration
        self.max_duration = max_duration
        self.clip_save_path = clip_save_path.removesuffix(os.sep) + os.sep #Where to save the completed clips
        self.ready_to_clip = False
        #self.streamer_main_page_url = self.actor.streamer_main_page_url #Make sure we have this before we try to start recording
        #self.stream_is_live = False #Wether or not the stream is live, we find this later
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
        self.save_format = static.Clip.save_extension #Format that clips are saved in. For ClipUploader
        self.clip_uploader = None #An object to upload the clips when they are complete
        self.recorder_thread = threading.Thread(target = self.record_loop, daemon = True)
        self.run_recorder = True
        self.recorder_thread.start()

    @property
    def help_message(self):
        """The help message for this command"""
        return f"Save a clip from the livestream. Use {static.Message.command_prefix}{self.name} [duration] [custom clip name]." + \
            f"Default duration is {self.default_duration}, max duration is {self.max_duration}."

    def get_ts_list(self, quality):
        """Download an m3u8 playlist and parse it for TS filenames"""
        assert self.ts_url_start and self.m3u8_filename, \
            "Must have the TS URL start and the m3u8 filename before this runs"
        m3u8 = requests.get(self.ts_url_start.format(quality = quality) + \
            self.m3u8_filename, timeout = static.REQUEST_TIMEOUT).text
        return [line for line in m3u8.splitlines() if not line.startswith("#")]

    def record_loop(self):
        """Start and run the recorder system"""

        #Get the base URL for the wualities listing
        m3u8_qualities_url = static.URI.m3u8_qualities_list.format(stream_id_b36 = self.actor.stream_id_b36)

        m3u8_qualities_raw = requests.get(m3u8_qualities_url, timeout = static.REQUEST_TIMEOUT).text

        m3u8_quality_urls_all = [line for line in m3u8_qualities_raw.splitlines() if not line.startswith("#")]
        ts_url_default = m3u8_quality_urls_all[-1]

        #Is this a DVR stream?
        self.is_dvr = ts_url_default.endswith("DVR.m3u8")

        self.ts_url_start = ts_url_default[:ts_url_default.rfind("/")] + "_{quality}/"

        self.m3u8_filename = ts_url_default[ts_url_default.rfind("/") + 1 ]

        self.get_quality_info()

        if self.is_dvr:
            self.use_quality = [q for q in static.Clip.Download.stream_qualities if q not in self.unavailable_qualities][-1]
            print("Not using TS cache for clips since stream is DVR. Ready to clip.")
            self.run_recorder = False
            self.ready_to_clip = True
            return

        #Find the best quality we can use
        for quality in static.Clip.Download.stream_qualities:
            if quality in self.unavailable_qualities:
                continue
            if self.average_ts_download_times[quality] > self.ts_durations[quality] / static.Clip.Download.speed_factor_req:
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
                    data = requests.get(self.ts_url_start.format(quality = self.use_quality) + ts_name, timeout = static.REQUEST_TIMEOUT).content
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
        assert self.ts_url_start, "Must have start of TS URL before this runs"
        for quality in static.Clip.Download.stream_qualities:
            download_times = []
            chunk_content = None #The content of a successful chunk download. used for duration checking
            for _ in range(static.Clip.Download.speed_test_iter):
                r1 = None
                try:
                    r1 = requests.get(self.ts_url_start.format(quality = quality) + self.m3u8_filename, timeout = static.REQUEST_TIMEOUT)
                except requests.exceptions.ReadTimeout:
                    print("Timeout for m3u8 playlist download")
                    download_times.append(static.REQUEST_TIMEOUT + 1)
                    continue

                if r1.status_code == 404:
                    print("404 for", self.ts_url_start.format(quality = quality) + self.m3u8_filename, "so assuming", quality, "quality is not available.")
                    self.unavailable_qualities.append(quality)
                    break

                #Download a chunk and time it
                ts_chunk_names = [l for l in r1.text if not l.startswith("#")]
                start_time = time.time()
                r2 = None
                try:
                    r2 = requests.get(self.ts_url_start.format(quality = quality) + ts_chunk_names[-1], timeout = static.REQUEST_TIMEOUT)
                except requests.exceptions.ReadTimeout:
                    print("Timeout for TS chunk download")
                    download_times.append(static.REQUEST_TIMEOUT + 1)
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

    def run(self, message, act_props: dict):
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

        #Avoid overwriting other clips
        safe_filename = utils.get_safe_filename(self.clip_save_path, filename)

        self.actor.send_message(f"Saving clip {safe_filename}, duration of {round(self.ts_durations[self.use_quality] * len(use_ts))} seconds.")
        saveclip_thread = threading.Thread(target = self.form_ts_into_clip, args = (safe_filename, use_ts), daemon = True)
        saveclip_thread.start()

    def form_ts_into_clip(self, filename, use_ts):
        """Do the actual TS [down]loading and processing, and save the video clip"""
        #Download the TS chunks if this is a DVR stream
        if self.is_dvr:
            print("Downloading TS for clip")
            tempfiles = []
            for ts_name in use_ts:
                try:
                    data = requests.get(self.ts_url_start.format(quality = self.use_quality) + ts_name, timeout = static.REQUEST_TIMEOUT).content
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
        complete_filepath = os.path.join(self.clip_save_path, filename + "." + static.Clip.save_extension)
        clip.write_videofile(
            complete_filepath,
            bitrate = static.Clip.Download.stream_qualities[self.use_quality],
            logger = None
        )

        self.running_clipsaves -= 1
        if self.running_clipsaves < 0:
            print("ERROR: Running clipsaves is now negative. Resetting it to zero, but this should not happen.")
            self.running_clipsaves = 0

        #We are responsible for DVR tempfile closing
        if self.is_dvr:
            for tf in tempfiles:
                tf.close()

        #Upload the clip
        if self.clip_uploader:
            self.clip_uploader.upload_clip(filename, complete_filepath)

        print("Complete")

class ClipRecordingCommand(ChatCommand):
    """Save clips of the livestream by duplicating then trimming an in-progress TS recording by OBS"""
    def __init__(self, actor, name = "clip", default_duration = 60, max_duration = 120, recording_load_path = ".", clip_save_path = "." + os.sep):
        """Instance this object, optionally pass it to a ClipUploader, then pass it to RumbleChatActor().register_command().
    actor: The Rumchat Actor
    name: The name of the command
    default_duration: How long the clip will last with no duration specified
    max_duration: How long the clip can possibly be
    recording_load_path: Where recordings from OBS are stored, used for filedialog init
    clip_save_path: Where to save clips to when they are made"""
        super().__init__(name = name, actor = actor, cooldown = default_duration)
        self.default_duration = default_duration
        self.max_duration = max_duration
        self.recording_load_path = recording_load_path.removesuffix(os.sep) #Where to first look for the OBS recording
        self.clip_save_path = clip_save_path.removesuffix(os.sep) + os.sep #Where to save the completed clips
        self.running_clipsaves = 0 #How many clip save operations are running
        self.__recording_filename = None #The filename of the running OBS recording, asked later
        print(self.recording_filename) #...now is later
        self.clip_uploader = None #An object to upload the clips when they are complete

    @property
    def help_message(self):
        """The help message for this command"""
        return f"Save a clip from the livestream. Use {static.Message.command_prefix}{self.name} [duration] [custom clip name]." + \
            f"Default duration is {self.default_duration}, max duration is {self.max_duration}."

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
                filetypes = static.Clip.Record.input_options,
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
        return static.Clip.Record.temp_copy_fn + "." + self.recording_container

    def run(self, message, act_props: dict):
        """Make a clip. TODO mostly identical to ClipDownloadingCommand().run()"""
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

        #Avoid overwriting other clips
        safe_filename = utils.get_safe_filename(self.clip_save_path, filename)

        #Report clip save
        self.actor.send_message(f"Saving clip {safe_filename}, duration of {duration} seconds.")

        #Run the clip save in a thread
        saveclip_thread = threading.Thread(target = self.form_recording_into_clip, args = (duration, safe_filename), daemon = True)
        saveclip_thread.start()

    def form_recording_into_clip(self, duration, filename):
        """Do the actual file operations to save a clip"""
        #Keep a counter of running clipsaves, may not be needed
        self.running_clipsaves += 1

        print("Making frozen copy of recording")
        shutil.copy(self.recording_filename, self.recording_copy_fn)
        print("Loading copy")
        recording = VideoFileClip(self.recording_copy_fn)
        print("Saving trimmed clip")
        complete_path = os.path.join(self.clip_save_path, filename + "." + static.Clip.save_extension)
        ffmpeg_extract_subclip(self.recording_copy_fn, max((recording.duration - duration, 0)), recording.duration, targetname = complete_path)
        print("Closing and deleting frozen copy")
        recording.close()
        os.system("rm " + self.recording_copy_fn)
        print("Done.")

        #Make note that the clipsave has finished
        self.running_clipsaves -= 1
        if self.running_clipsaves < 0:
            print("ERROR: Running clipsaves is now negative. Resetting it to zero, but this should not happen.")
            self.running_clipsaves = 0

        if self.clip_uploader:
            self.clip_uploader.upload_clip(filename, complete_path)

class ClipReplayBufferCommand(ChatCommand):
    """Save clips of the livestream by triggering OBS to save its replay buffer"""
    def __init__(self, actor, name = "clip", cooldown = 120, obs_hotkey = static.Clip.ReplayBuffer.obs_hotkey_default, clip_save_path = "." + os.sep, save_format = static.Clip.save_extension):
        """Instance this object, optionally pass it to a ClipUploader, then pass it to RumbleChatActor().register_command().
    actor: The Rumchat Actor
    name: The name of the command
    cooldown: Command cooldown
    obs_hotkey: List of keys to press at the same time to trigger OBS and save a replay buffer
    clip_save_path: Where replay buffer recordings from OBS are stored
    save_format: Format that replay buffers are saved in"""
        super().__init__(name = name, actor = actor, cooldown = cooldown)
        self.clip_save_path = clip_save_path.removesuffix(os.sep) + os.sep #Where replay buffer recordings from OBS are stored
        self.obs_hotkey = obs_hotkey
        self.save_format = save_format.removeprefix(".")
        self.__running_clipsaves = 0 #How many clip save operations are running
        self.clip_uploader = None #An object to upload the clips when they are complete

    @property
    def help_message(self):
        """The help message for this command"""
        return f"Save a clip from the livestream. Use {static.Message.command_prefix}{self.name} [custom clip name]." + \
            "Duration is defined by OBS replay buffer settings."

    @property
    def running_clipsaves(self):
        """How many clip save threads are currently running"""
        return self.__running_clipsaves

    @running_clipsaves.setter
    def running_clipsaves(self, new):
        """How many clip save threads are currently running"""
        assert int(new) == new, "Running clipsaves count must be an integer value"
        if new < 0:
            print("ERROR: Running clipsaves is now negative. Resetting it to zero, but this should not happen.")
            self.__running_clipsaves = 0
            return
        self.__running_clipsaves = new

    def run(self, message, act_props: dict):
        """Make a clip. TODO mostly identical to ClipDownloadingCommand().run()"""
        segs = message.text.split()
        #Only called clip, no arguments
        if len(segs) == 1:
            self.save_clip()

        #A name was passed
        else:
            self.save_clip("_".join(segs[1:]))

    def save_clip(self, filename = None):
        """Save a clip to the filename"""

        if filename:
            #Avoid overwriting other clips
            safe_filename = utils.get_safe_filename(self.clip_save_path, filename, extension = self.save_format)

            #Report clip save
            self.actor.send_message(f"Saving clip {safe_filename}.")

            filename = safe_filename

        else:
            #Report clip save
            self.actor.send_message("Saving clip with default filename.")

        #Run the clip save in a thread
        saveclip_thread = threading.Thread(target = self.save_buffer_as_clip, args = [filename], daemon = True)
        saveclip_thread.start()

    def save_buffer_as_clip(self, desired_filename):
        """Do the actual file operations to save a clip"""
        #Keep a counter of running clipsaves, may not be needed
        self.running_clipsaves += 1

        print("Pressing replay buffer save hotkey")
        for key in self.obs_hotkey:
            pyautogui.keyDown(key)

        #Time the clip was saved
        marktime = time.time()

        for key in self.obs_hotkey:
            pyautogui.keyUp(key)

        print("Egg timer for save to initialize")
        time.sleep(static.Clip.ReplayBuffer.save_start_delay)

        print("Locating saved replay buffer")
        search_string = f"{static.Clip.ReplayBuffer.save_name_format_notime}**.{self.save_format}"
        potential_files = glob.glob(search_string, root_dir = self.clip_save_path)
        potential_files.sort()

        if not potential_files:
            print(f"ERROR: No files matched search for '{search_string}' in {self.clip_save_path}")
            self.running_clipsaves -= 1
            return

        believed_filename = time.strftime(static.Clip.ReplayBuffer.save_name_format, time.localtime(marktime))
        if believed_filename in potential_files:
            print("Found exact match for", believed_filename)
            filename_wext = believed_filename
        else:
            print("Did not find exact match for", believed_filename)
            filename_wext = potential_files[-1]

        filename = filename_wext.removesuffix("." + self.save_format)
        complete_path = os.path.join(self.clip_save_path, filename_wext)

        print("Waiting for file to finish saving")
        old_size = 0
        while (new_size := os.path.getsize(complete_path)) != old_size:
            time.sleep(static.Clip.ReplayBuffer.size_check_delay)
            old_size = new_size

        if desired_filename:
            print(f"Renaming {filename} to {desired_filename}")
            old_complete_path = complete_path
            complete_path = os.path.join(self.clip_save_path, desired_filename + "." + self.save_format)
            shutil.move(old_complete_path, complete_path)
            filename = desired_filename
            del filename_wext #This is no longer valid, so remove from memory for debug

        #Make note that the clipsave has finished
        self.running_clipsaves -= 1

        if self.clip_uploader:
            self.clip_uploader.upload_clip(filename, complete_path)

class RaffleCommand(ChatCommand):
    """Create, enter, and draw from raffles"""
    def __init__(self, actor, name = "raffle"):
        """Instance this object, then pass it to RumbleChatActor().register_command().
    actor: The Rumchat Actor
    name: The name of the command"""
        super().__init__(name = name, actor = actor)

        #Username entries in the raffle
        self.entries = []

        #Winner of last raffle
        self.winner = None

        #Arguments we can take and associated methods
        self.operations = {
            "enter" : self.make_entry,
            "remove" : self.remove_entry,
            "count" : self.count_entries,
            "draw" : self.draw_entry,
            "winner" : self.report_winner,
            "reset" : self.reset,
            }

    @property
    def help_message(self):
        """The help message for this command"""
        return "Do raffles in the chat. " + \
            f"Use {static.Message.command_prefix}{self.name} [argument]. " + \
            f"Valid arguments are: {", ".join(self.operations)}"

    def run(self, message, act_props: dict):
        """Run the raffle command"""

        segs = message.text.split()
        #Only called command, no arguments
        if len(segs) == 1:
            #self.actor.send_message(self.help_message)
            print(f"{message.user.username} called the raffle command but without an argument. No action taken.")
            return

        #Valid argument
        if segs[1] in self.operations:
            self.operations[segs[1]](message)

        #Invalid argument
        else:
            print(f"{message.user.username} called the raffle command but with invalid argument(s): {", ".join(segs[1:])}. No action taken.")

    def make_entry(self, message):
        """An entry was made by the sender of the message"""
        if message.user.username in self.entries:
            print(f"{message.user.username} is already in the raffle.")
            return

        self.entries.append(message.user.username)
        print(f"{message.user.username} has entered the raffle.")

    def remove_entry(self, message):
        """Remove an entry from the raffle"""
        segs = message.text.split()
        #No username argument, the user wishes to remove themselves
        if len(segs) == 2:
            removal = message.user.username
        else:
            removal = segs[2].removesuffix("@")

        #Non-staff is trying to remove someone besides themselves
        if not utils.is_staff(message.user) and removal != message.user.username:
            #self.actor.send_message(f"@{message.user.username} You cannot remove another user from the raffle since you are not staff.")
            print(f"{message.user.username} Tried to remove {removal} from the raffle without the authority to do so.")
            return

        if removal not in self.entries:
            self.actor.send_message(f"@{message.user.username} The user {removal} was not entered in the raffle.")
            return

        self.entries.remove(removal)
        self.actor.send_message(f"@{message.user.username} The user {removal} was removed from the raffle.")

    def count_entries(self, message):
        """Report the number of entries made so far"""
        count = len(self.entries)
        self.actor.send_message(f"@{message.user.username} There {("are", "is")[count == 1]} currently {("no", count)[count != 0]} {("entries", "entry")[count == 1]} in the raffle.")

    def draw_entry(self, message):
        """Draw a winner"""
        if not utils.is_staff(message.user):
            print(f"{message.user.username} tried to draw a raffle winner without the authority to do so.")
            return

        if len(self.entries) < 2:
            self.actor.send_message(f"@{message.user.username} Cannot draw from raffle yet, need at least two entries.")
            return

        self.winner = random.choice(self.entries)
        self.report_winner(message)

    def report_winner(self, message):
        """Report the current winner"""
        if not self.winner:
            self.actor.send_message(f"@{message.user.username} There is no current winner.")
            return

        self.actor.send_message(f"@{message.user.username} The winner of the raffle is @{self.winner}")

    def reset(self, message):
        """Reset the raffle"""
        if not utils.is_staff(message.user):
            print(f"{message.user.username} tried to reset the raffle without the authority to do so.")
            return

        self.entries = []
        self.winner = None
        self.actor.send_message(f"@{message.user.username} Raffle reset.")
