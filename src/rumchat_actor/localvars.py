#!/usr/bin/env python3
"""Local variables

Absolute variable definitions not uinque to scripts.
S.D.G.
"""

from cocorum.localvars import RUMBLE_BASE_URL

#How long to wait maximum for a condition to be true in the browser
BROWSER_WAIT_TIMEOUT = 30

#How long to wait between sending messages
SEND_MESSAGE_COOLDOWN = 3

#Popout chat url. Format with stream_id_b10
CHAT_URL = RUMBLE_BASE_URL + "/chat/popup/{stream_id_b10}"

#Rumble user URL. Format with username
USER_URL = RUMBLE_BASE_URL + "/user/{username}"

#Rumble channel URL. Format with channel_name
CHANNEL_URL = RUMBLE_BASE_URL + "/c/{channel_name}"

#Maximum chat message length
MAX_MESSAGE_LEN = 200

#Message split across multiple lines must not be longer than this
MAX_MULTIMESSAGE_LEN = 1000

#Prefix to all actor messages
BOT_MESSAGE_PREFIX = "🤖: "

#How commands always start
COMMAND_PREFIX = "!"

#Levels of mute to discipline a user with, keyed to their HTML menu button class names
MUTE_LEVELS = {
    "5" : "cmi js-btn-mute-current-5",
    "stream" : "cmi js-btn-mute-current",
    "forever" : "cmi js-btn-mute-for-account",
    }

#Badges of staff chatters
STAFF_BADGES = ["admin", "moderator"]

#default path to a Browsermob Proxy executable
BROWSERMOB_EXE = 'browsermob-proxy'

#How often to refresh while waiting for a webpage condition to be met
WAIT_FOR_PAGE_CONDITION_REFRESH_RATE = 10

#The filename extension i.e. video container to use for saved clips
CLIP_FILENAME_EXTENSION = "mp4"

#Valid resolutions of a livestream and the bitrates they use / should be saved with
STREAM_QUALITIES = {"360p" : "1.2M", "720p" : "2.8M", "1080p" : "4.5M"}

#The default save quality for clips from a local recording
DEFAULT_CLIP_BITRATE = STREAM_QUALITIES["1080p"]

#Formats that the OBS recording can be in if recording-trimmed clips are to work
#Must be moviepy loadable even if copied while being recorded to
VALID_CLIP_RECORDING_CONTAINERS = ["ts"]

#Filename of the temporary copy of an OBS recording, used for ClipRecordingCommand
TEMP_RECORDING_COPY_FILENAME = ".temp_recording_copy"

#How many times to test a TS chunk download to get its average download time
NUM_TS_DOWNLOAD_TIME_CHECKS = 5

#TS chunks must be able to download this many times faster than their duration
#to be usable in a cache. Cannot be less than 1
TS_DOWNLOAD_SPEEDFACTOR_REQUIREMENT = 2

#LLM system message to moderate messages with
LLM_MODERATOR_SYS_MESSAGE = "Analyze the following chat messages for appropriate-ness. Respond with either a 0 or a 1: If a message is appropriate for PG-13 SFW and not spam, or you are not sure, respond with a 1. If it is not appropriate for PG-13 or is NSFW or is spam, respond with a 0. You can only respond with these two values. Do not respond with commentary."

#URL of upload page at Rumble
RUMBLE_UPLOAD_URL = RUMBLE_BASE_URL + "/upload.php"

#Default primary and secondary category of clips
CLIP_CATEGORY_1 = "Entertainment"
CLIP_CATEGORY_2 = None

#OLLaMa model to use for auto-modetation
OLLAMA_MODEL = "llama3.1"
