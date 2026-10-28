from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

# Profil RFC 9106 „low memory” (64 MiB, 3 iteracje, 4 wątki); sól losowana przy każdym hashu.
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4, type=Type.ID)


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain)
    except VerificationError, InvalidHashError:
        return False
