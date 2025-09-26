#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

import os
from typing import Sequence
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


def multiple_choice(title: str, options: Sequence[str]) -> str:
    """Allow the user to choose between multiple options.
        Automatically selects a lone option.

    Args:
        title (str): The question at hand.
        options (Sequence[str]): A subscriptable of option strings.

    Returns:
        choice (str): The chosen option."""

    # The function can't work if there's no options to choose from!
    assert len(options) > 0, "Too few options"

    # If there's just one option, choose it automatically
    if len(options) == 1:
        print(f"Only one option for, \"{title}\", and that is \"{options[0]}\".")
        return options[0]

    # Find the 'biggest' option by length, and then find out how long it is.
    option_max_width = len(max(options, key=len))

    # We're going to show a number next to each option as well, so we'd better
    # get the visual length of the biggest number as well.
    num_width = len(str(len(options)))

    # Make sure we get a valid choice.
    # The return statements will exit this loop for us.
    while True:
        # Display the question and the options, and get an input
        print(title)

        for i, option in enumerate(options):
            # Line all the options and their numbering up
            print(f"{i + 1:0{num_width}d}··{option:·>{option_max_width}}")

        # Finally, ask the user for some input.
        entry = input("Choice: ")

        # Option was typed directly
        if entry in options:
            return entry

        # Number was typed
        if entry.isnumeric():
            try:
                return options[int(entry) - 1]

            # The number wasn't a valid option index
            except IndexError:
                print("Entered number does not match an option.")

        # Something was typed but it was invalid
        if entry:
            print("Invalid entry. Please type a number or the option itself.")
