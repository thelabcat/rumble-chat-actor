#!/usr/bin/env python3
"""Common message actions

Actions commonly run on chat messages
S.D.G"""

# import socket
import threading
import time
from pygame import mixer
import talkey
from . import static

try:
    import ollama
    OLLAMA_IMPORTED = True
except ModuleNotFoundError:
    OLLAMA_IMPORTED = False

def ollama_message_moderate(message, act_props, actor):
    """Moderate a message with Ollama, deleting if needed

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of recorded properties from running this action."""

    assert OLLAMA_IMPORTED, "The Ollama library and a working Ollama installation are required for ollama_message_moderate"

    #Message was blank
    if not message.text.strip():
        print("Message was blank.")
        return {}

    #User has an immunity badge
    if True in [badge in message.user.badges for badge in static.Moderation.staff_badges]:
        print(f"{message.user.username} is staff, skipping LLM check.")
        return {}

    #Get the LLM verdict
    response = ollama.chat(model = static.AutoModerator.llm_model, messages = [
        {"role" : "system", "content" : static.AutoModerator.llm_sys_prompt},
        {"role" : "user", "content" : message.text},
        ])

    #Parse the verdict
    try:
        verdict = int(response["message"]["content"])

    #Verdict was not valid
    except ValueError:
        print(f"Bad verdict for {message.text} : {response["message"]["content"]}")
        return {}

    #Response was not in expected format
    except KeyError:
        print(f"Could not get verdict for {message.text} : Response: {response}")
        return {}

    #Returned 1 for SFW
    if verdict:
        print("LLM verdicted as clean: " + message.text)
        return {}

    #Returned 0 for NSFW
    print("LLM verdicted as dirty: " + message.text)
    actor.delete_message(message)
    return {"deleted" : True}

class RantTTSManager():
    """System to TTS rant messages, with threshhold settings"""
    def __init__(self):
        """System to TTS rant messages, with threshhold settings.
    Instance this object, then pass it to RumbleChatActor().register_message_action()"""

        #The amount a rant must be to be TTS-ed
        self.__tts_amount_threshold = 0

        #The TTS callable to use
        self.__say = talkey.Talkey().say

    @property
    def tts_amount_threshold(self):
        """The amount a rant must be to be TTS-ed, 0 means all rants are TTS-ed"""
        return self.__tts_amount_threshold

    @tts_amount_threshold.setter
    def tts_amount_threshold(self, new):
        """The amount a rant must be to be TTS-ed, 0 means all rants are TTS-ed

    Args:
        new (int): The new threshold in cents."""

        assert isinstance(new, (int, float)) and new >= 0, "Value must be a number greater than zero"
        self.__tts_amount_threshold = new

    def set_rant_tts_sayer(self, new):
        """Set the callable to be used on rant TTS

    Args:
        new (callable): The function or method to call, passing the message text."""

        assert callable(new), "Must be a callable"
        self.__say = new

    def action(self, message, act_props, actor):
        """TTS rants above the manager instance's threshhold

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of additional recorded properties from running this action."""

        #Do not overlap sounds
        if act_props["sound"]:
            return {}

        if message.is_rant and message.rant_price_cents >= self.__tts_amount_threshold:
            self.__say(message.text)
            return {"sound" : True}
        return {}

class TimedMessagesManager():
    """System to send messages on a timed basis"""
    def __init__(self, actor, messages: iter, delay = 60, in_between = 0):
        """System to send messages on a timed basis. Instance this object, then pass it to RumbleChatActor().register_message_action()

    Args:
        actor (RumbleChatActor): The actor, to send the timed messages,
        messages (list): List of str messages to send
        delay (int): Time between messages in seconds
        in_between (int): Number of messages that must be sent before we send another timed one"""

        self.actor = actor
        assert len(messages) > 0, "List of messages to send cannot be empty"
        self.messages = messages
        assert delay > static.Message.send_cooldown, "Cannot send timed messages that frequently"
        self.delay = delay
        self.in_between = in_between

        #Next message to send
        self.up_next_index = 0

        #Time of last send
        self.last_send_time = 0

        #Counter for messages sent since our last announcement
        self.in_between_counter = 0

        #Start the sender loop thread
        self.running = True
        self.sender_thread = threading.Thread(target = self.sender_loop, daemon = True)
        self.sender_thread.start()

    def action(self, message, act_props, actor):
        """Count the messages sent

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of additional recorded properties from running this action."""

        self.in_between_counter += 1
        return {}

    def sender_loop(self):
        """Continuously wait till it is time to send another message"""
        while self.running:
            #time to send a message?
            if self.in_between_counter >= self.in_between and time.time() - self.last_send_time >= self.delay:
                #Send a message
                self.actor.send_message(self.messages[self.up_next_index])

                #Up the index of the next message, with wrapping
                self.up_next_index += 1
                if self.up_next_index >= len(self.messages):
                    self.up_next_index = 0

                #Reset wait counters
                self.in_between_counter = 0
                self.last_send_time = time.time()

            time.sleep(1)

class ChatBlipper:
    """Blip with chat activity, getting fainter as activity gets more common"""
    def __init__(self, sound_filename: str, rarity_regen_time = 60, stay_dead_time = 10, rarity_reduce = 0.1):
        """Blip with chat activity, getting fainter as activity gets more common.
    Instance this object, then pass it to RumbleChatActor().register_message_action()

    Args:
        sound_filename (str): The filename of the blip sound to play.
        rarity_regen_time (int): How long before the blip volume regenerates to maximum, in seconds.
        stay_dead_time (int): Effectively more regen time, in seconds, but with the volume staying at zero for the duration.
        rarity_reduce (float): How much a message reduces the volume in factor, ranging from >0 to 1."""

        self.sound = None
        self.load_sound(sound_filename)
        self.rarity_regen_time = rarity_regen_time
        self.stay_dead_time = stay_dead_time
        self.rarity_reduce = rarity_reduce

        #Time in the past at which we would have been silent
        self.silent_time = 0

    def load_sound(self, fn):
        """Load a sound from a file to use as a blip"""
        #Make sure PyGame mixer is initialized
        if not mixer.get_init():
            mixer.init()

        self.sound = mixer.Sound(fn)

    @property
    def current_volume(self):
        """Calculate the current volume based on how rare messages have been, from 0 to 1"""
        return max((min((time.time() - self.silent_time) / self.rarity_regen_time, 1), 0))

    def reduce_rarity(self):
        """Reduce the remembered rarity of a message"""
        curtime = time.time()

        #Limit the effective regen to 100%
        if curtime - self.silent_time > self.rarity_regen_time:
            self.silent_time = curtime - self.rarity_regen_time

        #Move the time we "were" silent forward, capping at present + stay-dead time
        self.silent_time = min((self.silent_time + self.rarity_regen_time * self.rarity_reduce, curtime + self.stay_dead_time))

    def action(self, message, act_props, actor):
        """Blip for a chat message, taking rarity into account for the volume

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of additional recorded properties from running this action."""

        self.sound.set_volume(self.current_volume)
        self.sound.play()
        self.reduce_rarity()
        return {}

class Thanker(threading.Thread):
    """Thank followers and subscribers in the chat"""
    def __init__(self, actor, **kwargs):
        """Thank followers and subscribers in the chat.
    Instance this object, then pass it to RumbleChatActor().register_message_action()

    Args:
        actor (RumbleChatActor): The Rumble Chat Actor instance.
        follower_message (str): Message to format with Cocorum Follower object.
            Defaults to static.Thank.DefaultMessages.follower
        subscriber_message (str): Message to format with the Cocorum Subscriber object.
            Defaults to static.Thank.DefaultMessages.subscriber
        gifted_subs_message (str): Message to format with the Cocorum GiftPurchaseNotification object.
            Defaults to static.Thank.DefaultMessages.gifted_subs"""

        super().__init__(daemon = True)
        self.actor = actor
        self.rum_api = self.actor.rum_api
        assert self.rum_api, "Thanker cannot function if actor does not have Rumble API"

        #Set up default messages
        self.follower_message = kwargs.get("follower_message", static.Thank.DefaultMessages.follower)
        self.subscriber_message = kwargs.get("subscriber_message", static.Thank.DefaultMessages.subscriber)
        self.gifted_subs_message = kwargs.get("gifted_subs_message", static.Thank.DefaultMessages.gifted_subs)

        #Start the thread immediately
        self.start()

    def action(self, message, act_props, actor):
        """Check for subscription gifts, and thank for them

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        act_props (dict): Action properties, aka metadata about what other things did with this message
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of additional recorded properties from running this action."""

        gift = message.gift_purchase_notification

        #This is not a gift purchase notification
        if not gift:
            return

        self.actor.send_message(self.gifted_subs_message.format(gift = gift))

        return {}

    def run(self):
        """Continuously check for new followers and subscribers"""
        while self.actor.keep_running:
            #Thank all the new followers
            for follower in self.rum_api.new_followers:
                self.actor.send_message(self.follower_message.format(follower = follower))

            #Thank all the new subscribers
            for subscriber in self.rum_api.new_subscribers:
                self.actor.send_message(self.follower_message.format(subscriber = subscriber))

            #Wait a bit, either the Rumble API refresh rate or the message sending cooldown
            time.sleep(max((self.rum_api.refresh_rate, static.Message.send_cooldown)))
