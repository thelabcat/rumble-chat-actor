#Rumble Chat Actor

A Python framework for setting up commands or other automated action for your Rumble livestream chat.

## Rumble Terms of Service status

[Rumble's Live Stream API help page](https://rumble.support/help/how-to-use-rumble-s-live-stream-api) says that, for now, users have "full reign" on using and implementing the Rumble Live Stream API however they want. However, [Rumble's Terms of Service](https://rumble.com/s/terms) prohibit "any form of automated software to interact with or access the Rumble Site ... without the prior written permission of Rumble." They prohibit "systematic retrieval of data or Content ... to create or compile ... a collection, compilation, library, database or directory." They also prohibit harvesting information about chat and forum users. Because Rumble Chat Actor logs in, posts and moderates chat, uploads clips, and reads chat through [Cocorum](https://pypi.org/project/cocorum/)'s undocumented internal endpoints, it fits this description. I have already asked Rumble for written permission and am waiting on a reply, and I will update this project according to their reply.

### Even if Rumble says yes...

- Use this library only on your own account or channel, or on streams you moderate.
- Do not try to bypass any form of rate limits that Rumble may impose. This library is not intended to be used to harm Rumble or its users.
- Do not use any of the features for bulk collection of data.
- If Rumble asks you to stop, do.

## Table Of Contents

1. [Tutorials](tutorials.md)
2. [How-To Guides](how-to-guides.md)
3. [Reference](reference.md)
    1. [rumchat_actor](modules_ref/main.md)
    2. [rumchat_actor.actions](modules_ref/actions.md)
    3. [rumchat_actor.commands](modules_ref/commands.md)
    4. [rumchat_actor.misc](modules_ref/misc.md)
    5. [rumchat_actor.utils](modules_ref/utils.md)
    6. [rumchat_actor.static](modules_ref/static.md)
    7. [Action Properties](action_properties.md)
4. [Explanation](explanation.md)

## Acknowledgements

Special thanks to GlobalGamer2015 for information on the SSE chat API, and to K4nji for help with the password hashing algorithm. Both helped with other API endpoints as well. I'd also like to thank Angi Harrover and Derek Geetz for helping me test this framework. Honorable mention to [a3r0id's RumblePy](https://github.com/a3r0id/RumblePy), a discontinued module that held the basis for authentication which I used.

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

<small>This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.
</small>

**S.D.G.**
