#How-To Guides

## My own personal setup
```
#!/usr/bin/env/python3
"""TheLabCat's Rumchat Actor setup

My RumChat Actor live stream configuration.
S.D.G"""

import glob
import os.path as op
import subprocess
import rumchat_actor
import pyaudio  # For Piper TTS
from pygame import mixer  # For a sound-making command I have

with open("../../rumble_thelabcat_api_url_wkey.txt") as f:
    API_URL = f.read().strip()
with open("../../rumble_thelabcat_credentials.txt") as f:
    USERNAME, PASSWORD = f.read().splitlines()[:2]

# Timed messages to send
TIMED_MESSAGES = [
    "There are lots of buttons under the video. Press some of them if you haven't already. :-)",
    "Want some subtitles for a video, but aren't satisfied with auto-generated? I sell handmade subtitles on Fiverr! https://www.fiverr.com/s/qDDKm9V",
    "I have chat commands. Send \"!help\" to see them, send \"!help commandName\" for more information on that command.",
    ]

# Piper TTS settings
MODEL_PATH = "/home/wilbur/bin/pipertts/voices/"
PIPER_DEFAULT = "troutt"
PIPER_MODELS = {
    f.split("-")[1]: f
    for f in glob.glob("*.onnx", root_dir=MODEL_PATH)
    }

# Directory where my sound effects are
SOUND_EFFECTS_DIR = "/run/media/wilbur/WJHDD1/Audio/sound_effects"

mixer.init()
PA = pyaudio.PyAudio()

print("Setting up actor...")
actor = rumchat_actor.RumbleChatActor(
    api_url=API_URL,
    username=USERNAME,
    password=PASSWORD,
    channel="MarswideBGL"
    )

# The Sisyphus command
sisyphus_music = mixer.Sound(op.join(SOUND_EFFECTS_DIR, "sisyphus_short.mp3"))
sisyphus_music.set_volume(0.15)  # Just my arbitrary volume preference


def sisyphus(message, act_props, actor):
    """One must imagine a gamer happy

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor."""
    
    sisyphus_music.play()
    actor.send_message(f"@{message.user.username} One must imagine a gamer happy.")


actor.register_command(
    rumchat_actor.commands.ChatCommand(
        name="sisyphus",
        actor=actor,
        cooldown=120,
        target=sisyphus
        )
    )


# TTS command
def piper_tts(text, voice=PIPER_DEFAULT):
    """Synthesize text with Piper TTS"""
    assert voice in PIPER_MODELS, "Invalid voice selection"
    # The format here is always 8, but just to show how I got it, it is the
    # format for unsigned 16-bit (i.e. 2 byte, hence the 2).
    stream = PA.open(
        format=PA.get_format_from_width(2), channels=1, rate=22050, output=True
        )
    try:
        # Run Piper TTS via a command
        cp = subprocess.run(
            [
                "piper",
                "--model",
                op.join(MODEL_PATH, PIPER_MODELS[voice]),
                "--output-raw"
                ],

            # Send Piper the text to speak
            input=text.encode(),

            # Grab the output raw sound data
            capture_output=True
            )

        # Play the sound data
        stream.write(cp.stdout)

    # Make sure we always close the PyAudio stream
    finally:
        stream.close()


tts_command = rumchat_actor.commands.TTSCommand(
    actor=actor,
    voices={
        voice: eval(f"lambda text: piper_tts(text, \"{voice}\")")
        for voice in PIPER_MODELS
        }
    )

tts_command.voices["default"] = lambda text: piper_tts(text, PIPER_DEFAULT)

actor.register_command(tts_command)

# Killswitch command
actor.register_command(rumchat_actor.commands.KillswitchCommand(actor=actor))

# Lurk command
actor.register_command(rumchat_actor.commands.MessageCommand(
    actor=actor,
    name="lurk",
    text="@{} is lurking in the chat",
    ))

# Clip command
clip_command = rumchat_actor.commands.ClipRecordingCommand(
    actor=actor,
    recording_load_path="/home/wilbur/Videos/",
    clip_save_path="/home/wilbur/Videos/stream_clips/",
    )

# Auto-upload clips to my clips channel on Rumble
clip_uploader = rumchat_actor.misc.ClipUploader(
    actor,
    clip_command,
    channel_id=6350778,  # Marswide BGL Clips
    )

actor.register_command(clip_command)

# Help command
actor.register_command(rumchat_actor.commands.HelpCommand(actor=actor))

# Send timed messages
tmm = rumchat_actor.actions.TimedMessagesManager(
    actor, messages=TIMED_MESSAGES, delay=300, in_between=5
    )
actor.register_message_action(tmm.action)

# Follower / subscriber / etc. thanking system
thanker = rumchat_actor.actions.Thanker(actor)
actor.register_message_action(thanker)

# Message blipper
actor.register_message_action(
    rumchat_actor.actions.ChatBlipper(op.join(SOUND_EFFECTS_DIR, "pop.wav"))
    )


# User announcer
# Announce Izsak's arrival
izsak_intro = mixer.Sound(op.join(SOUND_EFFECTS_DIR, "izsak_intro.mp3"))


def announce_izsak(message, act_props, actor):
    """Announce when Izsak arrives in the chat

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of recorded properties from running this action."""

    izsak_intro.play()
    return {"sound": True}


announcer = rumchat_actor.actions.UserAnnouncer(
    special_announcers={
        "Jorash": announce_izsak,
        }
    )


actor.register_message_action(announcer)

# Run the bot continuously
print("Starting mainloop...")
actor.mainloop()
PA.terminate()
```

S.D.G.
