#!/usr/bin/env python3
"""Miscellanious classes and functions

Functions and classes that did not fit in another module
S.D.G."""

import queue
import threading
import time
from cocorum import uploadphp
from . import static

class ClipUploader():
    """Upload clips to Rumble automatically"""
    def __init__(self, actor, clip_command, **kwargs):
        """Upload clips to Rumble automatically

    Args:
        actor (RumbleChatActor): The RumbleChatActor() instance
        clip_command (ChatCommand): The clip command instance
        channel_id (str | int): The name or int ID of the channel to upload to, defaults to no channel (user page)"""

        #Save actor
        self.actor = actor

        #Save clip command instance and assign ourself to it
        self.clip_command = clip_command
        self.clip_command.clip_uploader = self

        #Get upload system
        self.uploadphp = uploadphp.UploadPHP(self.actor.servicephp)

        #Channel ID to use, or None if it was not passed
        self.channel_id = kwargs.get("channel_id", 0)

        #List of clip filenames to upload
        self.clips_to_upload = queue.Queue()

        #Thread to keep uploading clips as they arrive
        self.clip_uploader_thread = threading.Thread(target = self.clip_upload_loop, daemon = True)
        self.clip_uploader_thread.start()

    def upload_clip(self, name, complete_path):
        """Add the clip filename to the queue

    Args:
        name (str): The base name of the clip.
        complete_path (str): The full file path of the clip."""
        self.clips_to_upload.put((name, complete_path))

    def __upload_clip(self, name, complete_path):
        """Upload a clip to Rumble

    Args:
        name (str): The base name of the clip.
        complete_path (str): The full file path of the clip."""

        upload = self.uploadphp.upload_video(
            file_path = complete_path,
            title = f"stream {self.actor.stream_id_b10} clip {name}",
            description = "Automatic clip upload. Enjoy!",
            category1 = static.Clip.Upload.category_1,
            category2 = static.Clip.Upload.category_2,
            channel_id = self.channel_id,
            visibility = "unlisted",
            )

        #Announce link
        self.actor.send_message("Clip uploaded to " + upload.url)

        print(f"Clip {name} published.")

    def clip_upload_loop(self):
        """Keep uploading clips while actor is alive"""
        while self.actor.keep_running:
            try:
                self.__upload_clip(*self.clips_to_upload.get_nowait())
            except queue.Empty:
                pass

            time.sleep(1)

class Thanker(threading.Thread):
    """Thank followers and subscribers in the chat"""
    def __init__(self, actor, **kwargs):
        """Thank followers and subscribers in the chat

    Args:
        actor (RumbleChatActor): The Rumble Chat Actor instance.
        follower_message (str): Message to format with Cocorum follower object.
            Defaults to static.Thank.DefaultMessages.follower
        subscriber_message (str): Message to format with the Cocorum subscriber object (twice!).
            Defaults to static.Thank.DefaultMessages.subscriber"""

        super().__init__(daemon = True)
        self.actor = actor
        self.rum_api = self.actor.rum_api
        assert self.rum_api, "Thanker cannot function if actor does not have Rumble API"

        #Set up default messages
        self.follower_message = kwargs.get("follower_message", static.Thank.DefaultMessages.follower)
        self.subscriber_message = kwargs.get("subscriber_message", static.Thank.DefaultMessages.subscriber)

        #Start the thread immediately
        self.start()

    def run(self):
        """Continuously check for new followers and subscribers"""
        while self.actor.keep_running:
            #Thank all the new followers
            for follower in self.rum_api.new_followers:
                self.actor.send_message(self.follower_message.format(follower))

            #Thank all the new subscribers
            for subscriber in self.rum_api.new_subscribers:
                self.actor.send_message(self.follower_message.format(subscriber, subscriber))

            #Wait a bit, either the Rumble API refresh rate or the message sending cooldown
            time.sleep(max((self.rum_api.refresh_rate, static.Message.send_cooldown)))
