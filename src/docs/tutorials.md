# Tutorials

## A demo setup with an educational message action and commands

The first thing to do is import the base module.

```
import rumchat_actor
```

You can also import submodules, but I have `rumchat_actor` import all of them at current, so it's not necessary.
Next, we create the actor. You can pass it a few different combinations things to give it what it needs,which I explain below, or you can just skip to the code if you want to do the recommended way:

- It needs to know the numeric ID of the livestream it's going to act on. You can either pass that manually after obtaining it from the end of a pop-out chat URL, or just pass the actor your Rumble Live Stream API URL as obtained from [the Live Stream API key management page on Rumble.com](https://rumble.com/account/livestream-api). With the API URL, the actor will just automatically load the ID of the latest livestream and use that. Note, this can be either base 10 or 36, but if you make it base 10, please also make it an integer instead of a string. Base 36 can look like base 10 if it's just the right number so that only base 10 numerals are included, and there's no way for the actor to tell the difference, so it assumes base 36 for strings.
- It needs to be able to sign in to Rumble with a verified account to send chat messages. Since the credentials are sent directly to Rumble with no middleman service, they are as secure as the computer you're running this script on (assuming no module in this chain of support got a malicious update, only God can protect you ultimately). You can either pass it a Rumble username (NOT the email) and a password, or pass it a username and a session token (you would do that for saving logins), or pass it nothing and it will ask you to log in manually. A note about that, when you type the password, if you are in a terminal that Python can control directly, the characters will not be shown. Like, at all. Not even a dot or an asterisk, the cursor will not move. This is normal behavior, and is a security feature called "no echo" from the old teletype days. Now, if you run this script in Python's IDLE shell, the typed password WILL be shown CLEARLY VISIBLE, so don't use manual password entry and IDLE together if there is any chance that IDLE will be shown on stream. I personally recommend having the password loaded from a text file, or you can use an environment variable if you know how to do that, but never put your credentials directly into your code.

There are other things you can specify that some commands need, but most of them are automatically obtained from the Rumble Live Stream API if it is passed. You can find all of the arguments in the reference documentation. Here is the base recommended setup:

```
actor = rumchat_actor.RumbleChatActor(api_url = RUMBLE_API_URL, username = USERNAME, password = PASSWORD)
```

Once the actor is initialized, we can start registering message actions, and chat commands.
- A message action runs on every message, and can do stuff related to it or not. It must return a dictionary of action properties (pending documentation, this is basically metadata). The most common action property is "deleted" : bool, used for when a message action deleted the message in question. Message actions are registered as functions, or objects with an action() method that takes the same arguments: message, and actor.
- A chat command only runs when triggered, and returns nothing. It is passed the message it was launched from, and the action properties of that message from all the combined actions that ran on it.

Here is an example of a message action function, and registering it:

```
def eat_some_cheese(message, actor):
    """If a message mentions cheese, eat some cheese

    Args:
        message (cocorum.chatapi.Message): The chat message to run this action on.
        actor (RumbleChatActor): The chat actor.

    Returns:
        act_props (dict): Dictionary of recorded properties from running this action."""

    if "cheese" in message.text.lower():
        actor.send_message(f"@{message.user.username} Eat some cheese 🧀.")
    
    return {}

actor.register_message_action(eat_some_cheese)
```

And now, a basic chat command. We must specify the name of the command, and the callable to be run.

```
def say_hi(message, act_props):
        """Say hi to the user who ran this command

    Args:
        message (cocorum.ChatAPI.Message): The chat message that called us.
        act_props (dict): Message action recorded properties."""
        
    #Oh man this is broken, we shouldn't be accessing this globally, see issues #44 and #45
    actor.send_message(f"Hello, @{message.user.username}!")

actor.register_command(name = "hi", command = say_hi)
```

Once everything is registered, we can start the actor:

```
actor.mainloop()
```

This should run until you press Ctrl+C AND send one last message to stop it from waiting, or just kill the Python process somehow (closing the window for example). For a smoother means of shutdown, see the Killswitch command.
