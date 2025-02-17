import sqlite3
import os
from telegram import Update, InputMediaAudio
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token - it will be set as an environment variable in Heroku
TOKEN = os.getenv('BOT_TOKEN')

# Initialize the application (for v20+)
application = Application.builder().token(TOKEN).build()

# Database file
DB_FILE = 'bot_db.db'

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_channels (
        user_id INTEGER PRIMARY KEY,
        channels TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS music_files (
                    channel_id TEXT,
                    file_name TEXT,
                    file_id TEXT
                )''')
    conn.commit()
    conn.close()

# Add a user's channel to the database
def add_channel(user_id, channel):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT channels FROM user_channels WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        channels = result[0].split(',')
        if channel not in channels:
            channels.append(channel)
            c.execute('UPDATE user_channels SET channels = ? WHERE user_id = ?', (','.join(channels), user_id))
    else:
        c.execute('INSERT INTO user_channels (user_id, channels) VALUES (?, ?)', (user_id, channel))
    conn.commit()
    conn.close()

# Get the list of channels for a user
def get_channels(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT channels FROM user_channels WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0].split(',') if result else []

# Save music file details to the database
def save_music_file(channel_id, file_name, file_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO music_files (channel_id, file_name, file_id) VALUES (?, ?, ?)', 
              (channel_id, file_name, file_id))
    conn.commit()
    conn.close()

# Function to handle the start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Use /add_channel <channel_username> to add your channel. Then use /search_music <song_name> to find music in your channels.")

# Function to handle adding a channel
async def add_channel_command(update: Update, context: CallbackContext):
    user = update.message.from_user
    if not context.args:
        await update.message.reply_text("Please provide the channel username (e.g., /add_channel @mychannel).")
        return

    channel = context.args[0]
    add_channel(user.id, channel)
    await update.message.reply_text(f"Channel {channel} added to your account. Please add the bot as an admin in your channel.")

# Function to handle the music search
async def search_music(update: Update, context: CallbackContext):
    user = update.message.from_user
    query = ' '.join(context.args)
    
    if not query:
        await update.message.reply_text("Please provide the name of the song.")
        return
    
    # Search the music files database for matching files
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT channel_id, file_name, file_id FROM music_files WHERE file_name LIKE ?", 
              (f"%{query}%",))
    results = c.fetchall()
    conn.close()
    
    if results:
        # List matching songs
        for channel_id, file_name, file_id in results:
            await update.message.reply_text(f"Found: {file_name}\nSend /select_{file_id} to get the file.")
    else:
        await update.message.reply_text(f"No music found for: {query}.")

# Function to handle song selection
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    song_file_id = query.data.split('_')[1]
    
    # Retrieve and send the selected song
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM music_files WHERE file_id = ?", (song_file_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        file_id = result[0]
        await query.answer()
        await query.edit_message_text(f"Sending the selected song: {file_id}...")
        await query.message.reply_audio(file_id)
    else:
        await query.answer()
        await query.edit_message_text("Sorry, the song is no longer available.")

# Function to handle new music file uploads
async def handle_new_file(update: Update, context: CallbackContext):
    if update.message.document or update.message.audio:
        file_name = update.message.document.file_name if update.message.document else update.message.audio.file_name
        file_id = update.message.document.file_id if update.message.document else update.message.audio.file_id
        channel_id = update.message.chat.id
        
        # Save the file info in the database
        save_music_file(channel_id, file_name, file_id)

        await update.message.reply_text(f"File '{file_name}' saved successfully!")

# Add the command handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('add_channel', add_channel_command))
application.add_handler(CommandHandler('search_music', search_music))
application.add_handler(CallbackQueryHandler(button))  # Handle song selection button
application.add_handler(MessageHandler(filters.Document.ALL, handle_new_file))  # Listen for file uploads
application.add_handler(MessageHandler(filters.Audio.ALL, handle_new_file))  # Listen for audio uploads

# Initialize the database
init_db()

# Start the bot
application.run_polling()