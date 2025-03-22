import cv2
import numpy as np
import base64
import os

# Typische schermresoluties van 640x480 tot 8K
resoluties = [
    (640, 480),
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1280, 960),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
    (7680, 4320)  # 8K UHD
]

# Outputmap aanmaken
os.makedirs("test_images", exist_ok=True)

for width, height in resoluties:
    # Witte ruis genereren
    random_image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

    # Encodeer als JPG
    _, buffer = cv2.imencode(".jpg", random_image)

    # Converteer naar base64 (optioneel)
    encoded_string = base64.b64encode(buffer).decode("utf-8")

    # Afbeelding opslaan
    filename = f"test_images/white_noise_{width}x{height}.jpg"
    cv2.imwrite(filename, random_image)

    # Statusbericht
    print(f"[{width}x{height}] opgeslagen als {filename}")
    # Indien nodig kun je ook encoded_string gebruiken

# Laatste afbeelding tonen (kan zwaar zijn bij 8K)
cv2.imshow("Laatste afbeelding (witte ruis)", random_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
