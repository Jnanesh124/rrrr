from os import getenv

class Config:
    API_ID = int(getenv("API_ID", "19937650"))
    API_HASH = getenv("API_HASH", "6a6df8006df3cb56edce33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "6852169715:AAE9b0jxs91L9_uKUQ0PG1lIveRAtd4vnSw")
    FSUB = getenv("FSUB", "JNKBACKUP")  # This will be removed
    USER_SESSION = getenv("USER_SESSION", "BQFJ1LMAfI8oyuDDBstjqnwO6RGKpLlxDgJqnawlA-ZGPWlTzVgXEKfzbu1RHObQmlghmKVDBQK10UPdsMHCNQg0sN4NLpY4iCX8rjPt8zPyw8YVkKM9S4dt9llHLvBRP_C5TTb9WngPhjkSplDlvwpFcmowNZQW54Zko7-2JMEPZCVj571P3xSc2IOTJeP1AZE6tYK-dJVaybYlwiwkQHeKmJxeesJ82qin0Vzfs0cWp4voCY3VoH5yQcK_8vInZuog3NxLsCW9eWDMVyJoGo_Be3XM6I55zVnuCjvky3PetL2sGy5Bxc2ArKhPUbYQOmgSylkUbUIA9PxaeKAjF8j0yp9QxgAAAAHMf7o8AA")
    CHID = int(getenv("CHID", "-1002806980561"))
    SUDO = int(getenv("SUDO", "6415368038"))
    MONGO_URI = getenv("MONGO_URI", "mongodb+srv://nanu:nanu@cluster0.scwh8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    
    # Multiple Force Subscription Channels (comma separated IDs)
    # Format: "FSUB_CHANNELS=-1001234567890,-1001234567891,@publicchannel"
    FSUB_CHANNELS = getenv("FSUB_CHANNELS", "@JNKBACKUP, @JNKFREELOOTS, @JNK_BOTS")

cfg = Config()
