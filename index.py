import os
import json
import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.types import InputPeerEmpty, ChannelParticipantsRecent


# Load environment variables from .env file
load_dotenv()



# Retrieve values from environment variables
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
owner_id = int(os.getenv('OWNER_ID'))  # Convert to int if OWNER_ID is an integer
string_session = os.getenv('STRING_SESSION')

# Initialize TelegramClient with StringSession
client = TelegramClient(StringSession(string_session), api_id, api_hash)

# Start the client with bot token
client.start(bot_token=bot_token)

# File to store user history
history_file = 'user_history.json'

# Function to load user history from file
def load_history():
    try:
        with open(history_file, 'r') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
            else:
                return {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

# Function to save user history to file
def save_history(history):
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

# Load user history on startup
user_history = load_history()

# Function to send notification to all groups where bot and user are both members
async def send_notification_to_all_groups(user_id, change_type, old_value, new_value):
    try:
        dialogs = await client(GetDialogsRequest(
            offset_date=None, 
            offset_id=0, 
            offset_peer=InputPeerEmpty(), 
            limit=100, 
            hash=0
        ))
        
        for dialog in dialogs.dialogs:
            if hasattr(dialog.peer, 'channel_id') or hasattr(dialog.peer, 'chat_id'):
                chat_id = dialog.peer.channel_id if hasattr(dialog.peer, 'channel_id') else dialog.peer.chat_id
                try:
                    participants = await client.get_participants(chat_id)
                    user_in_group = any(participant.id == int(user_id) for participant in participants)
                    bot_in_group = any(participant.id == (await client.get_me()).id for participant in participants)
                    
                    if user_in_group and bot_in_group:
                        await client.send_message(chat_id, f"User ({user_id}) changed {change_type} from {old_value} to {new_value}")
                except Exception as e:
                    print(f"Error fetching participants for {chat_id}: {e}")

    except Exception as e:
        print(f"Error sending notification: {e}")

# Handler for /start command
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        'Hi!\n Use /help for all commands.',
        buttons=[
            [Button.url('Add to Group', 'https://t.me/sanghistory_bot?startgroup=true')]
        ]
    )

# Handler for /help command
@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    commands = [
        "/start - Start using the bot",
        "/check <user_id> or /check <@username> - Check user history",
        "/listusername - List all tracked usernames",
        "/ping - Measure bot response time",
        "/getgroup <group_id> - Get information about a group"
        # Add more commands as needed
    ]
    response = "Here are the available commands:\n\n"
    response += "\n".join(commands)
    await event.reply(response)

# Handler for /check <user_id|username> command
@client.on(events.NewMessage(pattern='/check'))
async def handler(event):
    if event.is_private or event.is_group:
        try:
            if event.is_reply:
                reply_message = await event.get_reply_message()
                user_id = str(reply_message.sender_id)
            else:
                query = event.message.message.split()[1]
                if query.startswith('@'):
                    username = query[1:]
                    user_id = None
                    for uid, history in user_history.items():
                        usernames = history.get('usernames', [])
                        if usernames and usernames[-1]['username'] == username:
                            user_id = uid
                            break
                    if user_id is None:
                        await event.reply(f"History not found!")
                        return
                else:
                    user_id = query

        except IndexError:
            await event.reply("Please provide the user ID or username to check. Example: /check 123456789 or /check @username")
            return

        if user_id in user_history:
            history = user_history[user_id]
            names = history.get('names', [])
            usernames = history.get('usernames', [])

            response = f"👤 **History for** {user_id}\n\n**Names:**\n"
            for i, record in enumerate(names, 1):
                response += f"{i}. [{record['timestamp']}] {record['name']}\n"

            response += "\n**Usernames:**\n"
            for i, record in enumerate(usernames, 1):
                response += f"{i}. [{record['timestamp']}] @{record['username']}\n"

        else:
            response = f"History not found!"

        await event.reply(response)

# Handler for /listusername command (only for owner)
@client.on(events.NewMessage(pattern='/listusername'))
async def list_usernames(event):
    if event.sender_id == owner_id:
        response = "👥 **List Users:**\n\n"
        for user_id, history in user_history.items():
            usernames = history.get('usernames', [])
            if usernames:
                response += f"- @{usernames[-1]['username']} ({user_id})\n"
        await event.reply(response)
    else:
        await event.reply("You are not authorized to use this command.")

# Handler to save new user information and send notifications on updates
@client.on(events.NewMessage)
async def save_user_info(event):
    if event.is_private or event.is_group:
        sender = await event.get_sender()
        user_id = str(sender.id)
        username = sender.username
        name = sender.first_name

        current_time = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S')

        if user_id not in user_history:
            user_history[user_id] = {'names': [], 'usernames': []}

        # Check if name or username has changed
        name_changed = False
        username_changed = False

        if name and (not user_history[user_id]['names'] or user_history[user_id]['names'][-1]['name'] != name):
            old_name = user_history[user_id]['names'][-1]['name'] if user_history[user_id]['names'] else ''
            user_history[user_id]['names'].append({
                'name': name,
                'timestamp': current_time
            })
            name_changed = True

        if username and (not user_history[user_id]['usernames'] or user_history[user_id]['usernames'][-1]['username'] != username):
            old_username = user_history[user_id]['usernames'][-1]['username'] if user_history[user_id]['usernames'] else ''
            user_history[user_id]['usernames'].append({
                'username': username,
                'timestamp': current_time
            })
            username_changed = True

        save_history(user_history)

        # If name or username has changed, send notification
        if name_changed:
            await send_notification_to_all_groups(user_id, 'name', old_name, name)
        if username_changed:
            await send_notification_to_all_groups(user_id, 'username', old_username, username)

# Handler for /ping command to measure response speed
@client.on(events.NewMessage(pattern='/ping'))
async def ping(event):
    if event.is_private or event.is_group:
        start_time = datetime.datetime.now()
        message = await event.respond("Pong!")
        end_time = datetime.datetime.now()
        delta = end_time - start_time
        await message.edit(f"Pong!\nResponse time: {delta.total_seconds() * 1000:.2f} ms")

# Handler for /getgroup command
@client.on(events.NewMessage(pattern=r'/getgroup(\s+\d+)?'))
async def getgroup(event):
    if event.is_group:
        try:
            if event.pattern_match.group(1):
                group_id = int(event.pattern_match.group(1).strip())
                chat = await client.get_entity(group_id)
            else:
                chat = await event.get_chat()
            
            # Fetch full group info
            full_chat = await client(GetFullChannelRequest(chat.id))

            response = (
                f"**Group Information**\n\n"
                f"**Title:** {chat.title}\n"
                f"**ID:** {chat.id}\n"
                f"**Date Created:** {chat.date}\n"
                f"**Link:** {chat.username if chat.username else 'N/A'}\n"
                f"**Description:** {full_chat.full_chat.about}\n"
            )
            await event.reply(response)
        except Exception as e:
            await event.reply(f"An error occurred: {e}")
    else:
        await event.reply("This command can only be used in groups.")

# Handler for /getlistcall command
async def is_user_in_voice_chat(user_id):
    # Placeholder function to check if a user is in a voice chat
    # Replace this with the actual implementation
    return True  # Simulate that user is in voice chat for testing

@client.on(events.NewMessage(pattern='/tagall'))
async def get_list_call_handler(event):
    if event.is_group:
        try:
            # Fetch the chat entity
            chat = await event.get_chat()
            chat_id = chat.id

            # Get recent participants in the chat
            participants = await client(GetParticipantsRequest(
                channel=chat, filter=ChannelParticipantsRecent(), offset=0, limit=2000000, hash=0
            ))

            active_calls = []

            for participant in participants.participants:
                try:
                    user = await client.get_entity(participant.user_id)
                    if await is_user_in_voice_chat(user.id):
                        if user.username:
                            active_calls.append(f"@{user.username}")
                        else:
                            active_calls.append(user.first_name)
                except Exception as e:
                    print(f"Error fetching participant info for {participant.user_id}: {e}")

            if active_calls:
                response = f"**Tagall Members:**\n\n"
                response += "\n".join(active_calls)
            else:
                response = "Not found!."

            await event.reply(response)

        except Exception as e:
            await event.reply(f"An error occurred: {e}")

    else:
        await event.reply("This command can only be used in groups.")



# Start the client event loop
client.run_until_disconnected()
