from os import getenv

class Config:
    API_ID = int(getenv("API_ID", "19937650"))
    API_HASH = getenv("API_HASH", "6a6df8006df3cb56edce33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "6852169715:AAE9b0jxs91L9_uKUQ0PG1lIveRAtd4vnSw")
    USER_SESSION = getenv("USER_SESSION", "BQFJ1LMATkB-k4zhKutqIZ2QQM9MarxhWhyYEF9zDekS0eFuUfFjpegURbkyD56TbzQyv2rnSASmEKkGgPDldSLb0iR6xnt6zBWdwS0kKYcUJ9yPdr-OM3kHMrhYEW5nMNEtC5tPZtlLvS9dHdW_3wkrfRJVrDr0kYb3WqvB4jit_BfA2pbXbLlzEjcIFdSQwFxIa9actCcuHnSCDcZ4bO4I5hHO_fdHfRutQ6evKJZLp8JQO278alGytKs81mUzltdQX2Kb4qtVjM3FL_JmNq3Xy3z7QtfzzG5Ydva5B3M7Tt0RV4rwXDDwXluf1mNjfY_shtu7Jkw95tGKpQUA1uUi6txP-AAAAAHMf7o8AA")
    SUDO = int(getenv("SUDO", "6415368038"))
    MONGO_URI = getenv("MONGO_URI", "mongodb+srv://nanu:nanu@cluster0.scwh8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

    # Multiple Force Subscription Channels (comma separated IDs)
    # Format: "FSUB_CHANNELS=-1001234567890,-1001234567891,@publicchannel"
    FSUB_CHANNELS = getenv("FSUB_CHANNELS", "@JNKBACKUP, @JNKFREELOOTS, @JNK_BOTS, -1001802232305")

cfg = Config()
