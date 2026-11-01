# Explanation

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

## Why I created this library
This started off as a substitute to The Rumble Bot by Henry. I don't remember exactly why I wanted this, other than that I don't like using online services when I can help it. Not that they're inherently bad or anything, I just like not relying on the internet or a third party, since I grew up without it. I learned the stark difference between having to connect to an outside service, even a free one, and being able to do things on your own machine with no service charge or ads. I also like understanding how something works, and The Rumble Bot is proprietary, so my tinkering dissasemble-the-toy-and-put-it-back-together desire played a part. Right now, it seems like most of the things Rumble Chat Actor can do, other services can do more simply (RumBot, StreamBot, etc), but they remain proprietary, strictly online, or both. I mainly build it for my own sake; to learn how to make this stuff almost more than to use it.

## Example use cases
The big advantage or Rumble Chat Actor is that it's not a boxed-up app, but a framework. While the script for setting up basic commands and actions could be fairly simple, you can also make them as complex as you like. Basically anything Python can do, a Rumble Chat Actor command can. It is not sandboxed at all. You could signal a Raspberry Pi to switch on solid-state relays to a 13.8V power supply and honk a car horn, change some file on your PC to switch around how the game your playing works, or do more complex interactions with OBS via it's WebSocket interface. It's more suited to the super custom commander than the average everyday game streamer. I am also at this time still supporting operation by a third party, such as your moderator, in case you don't have enough horsepower or something.

<small>This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.
</small>

**S.D.G.**
