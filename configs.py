from os import getenv

class Config:
    API_ID = int(getenv("API_ID", "19937650"))
    API_HASH = getenv("API_HASH", "6a6df8006df3cb56edce33056d37baca")
    BOT_TOKEN = getenv("BOT_TOKEN", "8277325762:AAEDDyJc6nThAofniQHPQZuMDIS_1naNLRo")
    FSUB = getenv("FSUB", "JNKBACKUP")
    USER_SESSION = getenv("USER_SESSION", "BQFJ1LMAtGkMzV2CMXwSCPIzzTH742lqPfWAgssZHZ8KjyhIgM35BiriFCpJKsko3oteLp2PkYPeyeni9gYWuEweRhcQ6aSvxFJmId3F1R3jQNSzEXKalRFBQvMtqpqgPB_XyWtfRa6oewFphKg1b8pZmzkTXOdCIm9Rk5VgkWVNbfJVq59hv5jBfRhbAqQ37IqdJX7mthLl7xuX1b4aRtzKp1_STY6WqVRBipiiSuP_2AHCaqK6XNtPl1d9HvYmxcOFq8bB8kwNIyzGVdiUcyn4XMOpPonHVB6clqIj6L_aAE2YD58yfhobIW4RnqRbpc-oK_AZ4lBcogUhikslY17l5fdlDgAAAAHMf7o8AA")
    CHID = int(getenv("CHID", "-1002806980561"))
    SUDO = int(getenv("SUDO", "6415368038"))
    MONGO_URI = getenv("MONGO_URI", "mongodb+srv://nanu:nanu@cluster0.scwh8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    
cfg = Config()
