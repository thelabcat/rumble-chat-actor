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
- A message action runs on every message, and returns a dict of any new [action properties](action_properties.md) from its run. Message actions are good for automatic moderation, for example.
- A chat command only runs when triggered, and returns nothing.

Both message actions and chat command targets are passed:
1. The message we are working on,
2. The action properties of that message from all the combined (previous) actions that ran on it, and
3. The Rumble Chat Actor instance itself.

Here is an example of a message action function, and registering it. This message action scans the message for the word "cheese" in its text, and if it's in there, it sends a message back to the user.

```
def eat_some_cheese(message, act_props, actor):
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

A warning about this, though: The actor must wait to send messages to avoid rate limits by Rumble, so it has a built-in queue and auto-sending loop. If it is queuing to send messages faster than it is actually able to send them, to the point where the outbox is full (specified by the  `max_outbox_size` keyword upon actor init), it will start discarding the oldest messages. If you have an extremely active chat, bear this in mind. Also, if the actor is not able to process all message actions before the next message arrives, to the point where the messages it is processing are older than the max age (specified by the  `max_inbox_age` keyword upon actor init), it will skip them too. As long as, on average, the actor can work faster than the chat, everything should be fine.

And now, creating and registering a basic chat command. We must specify the name of the command, and the callable to be run. Again, it is passed the message, the action properties, and the actor. But this time, it does not return anything: Nothing else runs on a message after a command, so there's no need for it.

```
def say_hi(message, act_props, actor):
        """Say hi to the user who ran this command

    Args:
        message (cocorum.ChatAPI.Message): The chat message that called us.
        act_props (dict): Message action recorded properties."""
        
    #Oh man this is broken, we shouldn't be accessing this globally, see issues #44 and #45
    actor.send_message(f"Hello, @{message.user.username}!")

actor.register_command(name = "hi", command = say_hi)
```

But what about commonly used commands, especially ones with complex code? Well, I've included some pre-builts in the `rumchat_actor.commands` module. Let's register one I always think is a good idea, the Killswitch command. This command is available to staff only, and shuts down the actor immediately when it is processed. I actually use this as my usual shutdown method. Using a pre-built command is simple. We instance it, then pass it to the actor's `register_command()` method. In some cases, we also pass it to something like a [stream clip auto uploader](../modules_ref/misc/#rumchat_actor.misc.ClipUploader), which should be mentioned in the command's documentation, such as [here](../modules_ref/commands/#rumchat_actor.commands.ClipReplayBufferCommand).

```
ks_command = rumchat_actor.commands.KillswitchCommand(actor = actor)
actor.register_command(ks_command)
```

Once everything is registered, we can start the actor:

```
actor.mainloop()
```

This should run until you press Ctrl+C AND send one last message to stop it from waiting, or just kill the Python process somehow (closing the window for example), or send "!killswitch" in the chat to run the Killswitch command.

S.D.G.
