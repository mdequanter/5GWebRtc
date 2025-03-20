import time
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# AES-256 sleutel
AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

def encrypt_data(plain_text):
    """Versleutelt gegevens met AES-256 CBC en base64-encodeert de uitvoer."""
    iv = os.urandom(16)  # IV van 16 bytes
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # PKCS7 padding toepassen
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(plain_text) + padder.finalize()

    encrypt_start_time = time.perf_counter()  # 🔥 Hogere precisie tijdmeting
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    encrypt_end_time = time.perf_counter()

    encryption_time_ms = (encrypt_end_time - encrypt_start_time) * 1000  # in ms
    return base64.b64encode(iv + encrypted_data).decode('utf-8'), encryption_time_ms

# Test met verschillende gegevensgroottes
data_sizes = [1024, 2048, 4096, 8192, 16384, 32768]  # Bytes
num_iterations = 10

for size in data_sizes:
    test_data = os.urandom(size)  # Willekeurige data van bepaalde grootte
    times = []

    for _ in range(num_iterations):
        _, enc_time = encrypt_data(test_data)
        times.append(enc_time)

    avg_time = sum(times) / len(times)
    print(f"Data size: {size} bytes - Gemiddelde encryptietijd: {avg_time:.6f} ms")  # 🔥 Tot 6 decimalen
