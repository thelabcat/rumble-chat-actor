#!/usr/bin/env python3
"""Rumble Chat Actor

Automatically interact with your Rumble livestream chats.
S.D.G."""

import textwrap
import time
import threading
from cocorum import RumbleAPI, utils
from cocorum.ssechat import SSEChat
import selenium
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

#How long to wait maximum for a condition to be true in the browser
BROWSER_WAIT_TIMEOUT = 30

#How long to wait between sending messages
SEND_MESSAGE_COOLDOWN = 3

#Popout chat url. Format with stream_id_b10
CHAT_URL = "https://rumble.com/chat/popup/{stream_id_b10}"

#Rumble user URL. Format with username
USER_URL = "https://rumble.com/user/{username}"

#Rumble channel URL. Format with channel_name
CHANNEL_URL = "https://rumble.com/c/{channel_name}"

#Maximum chat message length
MAX_MESSAGE_LEN = 200

#Message split across multiple lines must not be longer than this
MAX_MULTIMESSAGE_LEN = 1000

#Prefix to all actor messages
BOT_MESSAGE_PREFIX = "🤖: "

#How commands always start
COMMAND_PREFIX = "!"

#Levels of mute to discipline a user with
MUTE_LEVELS = {
    "5" : "cmi js-btn-mute-current-5",
    "stream" : "cmi js-btn-mute-current",
    "forever" : "cmi js-btn-mute-for-account",
    }

class ChatCommand():
    """A chat command, internal use only"""
    def __init__(self, name, actor, cooldown = SEND_MESSAGE_COOLDOWN, amount_cents = 0, exclusive = False, allowed_badges = ["subscriber"], whitelist_badges = ["moderator"], target = None):
        """name: The !name of the command
    actor: The RumleChatActor host object
    amount_cents: The minimum cost of the command. Defaults to free
    exclusive: If this command can only be run by users with allowed badges. Defaults to False
    allowed_badges: Badges that are allowed to run this command (if it is exclusive).
        Defaults to subscribers, admin is added internally.
    whitelist_badges: Badges which if borne give the user free-of-charge command access
    target: The command function(message, actor) to call. Defaults to self.run"""
        assert " " not in name, "Name cannot contain spaces"
        self.name = name
        self.actor = actor
        assert cooldown >= SEND_MESSAGE_COOLDOWN, \
            f"Cannot set a cooldown shorter than {SEND_MESSAGE_COOLDOWN}"

        self.cooldown = cooldown
        self.amount_cents = amount_cents #Cost of the command
        self.exclusive = exclusive
        self.allowed_badges = ["admin"] + allowed_badges #Admin can always run any command
        self.whitelist_badges = ["admin"] + whitelist_badges #Admin always has free-of-charge usage
        self.last_use_time = 0 #Last time the command was called
        self.target = target

    def call(self, message):
        """The command was called"""
        #this command is exclusive, and the user does not have the required badge
        if self.exclusive and \
            not (True in [badge.slug in self.allowed_badges for badge in message.user.badges]):

            self.actor.send_message(f"@{message.user.username} That command is exclusive to: " +
                                    ", ".join(self.allowed_badges)
                                    )

            return

        #The command is still on cooldown
        if (curtime := time.time()) - self.last_use_time < self.cooldown:
            self.actor.send_message(
                f"@{message.user.username} That command is still on cooldown. " +
                f"Try again in {int(self.last_use_time + self.cooldown - curtime + 0.5)} seconds."
                )

            return

        #the user did not pay enough for the command and they do not have a free pass
        if message.rant_price_cents < self.amount_cents and \
            not (True in [badge.slug in self.whitelist_badges for badge in message.user.badges]):

            self.actor.send_message("@" + message.user.username +
                                    f"That command costs ${self.amount_cents/100:.2f}."
                                    )
            return

        #the command was called successfully
        self.run(message)

        #Mark the last use time for cooldown
        self.last_use_time = time.time()

    def run(self, message):
        """Dummy run method"""
        if self.target:
            self.target(message, self.actor)
            return

        #Run method was never defined
        self.actor.send_message("@" + message.user.username +
                                "Hello, this command never had a target defined. :-)"
                                )

class RumbleChatActor():
    """Actor that interacts with Rumble chat"""
    def __init__(self, init_message = "Hello, Rumble!", ignore_users = ["TheRumbleBot"], **kwargs):
        """stream_id: The stream ID you want to connect to. Defaults to latest livestream
    init_message: What to say when the actor starts up.
    profile_dir: The Firefox profile directory to use. Defaults to temp (sign-in not saved)
    credentials: The (username, password) to log in with. Defaults to manual log in
    api_url: The Rumble Live Stream API URL with your key (or RumBot's passthrough).
        Defaults to no Live Stream API access
    streamer_username: The username of the person streaming.
        Defaults to Live Stream API username or manually requested if needed
    streamer_channel: The channel doing the livestream, if it is being streamed on a channel.
        Defaults to Live Stream API channel or manually requested if needed
    is_channel_stream: Bool, if the livestream is on a channel or not
    ignore_users: List of usernames, will ignore all their messages
    invalid_command_respond: Bool, sets if we should post an error message if a command was invalid.
        Defaults to False."""

        #The info of the person streaming
        self.__streamer_username = kwargs["streamer_username"] if "streamer_username" in kwargs else None
        assert isinstance(self.__streamer_username, str) or self.__streamer_username is None, \
            f"Streamer username must be str or None, not {type(self.__streamer_username)}"

        self.__streamer_channel = kwargs["streamer_channel"] if "streamer_channel" in kwargs else None
        assert isinstance(self.__streamer_channel, str) or self.__streamer_channel is None, \
            f"Streamer channel name must be str or None, not {type(self.__streamer_channel)}"

        self.__is_channel_stream = kwargs["is_channel_stream"] if "is_channel_stream" in kwargs else None
        assert isinstance(self.__is_channel_stream, bool) or self.__is_channel_stream is None, \
            f"Argument is_channel_stream must be bool or None, not {type(self.__is_channel_stream)}"

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

        #Get browser
        self.browser = webdriver.Firefox(options = options)
        self.browser.minimize_window()
        self.browser.get(CHAT_URL.format(stream_id_b10 = self.ssechat.stream_id_b10))
        assert "Chat" in self.browser.title

        #Sign in to chat, unless we are already. While there is a sign-in button...
        while sign_in_buttn := self.get_sign_in_button():
            #We have credentials
            if "username" in kwargs and "password" in kwargs:
                sign_in_buttn.click()
                WebDriverWait(self.browser, BROWSER_WAIT_TIMEOUT).until(
                    EC.visibility_of_element_located((By.ID, "login-username")),
                    "Timed out waiting for sign-in dialouge"
                    )

                uname_field = self.browser.find_element(By.ID, "login-username")
                uname_field.send_keys(kwargs["username"] + Keys.RETURN)
                self.browser.find_element(By.ID, "login-password").send_keys(kwargs["password"] + Keys.RETURN)

            #We do not have credentials, ask for manual sign in
            self.browser.maximize_window()
            input("Please log in at the browser, then press enter here.")

        #Wait for signed in loading to complete
        WebDriverWait(self.browser, BROWSER_WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "chat-message-text-input")),
            "Timed out waiting for chat message field to become usable"
            )


        #Find our username
        if "username" in kwargs:
            self.username = kwargs["username"]
        elif self.rum_api:
            self.username = self.rum_api.username
        else:
            self.username = None
            while not self.username:
                self.username = input("Enter the username the actor is using: ")

        #Ignore these users when processing messages
        self.ignore_users = ignore_users

        #History of the bot's messages so they do not get loop processed
        self.sent_messages = []

        #Messages waiting to be sent
        self.outbox = []

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

        assert "moderator" in m.user.badges or "admin" in m.user.badges, \
            "Actor cannot function without being a moderator"

        #Functions that are to be called on each message,
        #must return False if the message was deleted
        self.message_actions = []

        #Instances of RumbleChatCommand, by name
        self.chat_commands = {}

        #Wether or not to post an error message if an invalid command was called
        self.invalid_command_respond = kwargs["invalid_command_respond"] if "invalid_command_respond" in kwargs else False
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
        if self.is_channel_stream:
            return CHANNEL_URL.format(channel_name = self.streamer_channel.replace(" ", ""))

        return USER_URL.format(username = self.streamer_username)

    def get_sign_in_button(self):
        """Look for the sign in button"""
        try:
            return self.browser.find_element(By.CLASS_NAME, "chat--sign-in")
        except selenium.common.exceptions.NoSuchElementException:
            print("Could not find sign-in button, already signed in.")
            return None

    def send_message(self, text):
        """Send a message in chat (splits across lines if necessary)"""
        text = BOT_MESSAGE_PREFIX + text
        assert "\n" not in text, "Message cannot contain newlines"
        assert len(text) < MAX_MULTIMESSAGE_LEN, "Message is too long"
        for subtext in textwrap.wrap(text, width = MAX_MESSAGE_LEN):
            self.outbox.append(subtext)

    def _sender_loop(self):
        """Constantly check our outbox and send any messages in it"""
        while self.keep_running:
            #We have messages to send and it is time to send one
            if self.outbox and time.time() - self.last_message_send_time > SEND_MESSAGE_COOLDOWN:
                self.__send_message(self.outbox.pop(0))
            time.sleep(0.1)

    def __send_message(self, text):
        """Send a message in chat"""
        assert len(text) < MAX_MESSAGE_LEN, \
            f"Message with prefix cannot be longer than {MAX_MESSAGE_LEN} characters"

        self.sent_messages.append(text)
        self.last_message_send_time = time.time()
        self.browser.find_element(By.ID, "chat-message-text-input").send_keys(text + Keys.RETURN)

    def hover_element(self, element):
        """Hover over a selenium element"""
        ActionChains(self.browser).move_to_element(element).perform()

    def open_moderation_menu(self, message):
        """Open the moderation menu of a message"""

        #The passed message was a li element
        if isinstance(message, webdriver.remote.webelement.WebElement) and message.tag_name == "li":
            message_li = message
            message_id = message_li.get_attribute("data-message-id")

        #Find the message by ID
        elif isinstance(message, int):
            message_id = message
            message_li = self.browser.find_element(
                By.XPATH,
                "//li[@class='chat-history--row js-chat-history-item']" +
                f"[@data-message-id='{message_id}']"
                )

        #The message has a message ID attribute
        elif hasattr(message, "message_id"):
            message_id = message.message_id
            message_li = self.browser.find_element(
                By.XPATH,
                "//li[@class='chat-history--row js-chat-history-item']" +
                f"[@data-message-id='{message_id}']"
                )

        #Not a valid message type
        else:
            raise TypeError("Message must be ID, li element, or have message_id attribute")

        #Hover over the message
        self.hover_element(message_li)
        #Find the moderation menu
        menu_bttn = message_li.find_element(
            By.XPATH,
            ".//button[@class='js-moderate-btn chat-history--kebab-button']"
            )
        #Click the moderation menu button
        menu_bttn.click()

        return message_id

    def delete_message(self, message):
        """Delete a message in the chat"""
        m_id = self.open_moderation_menu(message)
        del_bttn = self.browser.find_element(
            By.XPATH,
            f"//button[@class='cmi js-btn-delete-current'][@data-message-id='{m_id}']"
            )

        del_bttn.click()

        #Wait for the confirmation to appear
        WebDriverWait(self.browser, BROWSER_WAIT_TIMEOUT).until(
            EC.alert_is_present(),
            "Timed out waiting for deletion confirmation dialouge to appear"
            )

        #Confirm the confirmation dialog
        Alert(self.browser).accept()

    def mute_by_message(self, message, mute_level = "5"):
        """Mute a user by message"""
        self.open_moderation_menu(message)
        timeout_bttn = self.browser.find_element(
            By.XPATH,
            f"//button[@class='{MUTE_LEVELS[mute_level]}']"
            )

        timeout_bttn.click()

    def mute_by_appearname(self, name, mute_level = "5"):
        """Mute a user by the name they are appearing with"""
        #Find any chat message by this user
        message_li = self.browser.find_element(
            By.XPATH,
            f"//li[@class='chat-history--row js-chat-history-item'][@data-username='{name}']"
            )

        self.mute_by_message(message = message_li, mute_level = mute_level)

    def pin_message(self, message):
        """Pin a message by ID or li element"""
        self.open_moderation_menu(message)
        pin_bttn = self.browser.find_element(By.XPATH, "//button[@class='cmi js-btn-pin-current']")
        pin_bttn.click()

    def unpin_message(self):
        """Unpin the currently pinned message"""
        try:
            unpin_bttn = self.browser.find_element(
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
        self.browser.quit()
        # TODO how to close an SSEClient?
        # self.ssechat.client.close()

    def __run_if_command(self, message):
        """Check if a message is a command, and run it if so"""
        #Not a command
        if not message.text.startswith(COMMAND_PREFIX):
            return

        #Get command name
        name = message.text.split()[0].removeprefix(COMMAND_PREFIX)

        #Is not a valid command
        if name not in self.chat_commands:
            if self.invalid_command_respond:
                self.send_message(f"@{message.user.username} That is not a registered command.")
            return

        self.chat_commands[name].call(message)

    def register_command(self, command, name = None):
        """Register a command"""
        #Is a ChatCommand instance
        if isinstance(command, ChatCommand):
            assert not name or name == command.name, \
                "ChatCommand instance has different name than one passed"
            self.chat_commands[command.name] = command

        #Is a callable
        elif callable(command):
            assert name, "Name cannot be None if command is a callable"
            assert " " not in name, "Name cannot contain spaces"
            self.chat_commands[name] = ChatCommand(name = name, actor = self, target = command)

        else:
            raise TypeError(f"Command must be of type ChatCommand or a callable, not {type(command)}.")

    def register_message_action(self, action):
        """Register an action callable to be run on every message
    - Action will be passed cocorum.ssechat.SSEChatMessage() and this actor
    - Action should return True if the message survived the action
    - Action should return False if the message was deleted by the action"""
        assert callable(action), "Action must be a callable"
        self.message_actions.append(action)

    def __process_message(self, message):
        """Process a single SSE Chat message"""
        #Ignore messages that match ones we sent before
        if message.text in self.sent_messages:
            return

        #If the message is from the same account as us, consider it in message send cooldown
        if message.user.username == self.username:
            self.last_message_send_time = max((self.last_message_send_time, message.time))

        #Ignore messages that are in the ignore_users list
        if message.user.username in self.ignore_users:
            return

        for action in self.message_actions:
            #The message got deleted, possibly by this action
            if message.message_id in self.ssechat.deleted_message_ids or not action(message, self):
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
