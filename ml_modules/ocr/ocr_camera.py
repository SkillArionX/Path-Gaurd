import cv2
import json

from ocr_engine import OCREngine


ocr = OCREngine()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not found")
    exit()

print("OCR Camera Started")
print("Press SPACE to scan text")
print("Press Q to quit")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.imshow(
        "OCR Camera",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == 32:

        result = ocr.extract_text(
            frame
        )

        print("\nOCR RESULT")

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )

        detected_text = (
            result["payload"]["detected_text"]
        )

        if detected_text:

            print("\nDetected:")
            print(detected_text)

            ocr.speak(
                detected_text
            )

        else:

            print(
                "\nNo readable text detected."
            )

    elif key == ord("q"):

        break

cap.release()

cv2.destroyAllWindows()