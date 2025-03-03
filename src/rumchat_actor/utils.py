#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

import os
from cocorum.utils import *
from . import static

def is_staff(user):
    """Check if a user is channel staff

Args:
    user (cocorum.chatapi.User): A user in the chat (importantly with a badges attribute)

Returns:
    Result (bool): Does the user have staff badges (admin or moderator)?"""

    return True in [badge in user.badges for badge in static.Moderation.staff_badges]

def get_safe_filename(clip_save_path, filename, extension = static.Clip.save_extension):
    """Make a filename that will not overwrite other files

Args:
    clip_save_path (str): The path to the folder to save the clip in.
    filename (str): The desired base filename.
    extension (str): The file name extension for the type of file to save.
        Defaults to static.Clip.save_extension

Returns:
    safe_filename (str): The base filename with a numeric suffix added as needed."""

    increment = 0
    safe_filename = filename
    while os.path.exists(os.path.join(clip_save_path, safe_filename + "." + extension)):
        increment += 1
        safe_filename = filename + f"({increment})"
    return safe_filename
