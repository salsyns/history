import os
import json
import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# Retrieve values from environment variables
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
owner_id = int(os.getenv('OWNER_ID'))  # Convert to int if OWNER_ID is an integer
string_session = os.getenv('STRING_SESSION')

# Initialize TelegramClient with StringSession
client = TelegramClient(string_session, api_id, api_hash)

# Start the client with bot token
client.start(bot_token=bot_token)

# File to store user history
history_file = 'user_history.json'

# Function to load user history from file
def load_history():
    try:
        with open(history_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Function to save user history to file
def save_history(history):
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

# Load user history on startup
user_history = load_history()

# Function to resize profile picture
def resize_image(photo_path):
    try:
        image = Image.open(photo_path)
        size = (100, 100)  # Adjust size as needed
        image.thumbnail(size)
        image.save(photo_path)
    except Exception as e:
        print(f"Error resizing image: {e}")

# Handler for /start command
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        'Welcome! Use the /check <user_id> command to check user history.',
        buttons=[
            [Button.url('Add to Group', 'https://t.me/sanghistory_bot?startgroup=true')]
        ]
    )

# Handler for /check <user_id> command
@client.on(events.NewMessage(pattern='/check'))
async def handler(event):
    if event.is_private or event.is_group:
        try:
            user_id = event.message.message.split()[1]
        except IndexError:
            await event.reply("Please provide the user ID to check. Example: /check 123456789")
            return
        
        if user_id in user_history:
            history = user_history[user_id]
            names = history.get('names', [])
            usernames = history.get('usernames', [])
            photos = history.get('photos', [])

            response = f"👤 History for {user_id}\n\nNames\n"
            for i, record in enumerate(names, 1):
                response += f"{i}. [{record['timestamp']}] {record['name']}\n"
            
            response += "\nUsernames\n"
            for i, record in enumerate(usernames, 1):
                response += f"{i}. [{record['timestamp']}] @{record['username']}\n"
            
            response += "\nPhotos\n"
            for i, record in enumerate(photos, 1):
                response += f"{i}. [{record['timestamp']}] {record['photo_path']}\n"
        else:
            response = f"No history found for ID {user_id}."

        await event.reply(response)

# Handler for /listusername command (only for owner)
@client.on(events.NewMessage(pattern='/listusername'))
async def list_usernames(event):
    if event.sender_id == owner_id:
        response = "👥 List of Users Using the Bot (Username):\n\n"
        for user_id, history in user_history.items():
            usernames = history.get('usernames', [])
            if usernames:
                latest_username = usernames[-1]['username']
                response += f"- @{latest_username} ({user_id})\n"
        await event.reply(response)
    else:
        await event.reply("You are not authorized to use this command.")

# Handler to save new user information
@client.on(events.NewMessage)
async def save_user_info(event):
    if event.is_private or event.is_group:
        sender = await event.get_sender()
        user_id = str(sender.id)
        username = sender.username
        name = sender.first_name
        photo_path = f'{user_id}_photo.jpg'

        current_time = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S')

        if user_id not in user_history:
            user_history[user_id] = {'names': [], 'usernames': [], 'photos': []}

        if name and (not user_history[user_id]['names'] or user_history[user_id]['names'][-1]['name'] != name):
            user_history[user_id]['names'].append({
                'name': name,
                'timestamp': current_time
            })

        if username and (not user_history[user_id]['usernames'] or user_history[user_id]['usernames'][-1]['username'] != username):
            user_history[user_id]['usernames'].append({
                'username': username,
                'timestamp': current_time
            })

        # Download and save profile photo if changed
        photo = await client.download_profile_photo(sender, file=photo_path, download_big=False)
        if photo and (not user_history[user_id]['photos'] or user_history[user_id]['photos'][-1]['photo_path'] != photo_path):
            resize_image(photo_path)
            user_history[user_id]['photos'].append({
                'photo_path': photo_path,
                'timestamp': current_time
            })

        save_history(user_history)

# Run the client
client.run_until_disconnected()
