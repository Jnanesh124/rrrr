from os import path, getenv

class Config:
    API_ID = int(getenv("API_ID", "1990"))
    API_HASH = getenv("API_HASH", "6a6dcb56edce33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "685b0jxs91L9_uKUQ0PG1lIveRAtd4vnSw")
    FSUB = getenv("FSUB", "ROCKERSBACKUP")
    CHID = int(getenv("CHID", "-100293873"))
    SUDO = int(getenv("SUDO", "6347574"))
    MONGO_URI = getenv("MONGO_URI", "mongodb@cluster0.8pzxa6s.mongodb.net/?retryWrites=true&w=majority")
    
cfg = Config()
