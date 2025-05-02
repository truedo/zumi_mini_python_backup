#!/usr/bin/env python3
# 개선된 파이썬 웹소켓 클라이언트

import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue

import logging

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

        self.led_color = 0
        
        self.l_spd = 0
        self.r_spd = 0


        self.l_dir = 0        
        self.r_dir = 0

        #self.server_ip = server_ip
        self.SENSOR_HEADER = bytes([0x24, 0x52])  # 'SD' in hex
        self.SENSOR_DATA_LENGTH = 7  # Header(2) + Data(5)
        
        self.logger = logging.getLogger("ESP32Receiver")
        self._setup_logging()
        
    def _setup_logging(self):
        """로깅 설정 초기화"""
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 콘솔 출력 핸들러
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
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
        ws.send("stream")
        ws.send("sensor")


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


    def _process_sensor_packet(self, data):
        """센서 데이터 처리"""
        if data[:2] != self.SENSOR_HEADER:
            self.logger.warning(f"Invalid sensor header: {data[:2].hex()}")
            return
        
        sensor_values = {
            'temp': data[2],
            'humidity': data[3],
            'light': data[4],
            'motion': data[5],
            'status': data[6]
        }        
        
        try:
            self.sensor_queue.put_nowait(sensor_values)
            self.last_sensor_time = time.time()
        except queue.Full:
            self.logger.warning("Sensor queue overflow")

            
    def _process_image_frame(self, data):
         
        """영상 프레임 처리"""
        try:
            # 비동기 디코딩을 위한 스레드 풀 사용
            self._decode_frame_async(data)
        except Exception as e:
            self.logger.error(f"Frame processing error: {str(e)}")

    def _decode_frame_async(self, data):
        """별도 스레드에서 프레임 디코딩"""
        import threading
        threading.Thread(target=self._async_decode_task, args=(data,)).start()

    def _async_decode_task(self, data):
        """실제 디코딩 작업"""
        try:
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = cv2.flip(img, 1)
            if img is not None:
                self._enqueue_frame(img)
            else:
                self.logger.warning("Failed to decode image")
        except Exception as e:
            self.logger.error(f"Decoding error: {str(e)}")

    def _enqueue_frame(self, frame):
        """프레임 큐에 안전하게 저장"""
        try:
            self.frame_queue.put_nowait(frame)
            self.frame_count += 1
            self.last_frame_time = time.time()
        except queue.Full:
            self.frames_dropped += 1
            if self.frames_dropped % 30 == 0:
                self.logger.warning(f"Dropped frames: {self.frames_dropped}")

                
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

    def start_display(self):
        """영상 디스플레이 메인 루프"""
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=2.0)
                sensors = self._get_latest_sensors()
                
                # 화면 오버레이 추가
                self._add_overlay(frame, sensors)
                
                cv2.imshow("ESP32 Stream", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except queue.Empty:
                if time.time() - self.last_frame_time > 5:
                    self.logger.warning("No frames received for 5 seconds")
                    #self.connected = False
                #continue
                    
        self.stop()

       
    def _get_latest_sensors(self):
        """최신 센서 값 가져오기"""
        latest = {}
        while not self.sensor_queue.empty():
            latest = self.sensor_queue.get_nowait()
        return latest
    

    def _add_overlay(self, frame, sensors):
        """화면에 정보 오버레이"""
        # 센서 정보
        if sensors:
            y = 30
            for k, v in sensors.items():
                text = f"{k}: {v}"
                cv2.putText(frame, text, (10, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                y += 30
        
        # FPS 계산
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, frame.shape[0]-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
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
    parser = argparse.ArgumentParser(description='개선된 ESP32-S3 카메라 클라이언트')
    parser.add_argument('--url', type=str, default='ws://192.168.0.59/ws',
    #parser.add_argument('--url', type=str, default='ws://106.249.166.181/ws',
    #parser.add_argument('--url', type=str, default='ws://zumimini.iptime.org/ws',  
                        help='서버 웹소켓 주소 (예: ws://IP_ADDRESS/ws)')
    args = parser.parse_args()

    client = WebSocketCameraClient(args.url)
    try:
        client.connect()

        client.start_display()
    except KeyboardInterrupt:
        print("안전하게 종료 중...")
        client.stop()

if __name__ == "__main__":
    main()
