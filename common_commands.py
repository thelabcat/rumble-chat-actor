#!/usr/bin/env python3
"""Rumble chat actor common commands

Derivative classes for common chat commands.
S.D.G."""

from . import ChatCommand, ExclusiveChatCommand
import talkey

class TTSCommand(ChatCommand):
    def __init__(self, *args, name = "tts", voices = {}, **kwargs):
        """Pass the same args and kwargs as ChatCommand, plus:
    voices: Dict of voice : say(text) callable"""
        super().__init__(*args, name = name, **kwargs)
        self.voices = voices
        self.default_voice = talkey.Takley()

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
