# Tutorials

## A demo setup with an educational message action and commands

The first thing to do is import the base module.

```python
import rumchat_actor
```

You can also import submodules, but I have `rumchat_actor` import all of them at current, so it's not necessary.
Next, we create the actor. You can pass it a few different combinations things to give it what it needs, but the simplest way for now is to just pass it your username.

```python
actor = rumchat_actor.RumbleChatActor(username = USERNAME)
```

With this, it will ask for your password (and potentially a 2FA code), and automatically get the Live Stream API URL for this account. It assumes that the account it is using is also the account you are streaming on, and that it should connect to the latest stream it finds in the Live Stream API. However, you can specify a different stream, or even a different account's Live Stream API URL if you want. You can also save your login by passing it a session token instead.

Once the actor is initialized, we can start registering message actions, and chat commands.
- A message action runs on every message, and returns a dict of any new [action properties](action_properties.md) from its run. Message actions are good for automatic moderation, for example.
- A chat command only runs when triggered, and returns nothing.

Both message actions and chat command targets are passed:
1. The message we are working on,
2. The action properties of that message from all the combined (previous) actions that ran on it, and
3. The Rumble Chat Actor instance itself.

Here is an example of a message action function, and registering it. This message action scans the message for the word "cheese" in its text, and if it's in there, it sends a message back to the user.

```python
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

```python
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

```python
ks_command = rumchat_actor.commands.KillswitchCommand(actor = actor)
actor.register_command(ks_command)
```

Once everything is registered, we can start the actor:

```python
actor.mainloop()
```

This should run until you press <kbd>Ctrl</kbd>+<kbd>C</kbd> AND send one last message to stop it from waiting, or just kill the Python process somehow (closing the window for example), or send "!killswitch" in the chat to run the Killswitch command.

<small>This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.
</small>

**S.D.G.**
