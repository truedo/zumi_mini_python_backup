#!/usr/bin/env python3
# 개선된 파이썬 웹소켓 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue

class WebSocketCameraClient:
    def __init__(self, url):
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

    def connect(self):
        """웹소켓 연결 시도 및 연결 확인"""
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

                # 연결이 확립될 때까지 대기 (최대 5초)
                timeout = time.time() + 5
                while not self.connected and time.time() < timeout:
                    time.sleep(0.1)
                if not self.connected:
                    print("연결 실패: 타임아웃")
                return self.connected
            except Exception as e:
                print(f"연결 실패: {e}")
                return False

    def on_open(self, ws):
        """연결 성공 시"""
        print("연결 성공!")
        self.connected = True
        self.start_time = time.time()
        self.frame_count = 0
        self.last_frame_time = time.time()
        ws.send("stream")

    def on_message(self, ws, message):
        """메시지 처리"""
        try:
            nparr = np.frombuffer(message, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                try:
                    self.frame_queue.put_nowait(img)
                    self.frame_count += 1
                    self.last_frame_time = time.time()  # 프레임 수신 시 시간 업데이트
                except queue.Full:
                    pass  # 프레임 드랍
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
        """스트리밍 시작"""
        self.running = True

        while self.running:
            if not self.connected:
                if not self.connect():
                    time.sleep(self.reconnect_interval)
                    continue

            try:
                # 1초 동안 프레임 대기
                frame = self.frame_queue.get(timeout=1.0)
                cv2.imshow("ESP32-S3 스트림", frame)

                # FPS 표시
                elapsed = time.time() - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                cv2.setWindowTitle("ESP32-S3 스트림", f"실시간 스트림 | FPS: {fps:.2f}")

                # 종료 처리: 'q' 키 입력시 종료
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except queue.Empty:
                # 프레임 수신이 5초간 없으면 재연결 시도
                if time.time() - self.last_frame_time > 5:
                    print("프레임 수신 없음. 재연결 시도...")
                    self.connected = False
                continue

        self.stop()

    def stop(self):
        """리소스 정리"""
        self.running = False
        if self.ws:
            self.ws.close()
        # ws 스레드가 있다면 join 시도 (데몬 스레드이므로 프로그램 종료시 함께 종료됨)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='개선된 ESP32-S3 카메라 클라이언트')
    parser.add_argument('--url', type=str, default='ws://192.168.0.59/ws',
                        help='서버 웹소켓 주소 (예: ws://IP_ADDRESS/ws)')
    args = parser.parse_args()

    client = WebSocketCameraClient(args.url)
    try:
        client.start()
    except KeyboardInterrupt:
        print("안전하게 종료 중...")
        client.stop()

if __name__ == "__main__":
    main()
