#!/usr/bin/env python3
"""Common chat actions

Actions commonly run on chat messages
S.D.G"""

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
