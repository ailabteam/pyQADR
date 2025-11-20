# crypto/qs_prf.py

"""
This module provides a cryptographic primitive for the QADR simulation:
a Quantum-Secure Pseudorandom Function (QS-PRF).

For the purpose of this simulation, we use SHAKE256, a standard eXtendable-Output
Function (XOF) from the SHA-3 family. It is widely considered to be resistant
to attacks by quantum computers.
"""

import hashlib
from qadr import constants

def qs_prf(key: bytes, output_length_bytes: int) -> bytes:
    """
    Expands a short, secret key into a long pseudorandom byte string.

    Args:
        key (bytes): The secret input key, typically from QKD.
                     Its length should match QKD_KEY_LENGTH_BYTES.
        output_length_bytes (int): The desired length of the output pseudorandom
                                   string in bytes.

    Returns:
        bytes: The generated pseudorandom byte string of the specified length.
    """
    # Ensure the key has the expected length for consistency
    if len(key) != constants.QKD_KEY_LENGTH_BYTES:
        # In a real application, this would be a critical error.
        # Here, we can raise an exception to catch potential bugs during development.
        raise ValueError(
            f"Invalid key length. Expected {constants.QKD_KEY_LENGTH_BYTES} bytes, "
            f"but got {len(key)} bytes."
        )

    # 1. Initialize the SHAKE256 hash object.
    shake = hashlib.shake_256()

    # 2. Update the hash object with the secret key.
    shake.update(key)

    # 3. Generate ("digest") the pseudorandom output of the desired length.
    return shake.digest(output_length_bytes)
