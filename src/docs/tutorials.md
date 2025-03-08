# Tutorials

```
Example usage:

import rumchat_actor

def eat_some_cheese(message, actor):
    '''If a message mentions cheese, eat some cheese'''
    if "cheese" in message.text.lower():
        actor.send_message(f"@{message.user.username} Eat some cheese 🧀.")

    #Actions should return True if they had to delete a message

#stream_id is either the base 10 or base 36 livestream ID you want the Actor to connect to, obtained from the popout chat or the Rumble Live Stream API.
#If stream_id is None but you pass api_url, the latest livestream shown on the API is chosen automatically.
#If you do not pass password, it will be requested
actor = rumchat_actor.RumbleChatActor(stream_id = STREAM_ID, username = USERNAME, password = PASSWORD)

#Register an action to be called on every message
actor.register_message_action(eat_some_cheese)

#Register a command via the ChatCommand class
actor.register_command(rumchat_actor.commands.ChatCommand(name = "hi", actor = actor, target = lambda message, actor: actor.send_message(f"Hello, @{message.user.username}!")))

#Register a command via a callable
actor.register_command(name = "tester", command = lambda message, actor: print(f"Test command run by {message.user.username}"))

#Run the bot continuously
actor.mainloop()
```
