# Action properties

Action properties are a dictionary of metadata produced by message actions, passed to each following message action and a command target if the message is a command. Each message action returns a dict of any *new* action properties it wants to add, but does not need to return existing ones. If a returned new action property already exists in the dict, the old value is overwritten. As mentioned above, commands are passed the action properties dict when they run, but they do not create any of their own, because a message can only ever call a maximum of one command.

## Official action properties (all keys are strings):

- "deleted" (bool): This message was deleted by the actor, stop processing it.
- "sound" (bool): Wether or not sound has been produced for this message.

<small>This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.
</small>

**S.D.G.**
