import cv2
from ultralytics import YOLO

# YOLOv8 모델 로드 (COCO-pretrained)
model = YOLO("yolov8n.pt")  # yolov8s.pt, yolov8m.pt 등으로 변경 가능

# 웹캠 열기 (0: 기본 카메라)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ 카메라를 열 수 없습니다.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # YOLOv8으로 객체 감지
    results = model(frame, conf=0.3)  # 신뢰도(confidence) 설정

    # 결과 시각화 (bounding box 등)
    annotated_frame = results[0].plot()

    # 화면에 출력
    cv2.imshow("YOLOv8 Camera Detection", annotated_frame)

    # 'q' 키 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 종료 처리
cap.release()
cv2.destroyAllWindows()
