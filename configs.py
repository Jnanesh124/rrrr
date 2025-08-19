from os import getenv

class Config:
    API_ID = int(getenv("API_ID", "150"))
    API_HASH = getenv("API_HASH", "6a6d33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "6852160PG1lIveRAtd4vnSw")
    USER_SESSION = getenv("USER_SESSION", "BQFJ1LMVjM3FL_JmNq3Xy3z7QtfzzG5Ydva5B3M7Tt0RV4rwXDDwXluf1mNjfY_shtu7Jkw95tGKpQUA1uUi6txP-AAAAAHMf7o8AA")
    SUDO = int(getenv("SUDO", "6415368038"))
    MONGO_URI = getenv("MONGO_URI", "mongodb+srv://nrue&w=majority&appName=Cluster0")

    # Multiple Force Subscription Channels (comma separated IDs)
    # Format: "FSUB_CHANNELS=-1001234567890,-1001234567891,@publicchannel"
    FSUB_CHANNELS = getenv("FSUB_CHANNELS", "@JNKBACKUP, @JNKFREELOOTS, @JNK_BOTS, -1001802232305, -1001910410959")

cfg = Config()
