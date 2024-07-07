import json
import datetime
import os
from telethon import TelegramClient, events, Button
from PIL import Image

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Ambil nilai-nilai dari environment variables
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
owner_id = 1959712188  # ID Pemilik

# Buat dan jalankan client
client = TelegramClient('1BVtsOIsBuxADv1sSdfjlMp5tpgNGVLFooUtXtcAkg-NUjiKqY5FJ5Q2l_HGQvAh_qu6BRQ_X8z5whB1jLKGAoeLiyNbwHN0zFWnimPBgK7iAo9ZvuVV1zxu7lC_jY8RTjKmQDI3ibnpIHEugoaOL7cOywh9Auc5TJ2NtUNSpN0UGbm9q7Iy9Qf1YD3E7WGPZ1X3198fsvtKR30UffHsEgagEL7UntnxNyHNdsku_INCrqz69FMsW4Ri91-UeO7edzwPaVTyQGkukp5Pe378XY6ctu9oFFh-lwAKFXNiprm67VY-MldejaLg40e9xNbIz3NnrFd9B4d-i64tBEu8JVTTKftGFgOU=', api_id, api_hash).start(bot_token=bot_token)

# File untuk menyimpan riwayat pengguna
history_file = 'user_history.json'

# Fungsi untuk memuat riwayat pengguna dari file
def load_history():
    try:
        with open(history_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Fungsi untuk menyimpan riwayat pengguna ke file
def save_history(history):
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

# Memuat riwayat pengguna saat startup
user_history = load_history()

# Fungsi untuk menyesuaikan ukuran foto profil
def resize_image(photo_path):
    try:
        image = Image.open(photo_path)
        size = (100, 100)  # Ubah ukuran sesuai kebutuhan
        image.thumbnail(size)
        image.save(photo_path)
    except Exception as e:
        print(f"Error resizing image: {e}")

# Handler untuk perintah /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        'Selamat datang! Gunakan perintah /cek <user_id> untuk memeriksa riwayat username, nama, dan gambar profil pengguna.',
        buttons=[
            [Button.url('Tambah ke Group', 'https://t.me/YOUR_BOT_USERNAME?startgroup=true')]
        ]
    )

# Handler untuk perintah /cek <user_id>
@client.on(events.NewMessage(pattern='/cek'))
async def handler(event):
    if event.is_private or event.is_group:
        try:
            user_id = event.message.message.split()[1]
        except IndexError:
            await event.reply("Mohon sertakan user ID yang ingin dicek. Contoh: /cek 123456789")
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
            response = f"Tidak ada riwayat untuk ID {user_id}."

        await event.reply(response)

# Handler untuk perintah /listusername (hanya pemilik)
@client.on(events.NewMessage(pattern='/listusername'))
async def list_usernames(event):
    if event.sender_id == owner_id:
        response = "👥 Daftar Pengguna yang Menggunakan Bot (Username):\n\n"
        for user_id, history in user_history.items():
            usernames = history.get('usernames', [])
            if usernames:
                latest_username = usernames[-1]['username']
                response += f"- @{latest_username} ({user_id})\n"
        await event.reply(response)
    else:
        await event.reply("Anda tidak memiliki izin untuk menggunakan perintah ini.")

# Handler untuk menyimpan informasi pengguna baru
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

        # Unduh dan simpan foto profil jika ada perubahan
        photo = await client.download_profile_photo(sender, file=photo_path, download_big=False)
        if photo and (not user_history[user_id]['photos'] or user_history[user_id]['photos'][-1]['photo_path'] != photo_path):
            resize_image(photo_path)
            user_history[user_id]['photos'].append({
                'photo_path': photo_path,
                'timestamp': current_time
            })

        save_history(user_history)

# Jalankan client
client.start()
client.run_until_disconnected()
