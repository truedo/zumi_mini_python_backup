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
        self.sensor_queue = queue.Queue(maxsize=20)
        
        self.running = False
        self.reconnect_interval = 3
        self.lock = threading.Lock()
        self.frame_count = 0
        self.start_time = time.time()
        self.last_frame_time = time.time()
        
        self.send_lock = threading.Lock()  # __init__에 추가

          
    def connect(self):
        """웹소켓 연결 시작"""
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
       # self.ws.run_forever()
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
            

    def on_open(self, ws):
        """연결 성공 시"""
        print("연결 성공!")
        self.connected = True
        self.start_time = time.time()
        self.frame_count = 0
        self.last_frame_time = time.time()
        #ws.send("stream")
        #ws.send("sensor")


    def on_message(self, ws, message):
        """메시지 처리"""
        try:            
            if isinstance(message, bytes):
                #print(len(message))
                if len(message) == self.SENSOR_DATA_LENGTH:
                    self._process_sensor_packet(message)
                    #print("sen")
                else:
                    self._process_image_frame(message)
            else:
                self.logger.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            self.logger.error(f"Message handling error: {str(e)}")


    def on_error(self, ws, error):
        """오류 처리"""
        print(f"오류 발생: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """연결 종료 처리"""
        print("연결 종료")
        #self.connected = False
        self.logger.info("Connection closed")
        self.running = False

    def stop(self):
        """리소스 정리"""
        print("stop")
        self.running = False
        if self.ws:
            self.ws.close()
        # ws 스레드가 있다면 join 시도 (데몬 스레드이므로 프로그램 종료시 함께 종료됨)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        cv2.destroyAllWindows()

def main():

    client = WebSocketCameraClient('ws://192.168.0.59/ws')
    try:
        client.connect()

        #client.start_display()
    except KeyboardInterrupt:
        print("안전하게 종료 중...")
        client.stop()

if __name__ == "__main__":
    main()
