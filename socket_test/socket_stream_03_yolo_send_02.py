#!/usr/bin/env python3
# 개선된 YOLO 객체 인식 웹소켓 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue
import torch

class YOLODetector:
    def __init__(self, model_name="yolov5s", confidence=0.45):
        """YOLO 객체 인식 모델 초기화"""
        print(f"YOLO 모델 '{model_name}' 로딩 중...")
        self.confidence = confidence
        
        try:
            self.model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
            self.model.conf = confidence
            self.model.iou = 0.45
            self.model.classes = None # 모두 인식
           # self.model.classes = [0]
            self.model.max_det = 100
            self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
            print(f"모델 로드 완료 - Device: {next(self.model.parameters()).device}")
        except Exception as e:
            print(f"모델 로드 실패: {e}")
            self.model = None

    def detect(self, frame):
        """객체 감지 및 결과 시각화"""
        if self.model is None:
            return frame, []

        results = self.model(frame)
        detections = results.pandas().xyxy[0]
        annotated_frame = results.render()[0]
        return annotated_frame, detections.to_dict('records')

class WebSocketCameraClient:
    def __init__(self, url, use_yolo=True, model_name="yolov5s", confidence=0.45):
        self.url = url
        self.ws = None
        self.ws_thread = None
        self.connected = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = False
        self.reconnect_interval = 3
        self.lock = threading.Lock()
        self.frame_count = 0
        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.use_yolo = use_yolo
        self.detector = YOLODetector(model_name, confidence) if use_yolo else None

        self.send_lock = threading.Lock()  # __init__에 추가

    def send_custom_packet(self):
        """커스텀 패킷 전송 메서드"""
        packet = bytes([0x24, 0x52, 0x01, 0x00])
        with self.send_lock:
            if self.connected and self.ws:
                try:
                    self.ws.send(packet, opcode=websocket.ABNF.OPCODE_BINARY)
                    print("패킷 전송 성공:", packet.hex(' '))
                except Exception as e:
                    print("패킷 전송 실패:", e)


    def connect(self):
        """웹소켓 연결 관리"""
        with self.lock:
            if self.connected:
                return True

            print(f"연결 시도: {self.url}")
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                self.ws_thread = threading.Thread(target=self.ws.run_forever)
                self.ws_thread.daemon = True
                self.ws_thread.start()

                # 연결 타임아웃 처리
                timeout = time.time() + 5
                while not self.connected and time.time() < timeout:
                    time.sleep(0.1)
                return self.connected
            except Exception as e:
                print(f"연결 실패: {e}")
                return False

    def on_open(self, ws):
        """연결 시작 핸들러"""
        print("연결 성공!")
        self.connected = True
        self.start_time = time.time()
        self.frame_count = 0
        self.last_frame_time = time.time()
        ws.send("stream")

    def on_message(self, ws, message):
        """프레임 수신 처리"""
        try:
            nparr = np.frombuffer(message, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                # 색상 변환 BGR - > RGB
                #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                try:
                    self.frame_queue.put_nowait(img)
                    self.frame_count += 1
                    self.last_frame_time = time.time()
                except queue.Full:
                    pass
        except Exception as e:
            print(f"이미지 처리 오류: {e}")

    def on_error(self, ws, error):
        """오류 처리"""
        print(f"오류 발생: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """연결 종료 처리"""
        print("연결 종료")
        self.connected = False

    def start(self):
        """메인 처리 루프"""
        self.running = True

        while self.running:
            if not self.connected:
                if not self.connect():
                    time.sleep(self.reconnect_interval)
                    continue

            try:
                frame = self.frame_queue.get(timeout=1.0)
                
                # YOLO 객체 인식
                if self.use_yolo and self.detector:
                    processed_frame, detections = self.detector.detect(frame)
                    obj_count = len(detections)
                else:
                    processed_frame = frame
                    obj_count = 0

                # FPS 계산
                elapsed = time.time() - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                
                # 화면 표시 정보 추가
                #cv2.putText(processed_frame, f"FPS: {fps:.2f}", (10, 30),
                #           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                #cv2.putText(processed_frame, f"Objects: {obj_count}", (10, 60),
                #           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 화면 출력
                cv2.imshow("ESP32-S3 YOLO 스트림", processed_frame)

                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    cv2.imwrite(f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg", processed_frame)
                    print("이미지 저장 완료")
                    
                elif key == ord('r'):  # 'r' 키로 패킷 전송
                    self.send_custom_packet()


                    

            except queue.Empty:
                if time.time() - self.last_frame_time > 5:
                    print("프레임 수신 없음. 재연결...")
                    self.connected = False
                continue

        self.stop()

    def stop(self):
        """리소스 정리"""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='YOLO 객체 인식 웹소켓 클라이언트')
    parser.add_argument('--url', type=str, default='ws://192.168.0.59/ws',
                       help='서버 주소 (예: ws://IP/ws)')
    parser.add_argument('--no-yolo', action='store_true',
                       help='YOLO 기능 비활성화')
    parser.add_argument('--model', type=str, default='yolov5m',
                       help='YOLO 모델 선택 (yolov5n, yolov5s, yolov5m 등)')
    parser.add_argument('--confidence', type=float, default=0.25,
                       help='신뢰도 임계값 (0.0-1.0)')
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
        print("안전 종료 중...")
        client.stop()

if __name__ == "__main__":
    main()
