#!/usr/bin/env python3
"""Common chat actions

Actions commonly run on chat messages
S.D.G"""

import socket
from .localvars import *
try:
    import ollama
    OLLAMA_IMPORTED = True
except ModuleNotFoundError:
    OLLAMA_IMPORTED = False

def ollama_message_moderate(message, actor):
    """Moderate a message with Ollama, deleting if needed"""
    assert OLLAMA_IMPORTED, "The Ollama library and a working Ollama installation are required for ollama_message_moderate"

    #Message was blank
    if not message.text.strip():
        print("Message was blank.")
        return True

    #User has an immunity badge
    if True in [badge in message.user.badges for badge in STAFF_BADGES]:
        print(f"{message.user.username} is staff, skipping LLM check.")
        return True

    #Get the LLM verdict
    response = ollama.chat(model = "llama3", messages = [
        {"role" : "system", "content" : LLM_MODERATOR_SYS_MESSAGE},
        {"role" : "user", "content" : message.text},
        ])

    #Parse the verdict
    try:
        verdict = int(response["message"]["content"])

    #Verdict was not valid
    except ValueError:
        print(f"Bad verdict for {message.text} : {response["message"]["content"]}")
        return True

    #Response was not in expected format
    except KeyError:
        print(f"Could not get verdict for {message.text} : Response: {response}")
        return True

    #Returned 1 for SFW
    if verdict:
        print("LLM verdicted as clean: " + message.text)
        return True

    #Returned 0 for NSFW
    print("LLM verdicted as dirty: " + message.text)
    actor.delete_message(message)
    return False

class URLDetector():
    """System to check if a message contains a valid URL, with memory for previous checks"""
    def __init__(self):
        """Not meant to be created by the user. Use actions.block_url_messages() instead"""
        self.known_urls = [] #Things we know are URLs
        self.known_non_urls = [] #Things we know are not URLs

    def is_valid_url(self, string):
        """Determine if a string is a valid URL"""
        #All URLs must contain a dot
        if "." not in string:
            return False

        #Use previous records on the string if we have them
        if string in self.known_urls:
            return True
        if string in self.known_non_urls:
            return False

        try:
            socket.gethostbyname(string)
            self.known_urls.append(string)
            return True
        except socket.error:
            self.known_non_urls.append(string)
            return False

    def block_url_messages(self, message, actor):
        """Delete messages that contain valid URLs, unless sent by staff"""
        #Staff can post URLs
        if True in [badge in message.user.badges for badge in STAFF_BADGES]:
            return True

        #If the message contains a URL, delete it
        for seg in message.text.split():
            if self.is_valid_url(seg):
                actor.delete_message(message)
                return False

        #The message did not contain a URL
        return True

#Create an instance of URLDetector and provide its block_url_messages() method directly
block_url_messages = URLDetector().block_url_messages
