import cv2
import torch
import numpy

class YOLODetector:
    def __init__(self, model_name="yolov5s", confidence=0.1):
        print(f"YOLO 모델 '{model_name}' 로딩 중...")
        self.confidence = confidence
        try:
            self.model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
            self.model.conf = confidence
            self.model.iou = 0.45
            self.model.classes = None
            self.model.max_det = 100
            self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
            print(f"YOLO 모델 로드 완료 - Device: {next(self.model.parameters()).device}")
        except Exception as e:
            print(f"YOLO 모델 로드 실패: {e}")
            self.model = None

    def detect(self, frame):
        if self.model is None:
            return frame, []
        results = self.model(frame)
        detections = results.pandas().xyxy[0]
        annotated_frame = results.render()[0]
        return annotated_frame, detections.to_dict('records')

# 이미지 파일을 불러와 테스트하기
if __name__ == "__main__":
    print(numpy.__version__)
    
    # YOLODetector 초기화
    detector = YOLODetector(model_name="yolov5n", confidence=0.1)

    # 테스트할 이미지 파일 경로 (원하는 파일 경로로 수정)
    img_path = "test_image.jpg"
    img = cv2.imread(img_path)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if img is None:
        print("이미지를 불러올 수 없습니다. 파일 경로를 확인하세요:", img_path)
    else:
        # 객체 감지 수행
        annotated_img, detections = detector.detect(img)
        print("감지된 객체:", detections)
        # 결과 표시
        cv2.imshow("YOLO 객체 검출 결과", annotated_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
