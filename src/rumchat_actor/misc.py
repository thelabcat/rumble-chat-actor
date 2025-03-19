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
