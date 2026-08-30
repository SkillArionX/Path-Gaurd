import cv2
from cloud.qwen.client import describe_scene

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera could not be opened")
    exit()

print("Camera started.")
print("Press SPACE to capture and send image to Qwen.")
print("Press Q to quit.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to read camera frame")
        break

    cv2.imshow("Path Guard - Qwen Vision Test", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord(" "):
        print("\nSending image to Qwen Cloud...")

        try:
            response = describe_scene(frame)

            print("\n===== QWEN RESPONSE =====")
            print(response)
            print("=========================\n")

        except Exception as e:
            print("\nQWEN ERROR:")
            print(e)

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()