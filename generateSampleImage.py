import cv2
import numpy as np
import base64

# Image dimensions
width, height = 640, 480

# Create a random image (random RGB values for each pixel)
random_image = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

# Encode the image as a JPG in memory
_, buffer = cv2.imencode(".jpg", random_image)

# Convert to base64
encoded_string = base64.b64encode(buffer).decode("utf-8")

# Print base64 string (you can send this over a network)
print(encoded_string)

# Save the image for reference
cv2.imwrite("random_image.jpg", random_image)

# Display the image
cv2.imshow("Random Image", random_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
