#!/usr/bin/env python3
"""Utilities

Various utility functions
S.D.G."""

from os.path import join as pjoin
from pathlib import Path
#from js2py import eval_js
from . import static

def is_staff(user):
    """Check if a user is channel staff"""
    return True in [badge in user.badges for badge in static.Moderation.staff_badges]

# def calc_password_hashes(password, salts):
#     """Hash a password given the salts"""
#     with open(pjoin(Path(__file__).parent, pjoin("dom_scripts", "md5Ex.js")), 'r') as f:
#         js = f.read()
#
#     return eval_js(js)(password, salts)
