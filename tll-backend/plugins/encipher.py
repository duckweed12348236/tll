import bcrypt

from plugins import Singleton


class Encipher(Singleton):
    def __init__(self, rounds: int = 12) -> None:
        self.rounds = rounds

    def encrypt(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
