#!/usr/bin/env python3
# 파이썬 웹소켓 카메라 스트리밍 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import tempfile
import time
import os
from threading import Thread, Lock

class WebSocketCameraClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.connected = False
        self.frame = None
        self.frame_lock = Lock()
        self.running = False
        
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
        print(time.ctime())
        self.ws.send("stream")  # 스트리밍 시작 요청
    
    def on_message(self, ws, message):
        """웹소켓으로부터 메시지를 받았을 때 호출"""
        try:
            # 임시 파일에 바이너리 데이터 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(message)
                tmp_name = tmp.name
            
            # OpenCV로 이미지 로드
            img = cv2.imread(tmp_name)
            os.unlink(tmp_name)  # 임시 파일 삭제
            
            if img is not None:
                with self.frame_lock:
                    self.frame = img
        except Exception as e:
            print(f"이미지 처리 오류: {e}")
            print(time.ctime())
    
    def on_error(self, ws, error):
        """웹소켓 오류 발생시 호출"""
        print(f"오류 발생: {error}")
        print(time.ctime())
    
    def on_close(self, ws, close_status_code, close_msg):
        """웹소켓 연결이 닫혔을 때 호출"""
        print("연결 종료")
        print(time.ctime())
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
                            cv2.imshow("ESP32-S3 카메라 스트림", self.frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.running = False
                        break
                    
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
    parser = argparse.ArgumentParser(description='ESP32-S3 카메라 웹소켓 클라이언트')
    parser.add_argument('--url', type=str, default='ws://192.168.0.59/ws',
                        help='ESP32-S3 웹소켓 서버 URL')
    args = parser.parse_args()
    
    client = WebSocketCameraClient(args.url)
    try:
        client.start()
    except KeyboardInterrupt:
        print("프로그램 종료")
        client.stop()

if __name__ == "__main__":
    main()
