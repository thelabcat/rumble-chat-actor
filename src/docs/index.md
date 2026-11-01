#Rumble Chat Actor

A Python framework for setting up commands or other automated action for your Rumble livestream chat.

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

## Table Of Contents

1. [Rumble Terms of Service status](#rumble-terms-of-service-status)
2. [Tutorials](tutorials.md)
3. [How-To Guides](how-to-guides.md)
4. [Reference](reference.md)
    1. [rumchat_actor](modules_ref/main.md)
    2. [rumchat_actor.actions](modules_ref/actions.md)
    3. [rumchat_actor.commands](modules_ref/commands.md)
    4. [rumchat_actor.misc](modules_ref/misc.md)
    5. [rumchat_actor.utils](modules_ref/utils.md)
    6. [rumchat_actor.static](modules_ref/static.md)
    7. [Action Properties](action_properties.md)
5. [Explanation](explanation.md)

## Acknowledgements

Special thanks to GlobalGamer2015 for information on the SSE chat API, and to K4nji for help with the password hashing algorithm. Both helped with other API endpoints as well. I'd also like to thank Angi Harrover and Derek Geetz for helping me test this framework. Honorable mention to [a3r0id's RumblePy](https://github.com/a3r0id/RumblePy), a discontinued module that held the basis for authentication which I used.

I, Wilbur Jaywright, and my brand, Marswide BGL, have no official association with Rumble Corp. beyond that of a normal user and/or channel on the Rumble Video platform. This wrapper is not officially endorsed by Rumble Corp. or its subsidiaries.

<small>This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.
</small>

**S.D.G.**
