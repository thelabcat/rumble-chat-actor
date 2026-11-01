# Rumble Chat Actor
Automatically interact with your Rumble livestream chats.

Read the [Rumble Terms of Service status](#rumble-terms-of-service-status) before you install or run this.

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

## Rumble Terms of Service status

This project has no affiliation with Rumble. Wilbur Jaywright and Marswide BGL have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This project is not officially endorsed by Rumble Corp. or its subsidiaries.

[Rumble's Terms of Service](https://rumble.com/s/terms) prohibit "any form of automated software to interact with or access the Rumble Site ... without the prior written permission of Rumble." They also prohibit systematic retrieval of data or Content from the Rumble Service without prior written permission, and harvesting or collecting information about users of the Forum. Those terms define the Forum to include live chat.

Rumble's [Live Stream API help page](https://rumble.support/help/how-to-use-rumble-s-live-stream-api) gives "full reign" on using and implementing the official Live Stream API. This project also logs in, posts and moderates chat, uploads clips, and reads chat through [Cocorum](https://pypi.org/project/cocorum/)'s undocumented internal endpoints. That help page does not cover those endpoints.

The author has asked Rumble for written permission. There is no answer yet.

If you run Rumble Chat Actor:

- Use it only on your own channel, or on streams you moderate.
- The actor already honors Rumble's 3-second chat send limit. Leave that wait in place.
- Keep the bot prefix (`🤖: `) and the killswitch enabled.
- Stop if Rumble asks you to stop.

## Legal

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This project is not officially endorsed by Rumble Corp. or its subsidiaries.

This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.

## S.D.G.
