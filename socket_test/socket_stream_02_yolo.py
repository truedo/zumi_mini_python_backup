#!/usr/bin/env python3
# 파이썬 웹소켓 카메라 스트리밍 YOLO 객체 인식 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import tempfile
import time
import os
from threading import Thread, Lock
import torch

class YOLODetector:
    def __init__(self, model_name="yolov5s", confidence=0.45):
        """YOLO 객체 인식 모델 초기화"""
        print(f"YOLO 모델 '{model_name}' 로딩 중...")
        self.confidence = confidence
        
        # YOLOv5 모델 로드 (torch hub 사용)
        try:
            self.model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
            self.model.conf = confidence  # 신뢰도 임계값 설정
            self.model.iou = 0.45  # IoU 임계값 설정
            self.model.classes = None  # 모든 클래스 감지
            self.model.max_det = 100  # 최대 감지 객체 수
            
            # GPU 사용 가능할 경우 활성화
            self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
            
            print(f"YOLO 모델 로드 완료 - Device: {next(self.model.parameters()).device}")
        except Exception as e:
            print(f"YOLO 모델 로드 실패: {e}")
            self.model = None
    
    def detect(self, frame):
        """이미지에서 객체 감지 수행"""
        if self.model is None:
            return frame, []
        
        # 추론 수행
        results = self.model(frame)
        
        # 결과 가져오기
        detections = results.pandas().xyxy[0]  # 객체 위치와 클래스 정보
        
        # 결과 시각화
        annotated_frame = results.render()[0]  # 객체 검출 결과가 표시된 이미지
        
        return annotated_frame, detections.to_dict('records')

class WebSocketCameraClient:
    def __init__(self, url, use_yolo=True, model_name="yolov5s", confidence=0.45):
        self.url = url
        self.ws = None
        self.connected = False
        self.frame = None
        self.frame_lock = Lock()
        self.running = False
        self.use_yolo = use_yolo
        self.fps_counter = 0
        self.fps = 0
        self.last_fps_time = time.time()
        
        if use_yolo:
            self.detector = YOLODetector(model_name, confidence)
        else:
            self.detector = None
        
    def connect(self):
        """웹소켓 서버에 연결"""
        print(f"ESP32-S3 카메라에 연결 중: {self.url}")
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.connected = True
            return True
        except Exception as e:
            print(f"연결 오류: {e}")
            return False
    
    def on_open(self, ws):
        """웹소켓 연결이 열렸을 때 호출"""
        print("연결 성공!")
        self.ws.send("stream")  # 스트리밍 시작 요청
    
    def on_message(self, ws, message):
        try:
            # 임시 파일 대신 메모리에서 바로 디코딩
            nparr = np.frombuffer(message, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                print("이미지 디코딩 실패")
                return
            
            if img is not None:
                # FPS 계산
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.fps = self.fps_counter
                    self.fps_counter = 0
                    self.last_fps_time = current_time
                    
                img = img.copy()  # 읽기 전용 문제 방지

                # FPS 계산 및 YOLO 객체 감지 수행
                if self.use_yolo and self.detector is not None:
                    img, detections = self.detector.detect(img)
                    #cv2.putText(img, f"Objects: {len(detections)}", (10, 60),
                    #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # FPS 표시
                img = img.copy()
                cv2.putText(img, f"FPS: {self.fps}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


                # FPS 표시 등 후속 처리...
                with self.frame_lock:
                    self.frame = img
                    
        except Exception as e:
            print(f"이미지 처리 오류: {e}")

    
    def on_error(self, ws, error):
        """웹소켓 오류 발생시 호출"""
        print(f"오류 발생: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """웹소켓 연결이 닫혔을 때 호출"""
        print("연결 종료")
        self.connected = False
    
    def start(self):
        """웹소켓 연결 및 화면 출력 시작"""
        if self.connect():
            self.running = True
            
            # 웹소켓 연결 스레드 시작
            ws_thread = Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 디스플레이 루프 시작
            try:
                while self.running:
                    with self.frame_lock:
                        if self.frame is not None:
                            cv2.imshow("ESP32-S3 카메라 스트림 (YOLO 객체 인식)", self.frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.running = False
                        break
                    elif key == ord('s') and self.frame is not None:
                        # 's' 키를 누르면 현재 프레임 저장
                        cv2.imwrite(f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg", self.frame)
                        print("이미지 저장됨")
                    
                    time.sleep(0.01)
            finally:
                self.stop()
    
    def stop(self):
        """웹소켓 연결 및 화면 출력 중지"""
        self.running = False
        if self.connected:
            self.ws.close()
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='ESP32-S3 카메라 웹소켓 클라이언트 (YOLO 객체 인식)')
    parser.add_argument('--url', type=str, default='ws://192.168.0.59/ws',
                        help='ESP32-S3 웹소켓 서버 URL')
    parser.add_argument('--no-yolo', action='store_true',
                        help='YOLO 객체 인식 사용 안 함')
    parser.add_argument('--model', type=str, default='yolov5n',
                        help='YOLO 모델 (yolov5n, yolov5s, yolov5m, yolov5l, yolov5x)')
    parser.add_argument('--confidence', type=float, default=0.45,
                        help='객체 인식 신뢰도 임계값 (0.0-1.0)')
    args = parser.parse_args()
    
    client = WebSocketCameraClient(
        args.url, 
        use_yolo=not args.no_yolo,
        model_name=args.model,
        confidence=args.confidence
    )
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("프로그램 종료")
        client.stop()

if __name__ == "__main__":
    main()
