import cv2

def capture_image():
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise Exception("Could not open webcam")

    success, frame = camera.read()

    camera.release()

    if not success:
        raise Exception("Failed to capture image")

    return frame