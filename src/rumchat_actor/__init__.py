#!/usr/bin/env python3
"""Rumble Chat Actor

Automatically interact with your Rumble livestream chats.

Example usage:

import rumchat_actor

def eat_some_cheese(message, actor):
    '''If a message mentions cheese, eat some cheese'''
    if "cheese" in message.text.lower():
        actor.send_message(f"@{message.user.username} Eat some cheese 🧀.")

    #Actions should return True if they had to delete a message

#stream_id is either the base 10 or base 36 livestream ID you want the Actor to connect to, obtained from the popout chat or the Rumble Live Stream API.
#If stream_id is None but you pass api_url, the latest livestream shown on the API is chosen automatically.
#If you pass profile_dir to an existing Firefox profile directory, your sign-ins to Rumble chat for the actor will be saved.
#Otherwise, you will have to log in manuaglly each time you use the bot, or pass username and password.
actor = rumchat_actor.RumbleChatActor(stream_id = STREAM_ID)

#Register an action to be called on every message
actor.register_message_action(eat_some_cheese)

#Register a command via the ChatCommand class
actor.register_command(rumchat_actor.commands.ChatCommand(name = "hi", actor = actor, target = lambda message, actor: actor.send_message(f"Hello, @{message.user.username}!")))

#Register a command via a callable
actor.register_command(name = "tester", command = lambda message, actor: print(f"Test command run by {message.user.username}"))

#Run the bot continuously
actor.mainloop()

S.D.G."""

from getpass import getpass
import textwrap
import time
import threading
from cocorum import RumbleAPI
from cocorum.ssechat import SSEChat
import selenium
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from . import actions, commands, misc, utils, static

class RumbleChatActor():
    """Actor that interacts with Rumble chat"""
    def __init__(self, init_message = "Hello, Rumble!", ignore_users = ["TheRumbleBot"], **kwargs):
        """Instance this object, register all chat commands and message actions, then call its mainloop() method.
    stream_id: The stream ID you want to connect to. Defaults to latest livestream
    init_message: What to say when the actor starts up.
    profile_dir: The Firefox profile directory to use. Defaults to temp (sign-in not saved).
    username: The username to log in with. Defaults to manual entry.
    password: The password to log in with. Defaults to manual entry.
    api_url: The Rumble Live Stream API URL with your key (or RumBot's passthrough).
        Defaults to no Live Stream API access.
    streamer_username: The username of the person streaming.
        Defaults to Live Stream API username or manually requested if needed.
    streamer_channel: The channel doing the livestream, if it is being streamed on a channel.
        Defaults to Live Stream API channel or manually requested if needed.
    is_channel_stream: Bool, if the livestream is on a channel or not.
        Defaults to automatic determination if possible.
    streamer_main_page_url: The URL of the streamer's main page.
        Defaults to automatic determination if possible.
    ignore_users: List of usernames, will ignore all their messages.
    invalid_command_respond: Bool, sets if we should post an error message if a command was invalid.
        Defaults to False.
    browser_head: Display a head for the Firefox process. Defaults to false."""

        #The info of the person streaming
        self.__streamer_username = kwargs.get("streamer_username")
        assert isinstance(self.__streamer_username, str) or self.__streamer_username is None, \
            f"Streamer username must be str or None, not {type(self.__streamer_username)}"

        self.__streamer_channel = kwargs.get("streamer_channel")
        assert isinstance(self.__streamer_channel, str) or self.__streamer_channel is None, \
            f"Streamer channel name must be str or None, not {type(self.__streamer_channel)}"

        self.__is_channel_stream = kwargs.get("is_channel_stream")
        assert isinstance(self.__is_channel_stream, bool) or self.__is_channel_stream is None, \
            f"Argument is_channel_stream must be bool or None, not {type(self.__is_channel_stream)}"

        self.__streamer_main_page_url = kwargs.get("streamer_main_page_url")
        assert isinstance(self.__streamer_main_page_url, str) or self.__streamer_main_page_url is None, \
            f"Argument streamer_main_page_url must be str or None, not {type(self.__is_channel_stream)}"

        #Get Live Stream API
        if "api_url" in kwargs:
            self.rum_api = RumbleAPI(kwargs["api_url"])
        else:
            self.rum_api = None

        #A stream ID was passed
        if "stream_id" in kwargs:
            self.stream_id, self.stream_id_b10 = utils.stream_id_36_and_10(kwargs["stream_id"])

            #It is not our livestream or we have no Live Stream API,
            #so LS API functions are not available
            if not self.rum_api or self.stream_id not in self.rum_api.livestreams:
                self.api_stream = None

            #It is our livestream, we can use the Live Stream API
            else:
                self.api_stream = self.rum_api.livestreams[self.stream_id]

        #A stream ID was not passed
        else:
            assert self.rum_api, "Cannot auto-find stream ID without a Live Stream API url"
            self.api_stream = self.rum_api.latest_livestream

            #At least one live stream must be shown on the API
            assert self.api_stream, "No stream ID was passed and you are not live"

            self.stream_id = self.api_stream.stream_id
            self.stream_id_b10 = utils.stream_id_36_to_10(self.stream_id)

        #Get SSE chat and empty the mailbox
        self.ssechat = SSEChat(stream_id = self.stream_id)
        self.ssechat.clear_mailbox()

        #Set browser profile directory if we have one
        options = webdriver.FirefoxOptions()
        if "profile_dir" in kwargs:
            options.add_argument("-profile")
            options.add_argument(kwargs["profile_dir"])

        #Set browser to headless mode, unless otherwise specified
        if not kwargs.get("browser_head"):
            options.add_argument("--headless")

        #Get browser
        self.driver = webdriver.Firefox(options)
        self.driver.minimize_window()
        self.driver.get(static.URI.chat_popout.format(stream_id_b10 = self.ssechat.stream_id_b10))
        assert "Chat" in self.driver.title, "Failed to load chat page: Title does not contain 'Chat'"

        #Close the premium banner if it is there
        utils.close_premium_banner(self.driver)

        #Get the login credentials from arguments, or None if they were not passed
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

        #We can get the username from the Rumble Live Stream API
        if not self.username and self.rum_api:
            self.username = self.rum_api.username
            print("Actor username obtained from Live Stream API:", self.username)

        #Sign in to chat, unless we are already. While there is a sign-in button...
        first_time = True
        while sign_in_buttn := self.get_sign_in_button():
            #First time going around this loop
            if first_time:
                #Only click the sign-in button the first time, as the sign-in dialog background blur overlay obscures it
                sign_in_buttn.click()

                #Wait for sign-in dialog to appear
                WebDriverWait(self.driver, static.Driver.wait_timeout).until(
                    EC.visibility_of_element_located((By.ID, "login-username")),
                    "Timed out waiting for sign-in dialouge"
                    )

                #Get the credentials entry fields
                uname_field = self.driver.find_element(By.ID, "login-username")
                password_field = self.driver.find_element(By.ID, "login-password")

            #Login failed
            else:
                print("Error. Login failed with provided credentials.")
                self.username = None
                self.password = None

                uname_field.clear()
                password_field.clear()

            #Ask user for credentials as needed
            if not self.username:
                self.username = input("Actor username: ")
            if not self.password:
                self.password = getpass("Actor password: ")

            #Enter the credentials
            uname_field.send_keys(self.username + Keys.RETURN)
            password_field.send_keys(self.password + Keys.RETURN)

            first_time = False

            #Wait for signed in loading to complete
            try:
                self.wait_for_chat_input_elem()

            #Sign in did not work
            except selenium.common.exceptions.WebDriverException as e:
                print(e)
                print("Could not get chat input field.")
                assert self.get_sign_in_button(), "Neither sign-in button nor chat input field are usable"

        #Wait for signed in loading to complete
        self.wait_for_chat_input_elem()

        #Ignore these users when processing messages
        self.ignore_users = ignore_users

        #History of the bot's messages so they do not get loop processed
        self.sent_messages = []

        #Messages waiting to be sent
        self.outbox = []

        #Messages that we know are actually raid alerts
        self.known_raid_alert_messages = []

        #Action to be taken when raids occur
        self.__raid_action = print

        #Time that the last message we sent was sent
        self.last_message_send_time = 0

        #Loop condition of the mainloop() and sender_loop() methods
        self.keep_running = True

        #thread to send messages at timed intervals
        self.sender_thread = threading.Thread(target = self._sender_loop, daemon = True)
        self.sender_thread.start()

        #Send an initialization message to get wether we are moderator or not
        self.send_message(init_message)

        #Wait until we get that message
        while (m := self.ssechat.get_message()).user.username != self.username:
            pass

        assert utils.is_staff(m.user), \
            "Actor cannot function without being channel staff"

        #Functions that are to be called on each message,
        #must return False if the message was deleted
        self.message_actions = []

        #Instances of ChatCommand, by name
        self.chat_commands = {}

        #Wether or not to post an error message if an invalid command was called
        self.invalid_command_respond = kwargs.get("invalid_command_respond", False)
        assert isinstance(self.invalid_command_respond, bool), \
            f"Argument invalid_command_respond must be bool, not {type(self.invalid_command_respond)}"

    @property
    def streamer_username(self):
        """The username of the streamer"""
        if not self.__streamer_username:
            #We are the ones streaming
            if self.api_stream:
                self.__streamer_username = self.rum_api.username
            else:
                self.__streamer_username = input("Enter the username of the person streaming: ")

        return self.__streamer_username

    @property
    def streamer_channel(self):
        """The channel of the streamer"""
        #We don't yet have the streamer channel, and this is a channel stream
        if not self.__streamer_channel and self.is_channel_stream:
            #We are the ones streaming, and the API URL is under the channel
            if self.api_stream and self.rum_api.channel_name:
                self.__streamer_channel = self.rum_api.channel_name

            #We are not the ones streaming,
            #or the API URL was not under our channel,
            #and we are sure this is a channel stream
            else:
                self.__streamer_channel = input("Enter the channel of the person streaming: ")

        return self.__streamer_channel

    @property
    def is_channel_stream(self):
        """Is the stream under a channel?"""
        #We do not know yet
        if self.__is_channel_stream is None:
            #We know that this is a channel stream because it showed up in the channel-specific API
            if self.api_stream and self.rum_api.channel_name:
                self.__is_channel_stream = True

            #We will ask the user
            else:
                self.__is_channel_stream = "y" in input("Is this a channel stream? y/[N]:")

        return self.__is_channel_stream

    @property
    def streamer_main_page_url(self):
        """The URL of the main page of the streamer"""
        #We do not yet know the URL
        if not self.__streamer_main_page_url:
            if self.is_channel_stream:
                #This stream is on the API
                if self.api_stream:
                    #We know our channel ID from the API
                    if self.rum_api.channel_id:
                        self.__streamer_main_page_url = static.URI.channel_page.format(channel_name = f"c-{self.rum_api.channel_id}")

                    #Is a channel stream and on the API but API is not for channel, use the user page instead
                    else:
                        self.__streamer_main_page_url = static.URI.user_page.format(username = self.streamer_username)

                #Is not an API stream and we don't know the username
                elif not self.__streamer_username:
                    while not (specified := input("Enter streamer main page URL: ")).startswith(static.URI.rumble_base):
                        pass
                    self.__streamer_main_page_url = specified

            #Not a channel stream, go by username
            else:
                self.__streamer_main_page_url = static.URI.user_page.format(username = self.streamer_username)

        return self.__streamer_main_page_url

    def get_sign_in_button(self):
        """Look for the sign in button"""
        try:
            return self.driver.find_element(By.CLASS_NAME, "chat--sign-in")
        except selenium.common.exceptions.NoSuchElementException:
            print("Could not find sign-in button, already signed in.")
            return None

    def wait_for_chat_input_elem(self):
        """Wait for the chat text input to appear, indicating page load"""
        WebDriverWait(self.driver, static.Driver.wait_timeout).until(
            EC.element_to_be_clickable((By.ID, "chat-message-text-input")),
            "Timed out waiting for chat message field to become usable"
            )

    def send_message(self, text):
        """Send a message in chat (splits across lines if necessary)"""
        text = static.Message.bot_prefix + text
        assert "\n" not in text, "Message cannot contain newlines"
        assert len(text) < static.Message.max_multi_len, "Message is too long"
        for subtext in textwrap.wrap(text, width = static.Message.max_len):
            self.outbox.append(subtext)
            print("💬:", subtext)

    def _sender_loop(self):
        """Constantly check our outbox and send any messages in it"""
        while self.keep_running:
            #We have messages to send and it is time to send one
            if self.outbox and time.time() - self.last_message_send_time > static.Message.send_cooldown:
                self.__send_message(self.outbox.pop(0))
            time.sleep(0.1)

    def __send_message(self, text):
        """Send a message in chat"""
        assert len(text) < static.Message.max_len, \
            f"Message with prefix cannot be longer than {static.Message.max_len} characters"

        self.sent_messages.append(text)
        self.last_message_send_time = time.time()
        self.driver.find_element(By.ID, "chat-message-text-input").send_keys(text)
        self.driver.find_element(By.CLASS_NAME, "chat--send").click()

    def hover_element(self, element):
        """Hover over a selenium element"""
        ActionChains(self.driver).move_to_element(element).perform()

    def open_moderation_menu(self, message):
        """Open the moderation menu of a message"""

        #The passed message was a li element
        if isinstance(message, webdriver.remote.webelement.WebElement) and message.tag_name == "li":
            message_li = message
            message_id = message_li.get_attribute("data-message-id")

        #Find the message by ID
        elif isinstance(message, int):
            message_id = message
            message_li = self.driver.find_element(
                By.XPATH,
                "//li[@class='chat-history--row js-chat-history-item']" +
                f"[@data-message-id='{message_id}']"
                )

        #The message has a message ID attribute
        elif hasattr(message, "message_id"):
            message_id = message.message_id
            message_li = self.driver.find_element(
                By.XPATH,
                "//li[@class='chat-history--row js-chat-history-item']" +
                f"[@data-message-id='{message_id}']"
                )

        #Not a valid message type
        else:
            raise TypeError("Message must be ID, li element, or have message_id attribute")

        if message_id in self.known_raid_alert_messages:
            print("Cannot open moderation menu: Is a raid message.")
            return None

        #Hover over the message
        self.hover_element(message_li)
        #Find the moderation menu
        try:
            menu_bttn = message_li.find_element(
                By.XPATH,
                ".//button[@class='js-moderate-btn chat-history--kebab-button']"
                )
        except selenium.common.exceptions.NoSuchElementException:
            print("Cannot open moderation menu: Could not find moderation button.")
            return None

        #Click the moderation menu button
        menu_bttn.click()

        return message_id

    def delete_message(self, message):
        """Delete a message in the chat"""
        m_id = self.open_moderation_menu(message)
        if m_id is None:
            print("Could not delete message.")
            return

        del_bttn = self.driver.find_element(
            By.XPATH,
            f"//button[@class='cmi js-btn-delete-current'][@data-message-id='{m_id}']"
            )

        del_bttn.click()

        #Wait for the confirmation to appear
        WebDriverWait(self.driver, static.Driver.wait_timeout).until(
            EC.alert_is_present(),
            "Timed out waiting for deletion confirmation dialouge to appear"
            )

        #Confirm the confirmation dialog
        Alert(self.driver).accept()

    def mute_by_message(self, message, mute_level = "5"):
        """Mute a user by message"""
        m_id = self.open_moderation_menu(message)
        if m_id is None:
            print("Could not mute by message.")
            return

        timeout_bttn = self.driver.find_element(
            By.XPATH,
            f"//button[@class='{static.Moderation.mute_levels[mute_level]}']"
            )

        timeout_bttn.click()

    def mute_by_appearname(self, name, mute_level = "5"):
        """Mute a user by the name they are appearing with"""
        #Find any chat message by this user
        message_li = self.driver.find_element(
            By.XPATH,
            f"//li[@class='chat-history--row js-chat-history-item'][@data-username='{name}']"
            )

        self.mute_by_message(message = message_li, mute_level = mute_level)

    def pin_message(self, message):
        """Pin a message by ID or li element"""
        m_id = self.open_moderation_menu(message)
        if m_id is None:
            print("Could not pin message.")
            return

        pin_bttn = self.driver.find_element(By.XPATH, "//button[@class='cmi js-btn-pin-current']")
        pin_bttn.click()

    def unpin_message(self):
        """Unpin the currently pinned message"""
        try:
            unpin_bttn = self.driver.find_element(
                By.XPATH,
                "//button[@data-js='remove_pinned_message_button']"
                )

        except selenium.common.exceptions.NoSuchElementException:
            return False #No message was pinned

        unpin_bttn.click()
        return True

    def quit(self):
        """Shut down everything"""
        self.keep_running = False
        self.driver.quit()
        # TODO how to close an SSEClient?
        # self.ssechat.client.close()

    def __run_if_command(self, message):
        """Check if a message is a command, and run it if so"""
        #Not a command
        if not message.text.startswith(static.Message.command_prefix):
            return

        #Get command name
        name = message.text.split()[0].removeprefix(static.Message.command_prefix)

        #Is not a valid command
        if name not in self.chat_commands:
            if self.invalid_command_respond:
                self.send_message(f"@{message.user.username} That is not a registered command.")
            return

        self.chat_commands[name].call(message)

    def register_command(self, command, name = None, help_message = None):
        """Register a command"""
        #Is a ChatCommand instance
        if isinstance(command, commands.ChatCommand):
            assert not name or name == command.name, \
                "ChatCommand instance has different name than one passed"
            self.chat_commands[command.name] = command

        #Is a callable
        elif callable(command):
            assert name, "Name cannot be None if command is a callable"
            assert " " not in name, "Name cannot contain spaces"
            self.chat_commands[name] = commands.ChatCommand(name = name, actor = self, target = command)

        else:
            raise TypeError(f"Command must be of type ChatCommand or a callable, not {type(command)}.")

        #A specific help message was provided
        if help_message:
            assert not self.chat_commands[name].help_message, "ChatCommand has internal help message already set, cannot override"
            self.chat_commands[name].help_message = help_message

    def register_message_action(self, action):
        """Register an action to be run on every message
    - Action must be a callable or have an action() attribute
    - Action will be passed cocorum.ssechat.SSEChatMessage() and this actor
    - Action should return False if the message survived the action
    - Action should return True if the message was deleted by the action"""

        if hasattr(action, "action"):
            action = action.action

        assert callable(action), "Action must be a callable or have an action() attribute"
        self.message_actions.append(action)

    @property
    def raid_action(self):
        """The callable we are supposed to run on raids"""
        return self.__raid_action

    @raid_action.setter
    def raid_action(self, new_action):
        assert callable(new_action), "Raid action must be a callable"
        self.__raid_action = new_action

    def __process_message(self, message):
        """Process a single SSE Chat message"""
        #Ignore messages that match ones we sent before
        if message.text in self.sent_messages:
            return

        #the message is actually a raid alert, take raid action on it, nothing more
        if message.raid_notification:
            self.known_raid_alert_messages.append(message)
            self.raid_action(message)
            return

        #If the message is from the same account as us, consider it in message send cooldown
        if message.user.username == self.username:
            self.last_message_send_time = max((self.last_message_send_time, message.time))

        #Ignore messages that are in the ignore_users list
        if message.user.username in self.ignore_users:
            return

        for action in self.message_actions:
            #The message got deleted, possibly by this action
            if message.message_id in self.ssechat.deleted_message_ids or action(message, self):
                return

        self.__run_if_command(message)

    def mainloop(self):
        """Run the actor forever"""
        try:
            while self.keep_running:
                m = self.ssechat.get_message()
                if not m: #Chat has closed
                    self.keep_running = False
                    return
                self.__process_message(m)

        except KeyboardInterrupt:
            print("KeyboardInterrupt shutdown.")
            self.quit()
