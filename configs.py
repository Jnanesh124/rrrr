from os import path, getenv

class Config:
    API_ID = int(getenv("API_ID", "19937650"))
    API_HASH = getenv("API_HASH", "6a6df8006df3cb56edce33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "8090402815:AAENW_NseaMdZlY6Ywww4QMRu_O-uBsFrCg")
    FSUB = getenv("FSUB", "JNKBACKUP")
    CHID = int(getenv("CHID", "-1002806980561"))
    SUDO = int(getenv("SUDO", "6415368038"))
    MONGO_URI = getenv("MONGO_URI", "mongodb+srv://nanu:nanu@cluster0.scwh8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    
cfg = Config()
