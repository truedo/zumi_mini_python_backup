#!/usr/bin/env python3
# 개선된 파이썬 웹소켓 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue

from tensorflow.keras.models import load_model
from PIL import Image, ImageOps, ImageDraw, ImageFont
import numpy as np

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
        
        self.send_lock = threading.Lock()  # __init__에 추가

        self.led_color = 0
        
        self.l_spd = 0
        self.r_spd = 0


        self.l_dir = 0        
        self.r_dir = 0
 
    def send_custom_packet(self):
        """커스텀 패킷 전송 메서드"""
        packet = bytes([0x24, 0x52, self.l_spd, self.r_spd, self.l_dir, self.r_dir, self.led_color])
        with self.send_lock:
            if self.connected and self.ws:
                try:
                    self.ws.send(packet, opcode=websocket.ABNF.OPCODE_BINARY)
                    print("패킷 전송 성공:", packet.hex(' '))
                except Exception as e:
                    print("패킷 전송 실패:", e)
                    


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
    
        if not self.connected:
            self.connect()

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
    parser.add_argument('--url', type=str, default='ws://192.168.0.63/ws',
    #parser.add_argument('--url', type=str, default='ws://106.249.166.181/ws',
    #parser.add_argument('--url', type=str, default='ws://zumimini.iptime.org/ws',  
                        help='서버 웹소켓 주소 (예: ws://IP_ADDRESS/ws)')
    args = parser.parse_args()

    client = WebSocketCameraClient(args.url)
    print("test1")

    try:
        client.start()
    except KeyboardInterrupt:
        print("안전하게 종료 중...")
        client.stop()

    print("test2")
    
    client.led_color = 3 
    client.send_custom_packet()

    

if __name__ == "__main__":
    main()
    print("test3")

