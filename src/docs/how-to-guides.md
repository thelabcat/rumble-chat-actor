#How-To Guides

## My own personal setup
```
#!/usr/bin/env/python3
"""TheLabCat's Rumchat Actor setup

My RumChat Actor live stream configuration.
S.D.G"""

import rumchat_actor
from pygame import mixer #For a sound-making command I have

with open("cheeseburger.txt") as f:
    API_URL = f.read().strip()
with open("large_fries.txt") as f:
    USERNAME, PASSWORD = f.read().splitlines()[:2]

#Timed messages to send
TIMED_MESSAGES = [
    "There are lots of buttons under the video. Press some of them if you haven't already. :-)",
    "Want some subtitles for a video, but aren't satisfied with auto-generated? I sell handmade subtitles on Fiverr! https://www.fiverr.com/s/qDDKm9V",
    "I have chat commands. Send \"!help\" to see them, send \"!help commandName\" for more information on that command.",
    ]

mixer.init()

print("Setting up actor...")
actor = rumchat_actor.RumbleChatActor(
    api_url = API_URL,
    username = USERNAME,
    password = PASSWORD,
    )

#The Sisyphus command
sisyphus_music = mixer.Sound("../../../../Audio/sound_effects/sisyphus_short.mp3")
sisyphus_music.set_volume(0.15) #Just my arbitrary volume preference
def sisyphus(message, act_props, actor):
    """One must imagine a gamer happy

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor."""
    
    sisyphus_music.play()
    actor.send_message(f"@{message.user.username} One must imagine a gamer happy.")

actor.register_command(rumchat_actor.commands.ChatCommand(name = "sisyphus", actor = actor, cooldown = 120, target = sisyphus))

#TTS command
actor.register_command(rumchat_actor.commands.TTSCommand(actor = actor))

#Killswitch command
actor.register_command(rumchat_actor.commands.KillswitchCommand(actor = actor))

#Lurk command
actor.register_command(rumchat_actor.commands.MessageCommand(
    actor = actor,
    name = "lurk",
    text = "@{} is lurking in the chat",
    ))

#Clip command
clip_command = rumchat_actor.commands.ClipRecordingCommand(
    actor = actor,
    recording_load_path = "/home/wilbur/Videos/",
    clip_save_path = "/home/wilbur/Videos/stream_clips/",
    )

clip_uploader = rumchat_actor.misc.ClipUploader( #Auto-upload clips to my clips channel on Rumble
    actor,
    clip_command,
    channel_id = 6350778, #Marswide BGL Clips
    )

actor.register_command(clip_command)

#Help command
actor.register_command(rumchat_actor.commands.HelpCommand(actor = actor))

#Send timed messages
tmm = rumchat_actor.actions.TimedMessagesManager(actor, messages = TIMED_MESSAGES, delay = 300, in_between = 5)
actor.register_message_action(tmm.action)

#Follower / subscriber / etc. thanking system
rumchat_actor.misc.Thanker(actor)

#Run the bot continuously
print("Starting mainloop...")
actor.mainloop()
```

S.D.G.
