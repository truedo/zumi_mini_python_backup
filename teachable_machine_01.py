# robot_ai.py  (라이브러리 또는 모듈 형태로 배포)
import cv2
from teachable_machine import TeachableMachine

class RobotAI:
    def __init__(self, model_path="keras_model.h5", labels_path="labels.txt", cam_index=0):
        # 1) 모델 로드
        self.model = TeachableMachine(model_path=model_path,
                                      labels_file_path=labels_path)
        # 2) 카메라 초기화 (ESP32-CAM 스트리밍 대신 로컬 웹캠도 가능)
        self.cap = cv2.VideoCapture(cam_index)

    def collect_images(self, classname, count=20, save_dir="dataset/"):
        """  키 하나만 누르면 해당 클래스 이미지(count장) 자동 저장 """
        import requests, os, time
        os.makedirs(f"{save_dir}/{classname}", exist_ok=True)
        for i in range(count):
            # ESP32-CAM 캡처 URL (예시)
            img_bytes = requests.get("http://192.168.4.1:81/capture").content
            with open(f"{save_dir}/{classname}/{classname}_{i}.jpg","wb") as f:
                f.write(img_bytes)
            print(f"[{classname}] image {i+1}/{count} saved")
            time.sleep(0.5)

    def predict_loop(self, callback):
        """ 실시간 추론 루프. callback(label)을 호출 """
        while True:
            ret, frame = self.cap.read()
            cv2.imwrite("tmp.jpg", frame)
            label, img = self.model.classify_and_show("tmp.jpg")
            callback(label)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
