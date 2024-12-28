# Rumble Chat Actor
Automatically interact with your Rumble livestream chats.

This project is currently just a Python module. It is fully functional, but you have to install the [Python Programming Language](https://python.org) and write your own little script to inport and use it.

This project requires the following python libraries:
- [Cocorum](https://pypi.org/project/cocorum/)
- [Selenium](https://pypi.org/project/selenium/)
- [BrowserMob Proxy](https://pypi.org/project/browsermob-proxy)
- [MoviePy](https://pypi.org/project/moviepy)
- [Requests](https://pypi.org/project/requests)
- [Talkey](https://pypi.org/project/talkey)

RumChat Actor itself is [on PyPi](https://pypi.org/project/rumchat_actor), so once you have Python, installing it with `pip install rumchat-actor` should automatically download all dependencies.
Note that, if you are using Linux, you may have to install python3-pip separately. On Windows, Pip comes with Python.

Additional software requirements that aren't directly Python-related:
- [The Firefox web browser](https://www.mozilla.org/en-US/firefox/new/)

This is basically meant to be a FOSS local implementation of The Rumble Bot, and should run alongside your streaming software and / or other applications on most systems.

Here is an example usage script. Lines starting with # are comments. You would write a script like this, and save it as 'my_rumchat_actor_rig.py` or similar.
```
#First, import the module
import rumchat_actor

#Then, instantiate the Actor object.
#stream_id is either the base 10 or base 36 livestream ID you want the Actor to connect to, obtained from the popout chat or the Rumble Live Stream API.
#If stream_id is None but you pass api_url, the latest livestream shown on the API is chosen automatically.
#If you do not pass password, it will be requested
actor = rumchat_actor.RumbleChatActor(stream_id = STREAM_ID, username = USERNAME, password = PASSWORD)

#Let's set up a message action. A message action is a function called on every chat message.
#It is passed the cocorum.ssechat.SSEChatMessage object, and the RumbleChatActor object.

def eat_some_cheese(message, actor):
    '''If a message mentions cheese, eat some cheese'''
    if "cheese" in message.text.lower():
        actor.send_message(f"@{message.user.username} Eat some cheese 🧀.")
    #Actions should return True if they had to delete a message.
    #This action does not delete messages, so leaving it at the Python default
    # of returning None is fine.

actor.register_message_action(eat_some_cheese)

#There are many ways to register commands. Internally, they all end up
# as some form of rumchat_actor.commands.ChatCommand().
#The simplest way is to instantiate a prebuilt modification of this class.
#Be sure to pass the actor object to the class when you instantiate it.

actor.register_command(rumchat_actor.commands.KillswitchCommand(actor))

#This KillswitchCommand, by the way, shuts down the actor when a mod or admin runs it.
#You can open the Python interpreter and run help("rumchat_actor.commands") to
# see info on other ChatCommand derivative classes.

#The other main way to register a command is via a simple callable.
#Like message actions, these are also passed SSEChatMEssage and RumbleChatActor
def tester(message, actor):
    '''Test command callable'''
    actor.send_message(f"Test command run by @{message.user.username}")

#You must provide a command name when you do this way.
actor.register_command(name = "tester", command = tester)

#Finally, once everything is registered, we call the actor's mainloop method
# to run it. When this is running, you can press Ctrl+C to exit,
# but it might take a moment to respond.
actor.mainloop()
```

You would write this script, and run it as your local Rumble Chat Actor instance. Note that it currently does not exit on its own when a livestream ends. It may also exit on its own if chat is inactive for a very long time.
Hope this helps!

Be sure to run `help("rumchat_actor")` in the Python interpreter to get more info on the various methods that are available.
I'll try to get some better documentation up soon. Hope this helps!

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This project is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
