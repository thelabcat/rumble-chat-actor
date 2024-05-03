# Rumble Chat Actor
Automatically interact with your Rumble livestream chats.

This project requires the following python libraries:
- [Cocorum](https://pypi.org/project/cocorum/)
- [Selenium](https://pypi.org/project/selenium/)

Additional software requirements:
- [Firefox](https://www.mozilla.org/en-US/firefox/new/)

This is basically meant to be a FOSS local implementation of The Rumble Bot, and should run alongside your streaming software and / or other applications on most systems.

Example usage:
```
import rumchat_actor

def eat_some_cheese(message, actor):
    """If a message mentions cheese, eat some cheese"""
    if "cheese" in message.text.lower():
        actor.send_message(f"@{message.user.username} Eat some cheese 🧀.")

    return True #Actions should return None or False if they had to delete a message

#stream_id is either the base 10 or base 36 livestream ID you want the Actor to connect to, obtained from the popout chat or the Rumble Live Stream API.
#If stream_id is None but you pass api_url, the latest livestream shown on the API is chosen automatically.
#If you pass profile_dir to an existing Firefox profile directory, your sign-ins to Rumble chat for the actor will be saved.
#Otherwise, you will have to log in manuaglly each time you use the bot, or pass credentials = (username, password).
actor = rumchat_actor.RumbleChatActor(stream_id = STREAM_ID)

#Register an action to be called on every message
actor.register_message_action(eat_some_cheese)

#Register a command via the ChatCommand class
actor.register_command(rumchat_actor.ChatCommand(name = "hi", actor = actor, target = lambda message, actor: actor.send_message(f"Hello, @{message.user.username}!")))

#Register a command via a callable
actor.register_command(name = "tester", command = lambda message, actor: print(f"Test command run by {message.user.username}"))

#Run the bot continuously
actor.mainloop()
```

You would write this script, and run it as your local Rumble Chat Actor instance. Note that it currently does not exit on its own when a livestream ends.
Hope this helps!

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
