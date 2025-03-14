# Rumble Chat Actor
Automatically interact with your Rumble livestream chats.

This project is currently just a Python module. It is fully functional, but you have to install the [Python Programming Language](https://python.org) and write your own little script to inport and use it.

This project requires the following python libraries:
- [Cocorum](https://pypi.org/project/cocorum/)
- [MoviePy](https://pypi.org/project/moviepy)
- [Requests](https://pypi.org/project/requests)
- [Talkey](https://pypi.org/project/talkey)
- [OBSWS Python](https://pypi.org/project/obsws-python)
- [PyGame](https://pypi.org/project/pygame)
- [Standard Pipes](https://pypi.org/project/standard-pipes)

RumChat Actor itself is [on PyPi](https://pypi.org/project/rumchat_actor), so once you have Python, installing it with `pip install rumchat-actor` should automatically download all dependencies.
Note that, if you are using Linux, you may have to install python3-pip separately. On Windows, Python's installer comes with Pip.

This is basically meant to be a FOSS local implementation of The Rumble Bot, and should run alongside your streaming software and / or other applications on most systems. To use it, you write your own Python script that imports the library and sets up your actor the way you want, and run it as your local Rumble Chat Actor instance. You can learn more about how to use Rumble Chat Actor with [the official documentation](https://thelabcat.github.io/rumble-chat-actor/). A basic tutorial is included.

Note that the actor currently does not exit on its own when a livestream ends. It may also exit on its own if chat is inactive for a very long time.

Hope this helps!

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This project is not officially endorsed by Rumble Corp. or its subsidiaries.

S.D.G.
