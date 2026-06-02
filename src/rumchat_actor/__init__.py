#!/usr/bin/env python3
"""Rumble Chat Actor

Automatically interact with your Rumble livestream chats.

Modules exported by this package:

- `actions`: Common message actions (some are functions, others are classes)
- `commands`: Chat command base class and derivatives for common commands
- `misc`: Miscellanious classes and functions for end use
- `utils`: Utility functions and classes for internal use
- `static`: Static variables

This file is part of Rumble Chat Actor.

Rumble Chat Actor is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Rumble Chat Actor is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Rumble Chat Actor. If not, see <https://www.gnu.org/licenses/>.

S.D.G."""

from getpass import getpass
import queue
import textwrap
import threading
import time
from typing import Sequence
from cocorum import RumbleAPI, Livestream, servicephp, scraping
from cocorum.chatapi import ChatAPI
from . import actions, commands, misc, utils, static


class RumbleChatActor:
    """Actor that interacts with Rumble chat"""

    def __init__(self, init_message: str = "Hello, Rumble!", ignore_users: Sequence[str] = static.KNOWN_BOTS, **kwargs):
        """Actor that interacts with Rumble chat.
    Instance this object, register all chat commands and message actions, then call its mainloop() method.

    Args:
        stream_id (int | str): The stream ID you want to connect to.
            Defaults to latest livestream.
        init_message (str): What to say when the actor starts up.
            Defaults to "Hello, Rumble!"
        session (str | dict[str, str): A saved session token we are already logged in with.
            Defaults to None, we must perform login now.
        username (str): The username to log in with.
            Defaults to manual entry.
        password (str): The password to log in with.
            Defaults to manual entry.
        logout_on_exit (bool): Wether or not to log out when the actor quits.
            Defaults to logging out a session we created, not logging out a provided session.
        channel (int | str): The channel to post messages as.
            Defaults to user posts messages, no channel.
        api_url (str): The Rumble Live Stream API URL with the streamer's key (or RumBot's passthrough).
            Defaults to acquiring key from the account the bot signs in to.
        ignore_users (Sequence[str]): List of usernames to not act on (not a moderation feature).
            Defaults to static.KNOWN_BOTS
        invalid_command_respond (bool): Sets if we should post an error message if a command was invalid.
            Defaults to False.
        max_outbox_size (int): How many messages can be waiting to send before we start cancelling old ones.
            Defaults to static.Message.max_outbox_size
        max_inbox_age (int | float): How old messages in the chat can be before we start skipping them to catch up.
            Defaults to static.Message.max_inbox_age"""

        # Get Live Stream API

        channel = kwargs.get("channel")
        password = kwargs.get("password")
        session = kwargs.get("session")
        api_url = kwargs.get("api_url")
        stream_id = kwargs.get("stream_id")

        self.servicephp: servicephp.ServicePHP | None = servicephp.ServicePHP(
            kwargs.get("username"), session)
        """Cocorum Service.PHP API wrapper, for most account operations"""

        self.username: str = None
        """The username we are chatting as, once we figure that out"""

        self.rum_api: RumbleAPI = None
        """Cocorum Live Stream API wrapper, if the bot is acting on its own account's behalf"""

        self.api_stream: Livestream = None
        """Cocorum wrapper for livestream data, if we have Live Stream API for the streamer"""

        # Don't try to use logged-in operations until ServicePHP is logged in!
        self.scraper = scraping.Scraper(self.servicephp)
        """Cocorum data scraper for misc"""

        # We have a good session
        if self.servicephp.session_cookie:
            print("Session token provided - already logged in.")

        # We must log in ourselves
        else:
            if api_url:
                print("Live Stream API URL provided.")
                self.rum_api = RumbleAPI(api_url)
                if self.servicephp.username and self.rum_api.username != self.servicephp.username:
                    print(
                        "Note: This is someone else's Live Stream API. We are acting on behalf of another user.")
                    assert not stream_id or stream_id in self.rum_api.livestreams, "Stream ID was manually specified, but is not present in provided Live Stream API data"

                elif not self.servicephp.username:
                    print(
                        "Assuming this is our API URL. Starting login as `{self.rum_api.username}`...")
                    # We're not using the local `username` variable anymore
                    self.servicephp.username = self.rum_api.username

            # Keep trying to log in until we succeed
            while not self.servicephp.session_cookie:
                # Get credentials, or let the user know we have them
                if not self.servicephp.username:
                    self.servicephp.username = input("Username: ")
                else:
                    print("Username:", self.servicephp.username)
                if not password:
                    password = getpass("Password (no echo): ")
                else:
                    print("Password: [specified]")

                try:
                    twofa = self.servicephp.login_basic(password)
                    if twofa:
                        self.handle_2fa(twofa)
                except AssertionError as e:
                    print("Login failed with the following exception:", e)
                    self.servicephp.username = None
                    password = None

        # We don't know our username, or it is an email (cannot use)
        if not self.servicephp.username or "@" in self.servicephp.username:
            print("Don't know our in-chat username. Discovering...")
            self.scraper.validate_username()
            print(f"Username is `{self.servicephp.username}`.")

        # Now that we are logged in, get some other data and endpoints

        self.channel: scraping.HTMLChannel = self._find_appear_channel_info(
            channel) if channel else None
        """Cocorum wrapper for information on the channel we should chat as, if any"""

        # Once we are logged in, see if we should get an API wrapper
        if not api_url:
            print("No Live Stream API URL provided.")

            if stream_id:
                print(
                    "Stream ID manually specified. Assuming this bot is acting on behalf of another user.")
            else:
                print("Auto-obtaining API URL...")
                key_infos = self.scraper.get_rls_api_keys()
                ki = key_infos[0]

                # Main user account does not have key associated
                if not ki.url_with_key:
                    print("Main user account does not have a pre-generated key.")
                    # User specified a channel, maybe that has a key
                    if self.channel:
                        # Find the matching key info
                        ki = None
                        for ki in key_infos:
                            if ki.channel_id == self.channel:
                                break
                        assert ki is not None, f"Somehow Cocorum Scraper did not return any matching key infos for channel `{self.channel}`, even though it exists. Report this issue to Cocorum devs."

                        # Specific channel does not have key either
                        if not ki.url_with_key:
                            print(
                                "Specified channel does not have a pre-generated key.")

                # We still need key info
                if not ki.url_with_key:
                    print("Generating new key for user...")
                    key_infos[0].reset_key()
                    key_infos = self.scraper.get_rls_api_keys()
                    ki = key_infos[0]

                # We definitely have key info now
                self.rum_api = RumbleAPI(ki)

        # A stream ID was passed
        if stream_id:
            self.stream_id, self.stream_id_b10 = utils.base_36_and_10(
                stream_id)

            # It is not our livestream or we have no Live Stream API,
            # so LS API functions are not available
            if not self.rum_api or self.stream_id not in self.rum_api.livestreams:
                self.api_stream = None

            # It is our livestream, we can use the Live Stream API
            else:
                self.api_stream = self.rum_api.livestreams[self.stream_id]

        # A stream ID was not passed
        else:
            assert self.rum_api, "Cannot auto-find stream ID without a Live Stream API url"
            self.api_stream = self.rum_api.latest_livestream

            # At least one live stream must be shown on the API
            assert self.api_stream, "No stream ID was passed and you are not live"

            self.stream_id = self.api_stream.stream_id
            self.stream_id_b10 = utils.base_36_to_10(self.stream_id)

        # Connect to chat
        self.chat = ChatAPI(self.stream_id, self.servicephp)
        self.chat.clear_mailbox()

        # The maximum age of a message before we will not process it
        self.max_inbox_age = kwargs.get(
            "max_inbox_age", static.Message.max_inbox_age)

        # Ignore these users when processing messages
        self.ignore_users = ignore_users

        # History of the bot's messages so they do not get loop processed
        self.sent_messages = []

        # Thread exit pipe for above
        self.__sent_messages_queue = queue.Queue()

        # Messages waiting to be sent
        self.outbox = queue.Queue(kwargs.get(
            "max_outbox_size", static.Message.max_outbox_size))

        # Messages that we know are actually raid alerts
        self.known_raid_alert_messages = []

        # Action to be taken when raids occur
        self.__raid_action = print

        # Loop condition of the mainloop() and sender_loop() methods
        self.keep_running = True

        # Send an initialization message to get wether we are moderator or not
        _, user = self.__send_message(static.Message.bot_prefix + init_message)
        assert utils.is_staff(user), \
            "Actor cannot function without being channel staff"

        # Time that the last message we sent was sent
        self.last_message_send_time = time.time()

        # thread to send messages at timed intervals
        self.sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True)
        self.sender_thread.start()

        # Functions that are to be called on each message,
        # must return False if the message was deleted
        self.message_actions = []

        # Instances of ChatCommand, by name
        self.chat_commands = {}

        # Wether or not to post an error message if an invalid command was called
        self.invalid_command_respond = kwargs.get(
            "invalid_command_respond", False)
        assert isinstance(self.invalid_command_respond, bool), \
            f"Argument invalid_command_respond must be bool, not {type(self.invalid_command_respond)}"

        # Finally, get the logout setting
        self.logout_on_exit = kwargs.get("logout_on_exit", not session)

    def _find_appear_channel_info(self, ident: int | str):
        """
        Find all channel data based on one piece of information

        Args:
            ident (int |str): The channel numeric ID, name, or slug.

        Returns:
            channel (scraping.HTMLChannel): Matching channel information.
        """

        # Get all real channels we can use
        postable_channels = self.scraper.get_channels()

        # Check through all the real channels to see if one matches the choice
        for channel in postable_channels:
            if ident == channel:
                return channel

        # We went through all of them and never returned out of the method
        raise ValueError(f"Did not find any matching channels for `{ident}`")

    def handle_2fa(self, twofa: servicephp.TwoFacAuth):
        """Handle 2FA login

        Args:
            twofa (servicephp.TwoFacAuth): The 2FA information handler from the first login step."""

        option = utils.multiple_choice("Select option for 2FA:", twofa.options)
        sent_to = twofa.request_2fa_code(option)
        if sent_to:
            print(f"A code was sent to \"{sent_to}\".")
        code = input("Enter the 2FA code: ")
        self.servicephp.login_second_factor(twofa, code)

    def send_message(self, text):
        """Send a message in chat (splits across lines if necessary)

        Args:
            text (str): The message to send"""

        text = static.Message.bot_prefix + text
        assert "\n" not in text, "Message cannot contain newlines"
        assert len(text) < static.Message.max_multi_len, "Message is too long"
        for subtext in textwrap.wrap(text, width=static.Message.max_len):
            is_sent = False
            while not is_sent:
                try:
                    self.outbox.put(subtext, block=False)
                    # TODO: Print is not quite thread safe... sort of? It won't crash at least
                    print("💬:", subtext)
                    is_sent = True
                except queue.Full:
                    print(
                        "Error: Message send outbox is full, dropped message:\n\t", self.outbox.get())

    def _sender_loop(self):
        """Constantly check our outbox and send any messages in it"""
        while self.keep_running:
            # We have messages to send and it is time to send one
            if time.time() - self.last_message_send_time > static.Message.send_cooldown:
                try:  # Must be nonblocking so we can shut down
                    self.__send_message(self.outbox.get_nowait())
                except queue.Empty:
                    pass
            time.sleep(0.1)

    def __send_message(self, text):
        """Send a message in chat (no safeties or suffix)

        Args:
            text (str): The message to send"""

        assert len(text) < static.Message.max_len, \
            f"Message with prefix cannot be longer than {static.Message.max_len} characters"

        self.__sent_messages_queue.put(text)

        self.last_message_send_time = time.time()
        return self.chat.send_message(text, channel_id=self.channel)

    @property
    def delete_message(self):
        """Delete a message in the chat (passthrough to cocorum.ChatAPI)"""
        return self.chat.delete_message

    @property
    def mute_user(self):
        """Mute a user in the chat (passthrough to cocorum.ChatAPI)"""
        return self.chat.mute_user

    @property
    def unmute_user(self):
        """Unmute a user (passthrough to cocorum.ChatAPI)"""
        return self.chat.unmute_user

    @property
    def pin_message(self):
        """Pin a message by ID or li element (passthrough to cocorum.ChatAPI)"""
        return self.chat.pin_message

    @property
    def unpin_message(self):
        """Unpin the currently pinned message (passthrough to cocorum.ChatAPI)"""
        return self.chat.unpin_message

    def quit(self):
        """Shut down everything"""
        self.keep_running = False
        self.chat.close()
        if self.logout_on_exit:
            self.servicephp.logout()

    def __run_if_command(self, message, act_props: dict):
        """Check if a message is a command, and run it if so

        Args:
            message (cocorum.ChatAPI.Message): The message in question.
            act_props (dict): Properties of this message as recorded by message actors."""

        # Not a command
        if not message.text.startswith(static.Message.command_prefix):
            return

        # Get command name
        name = message.text.split()[0].removeprefix(
            static.Message.command_prefix)

        # Is not a valid command
        if name not in self.chat_commands:
            if self.invalid_command_respond:
                self.send_message(
                    f"@{message.user.username} That is not a registered command.")
            return

        self.chat_commands[name].call(message, act_props)

    def register_command(self, command, name=None, help_message=None):
        """Register a command

        Args:
            command (callable | commands.ChatCommand): The command operation to register.
            name (str): The name of the command.
                Defaults to None, use the ChatCommand name.
            help_message (str): Help message for this command.
                Defaults to None, use the ChatCommand help message (cannot override).
            """
        # Is a ChatCommand instance
        if isinstance(command, commands.ChatCommand):
            if name and name != command.name:
                print(
                    f"Overriding command name ''{command.name}' with '{name}'")
                command.name = name

            self.chat_commands[command.name] = command

        # Is a callable
        elif callable(command):
            assert name, "Name cannot be None if command is a callable"
            assert " " not in name, "Name cannot contain spaces"
            self.chat_commands[name] = commands.ChatCommand(
                name=name, actor=self, target=command)

        else:
            raise TypeError(
                f"Command must be of type ChatCommand or a callable, not {type(command)}.")

        # A specific help message was provided
        if help_message:
            assert not self.chat_commands[name].help_message, "ChatCommand has internal help message already set, cannot override"
            self.chat_commands[name].help_message = help_message

    def register_message_action(self, action):
        """Register an action to be run on every message

        Args:
            action (callable | object):
                - Action must be a callable or have an action() attribute.
                - On run, action will be passed cocorum.ssechat.SSEChatMessage() and this actor instance.
                - Action should return a dictionary of action properties (full documentation pending, things like {"deleted" : True})."""

        if hasattr(action, "action"):
            action = action.action

        assert callable(
            action), "Action must be a callable or have an action() attribute"
        self.message_actions.append(action)

    @property
    def raid_action(self):
        """The callable we are supposed to run on raids"""
        return self.__raid_action

    @raid_action.setter
    def raid_action(self, new_action):
        """The callable we are supposed to run on raids

        Args:
            new_action (callable): The callable to be run.
                Passes it the cocorum.ChatAPI.Message and this actor instance."""

        assert callable(new_action), "Raid action must be a callable"
        self.__raid_action = new_action

    def __process_message(self, message):
        """Process a single SSE Chat message

        Args:
            message (cocorum.ChatAPI.Message): The message to send to actions and check for commands"""

        # Skip messages that are too old
        if time.time() - message.time > self.max_inbox_age:
            print(
                f"Error: Message processing is behind. Skipped message:\n{message.text}\n\t- {message.user.username}")
            return

        # Ignore messages that are from our account and match ones we sent before
        if message.user.username == self.username and message.text in self.sent_messages:
            return

        # the message is actually a raid alert, take raid action on it, nothing more
        if message.raid_notification:
            self.known_raid_alert_messages.append(message)
            self.raid_action(message, self)
            return

        # If the message is from the same account as us, consider it in message send cooldown
        if message.user.username == self.username:
            self.last_message_send_time = max(
                (self.last_message_send_time, message.time))

        # Ignore messages that are in the ignore_users list
        if message.user.username in self.ignore_users:
            return

        act_props_all = {}
        for action in self.message_actions:
            # The message got deleted
            if message.deleted:
                return

            act_props_one = action(message, act_props_all, self)

            # Legacy message action return support
            if act_props_one is None:
                act_props_one = {}
            elif not isinstance(act_props_one, dict):
                print(
                    f"Warning: message action {action} did not return valid action properties, but rather {act_props_one}. Compensating with blank action properties.")
                act_props_one = {}

            act_props_all.update(act_props_one)
            if act_props_all.get("deleted"):
                return

        self.__run_if_command(message, act_props_all)

    def empty_sent_message_queue(self):
        """Move sent messages from the thread exit pipe to the list"""
        # WARNING: This is only safe if nobody else gets from this queue!
        while not self.__sent_messages_queue.empty():
            self.sent_messages.append(self.__sent_messages_queue.get())

    def mainloop(self):
        """Run the actor forever"""
        try:
            while self.keep_running:
                self.empty_sent_message_queue()
                m = self.chat.get_message()
                if not m:  # Chat has closed
                    self.keep_running = False
                    return
                self.__process_message(m)

        except KeyboardInterrupt:
            print("KeyboardInterrupt shutdown.")
            self.quit()
