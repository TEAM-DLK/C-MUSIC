import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, filters

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
    )
    ''')
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

# Function to simulate listing music files from a channel (you should replace this with actual logic)
def list_music_files(channel):
    # This simulates a list of music files in the channel
    return [
        {"title": "Song 1", "file_id": "song_1_file_id"},
        {"title": "Song 2", "file_id": "song_2_file_id"},
        {"title": "Song 3", "file_id": "song_3_file_id"}
    ]

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

# Function to handle music search and sending the music file
async def search_music(update: Update, context: CallbackContext):
    user = update.message.from_user
    query = ' '.join(context.args)
    
    if not query:
        await update.message.reply_text("Please provide the name of the song.")
        return
    
    channels = get_channels(user.id)  # Get the channels the user has added
    if not channels:
        await update.message.reply_text("You have not added any channels. Use /add_channel <channel_username> to add a channel.")
        return
    
    found = False
    for channel in channels:
        try:
            # Simulate getting the list of music files from the channel
            music_files = list_music_files(channel)
            
            # Search for the song in the music files
            matched_files = [file for file in music_files if query.lower() in file["title"].lower()]
            
            if matched_files:
                # Create an inline keyboard for the user to choose a song
                keyboard = [
                    [InlineKeyboardButton(f"Select {file['title']}", callback_data=file['file_id'])] for file in matched_files
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(f"Found music in {channel}: {query}. Please choose a song:", reply_markup=reply_markup)
                found = True
                break
        except Exception as e:
            await update.message.reply_text(f"Error while searching in {channel}: {e}")
    
    if not found:
        await update.message.reply_text(f"No music found for: {query} in your channels.")

# Function to handle song selection
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    song_file_id = query.data
    
    # Simulate sending the selected song file
    await query.answer()
    await query.edit_message_text(f"Sending the selected song: {song_file_id}...")
    
    # In a real scenario, you would retrieve the file ID and send it
    await query.message.reply_audio(song_file_id)

# Add the command handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('add_channel', add_channel_command))
application.add_handler(CommandHandler('search_music', search_music))
application.add_handler(MessageHandler(filters.Regex('^/search_music'), search_music))  # For music search in response
application.add_handler(CallbackQueryHandler(button))  # Handle song selection button

# Initialize the database
init_db()

# Start the bot
application.run_polling()