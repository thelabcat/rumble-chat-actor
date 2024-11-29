#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

import os
from cocorum.utils import *
from . import static

def is_staff(user):
    """Check if a user is channel staff"""
    return True in [badge in user.badges for badge in static.Moderation.staff_badges]

def get_safe_filename(clip_save_path, filename, extension = static.Clip.save_extension):
    """Make a filename that will not overwrite other clips"""
    increment = 0
    safe_filename = filename
    while os.path.exists(os.path.join(clip_save_path, safe_filename + "." + extension)):
        increment += 1
        safe_filename = filename + f"({increment})"
    return safe_filename
