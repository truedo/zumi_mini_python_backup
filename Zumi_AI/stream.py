import cv2
import numpy as np
import websocket
import threading
import queue
import time
import os

try:
    from tensorflow.keras.models import load_model
except ImportError:
    load_model = None

class ModelNotReadyError(Exception):
    """Raised when AI mode is selected but model files are missing or invalid."""
    pass

class RobotController:
    def __init__(
        self,
        ws_url: str,
        mode: str = 'stream',              # 'stream' or 'ai'
        model_path: str = None,            # path to .h5 model for AI mode
        labels_path: str = None,           # path to labels.txt for AI mode
        show_video: bool = True,           # whether to display the video window
        reconnect_interval: float = 3.0,   # seconds between reconnect attempts
    ):
        self.ws_url = ws_url
        self.mode = mode
        self.show_video = show_video
        self.reconnect_interval = reconnect_interval

        # WebSocket and threading
        self.ws = None
        self.ws_thread = None
        self.connected = False
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.lock = threading.Lock()

        # Load AI model if requested
        if self.mode == 'ai':
            if load_model is None:
                raise ModelNotReadyError("TensorFlow not installed.")
            if not (model_path and os.path.exists(model_path) and labels_path and os.path.exists(labels_path)):
                raise ModelNotReadyError("Model file or labels not found.")
            self.model = load_model(model_path)
            with open(labels_path, 'r') as f:
                self.labels = [line.strip() for line in f]

        # robot control
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

    def keyCheck(self,key):
        # Handle GUI events
        if key == ord('q'):
            self.stop()

        elif key == ord('c'):
            cv2.imwrite(f"dataset2_{time.strftime('%Y%m%d_%H%M%S')}.jpg", frame)
            print("이미지 저장 완료")

        elif key == ord('0'):  #
            self.led_color = 0
            self.send_custom_packet()

        elif key == ord('1'):  #
            self.led_color = 1
            self.send_custom_packet()


        elif key == ord('2'):  #
            self.led_color = 2
            self.send_custom_packet()

        elif key == ord('3'):  #
            self.led_color = 3
            self.send_custom_packet()

        elif key == ord('4'):  #
            led_color = 4
            self.send_custom_packet()

        elif key == ord('5'):  #
            self.led_color = 5
            self.send_custom_packet()

        elif key == ord('6'):  #
            self.led_color = 6
            self.send_custom_packet()

        elif key == ord('7'):  #
            self.led_color = 7
            self.send_custom_packet()

        elif key == ord('e'):  # right
            self.l_spd = 0
            self.r_spd = 0
            self.l_dir = 0
            self.r_dir = 0
            self.send_custom_packet()

        elif key == ord('w'):  # forward
            #self.led_color = 7
            self.l_spd = 20
            self.r_spd = 20
            self.l_dir = 2
            self.r_dir = 1
            self.send_custom_packet()

        elif key == ord('s'):  # reverse
            self.l_spd = 20
            self.r_spd = 20
            self.l_dir = 1
            self.r_dir = 2
            self.send_custom_packet()

        elif key == ord('a'):  # left
            self.l_spd = 10
            self.r_spd = 10
            self.l_dir = 1
            self.r_dir = 1
            self.send_custom_packet()

        elif key == ord('d'):  # right
            self.l_spd = 10
            self.r_spd = 10
            self.l_dir = 2
            self.r_dir = 2
            self.send_custom_packet()


    def connect(self):
        """Establish WebSocket connection and start listening thread."""
        with self.lock:
            if self.connected:
                return True

            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()

            timeout = time.time() + 5
            while not self.connected and time.time() < timeout:
                time.sleep(0.1)
            return self.connected

    def on_open(self, ws):
        self.connected = True
        ws.send("stream")

    def on_message(self, ws, message):
        data = np.frombuffer(message, np.uint8)
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if frame is not None:
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def on_error(self, ws, error):
        self.connected = False
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print("WebSocket closed")

    def start(self):
        """Begin processing loop based on selected mode."""
        self.running = True
        while self.running:
            if not self.connected:
                if not self.connect():
                    time.sleep(self.reconnect_interval)
                    continue
            try:
                frame = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Flip and optionally display
            frame = cv2.flip(frame, 1)
            if self.show_video:
                cv2.imshow("Robot Stream", frame)

            # If AI mode, perform prediction
            if self.mode == 'ai':
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(frame_rgb, (224, 224))
                array = resized / 255.0
                array = np.expand_dims(array, axis=0)
                pred = self.model.predict(array, verbose=0)
                idx = np.argmax(pred[0])
                label = self.labels[idx]
                print(f"Prediction: {label}")

            if self.show_video:
                key = cv2.waitKey(1) & 0xFF
                self.keyCheck(key)





    def stop(self):
        """Clean up resources and close connections."""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        if self.show_video:
            cv2.destroyAllWindows()

# # Example usage
# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--url', default='ws://192.168.0.63/ws')
#     parser.add_argument('--mode', choices=['stream','ai'], default='stream')
#     parser.add_argument('--model', help='Path to keras_model.h5')
#     parser.add_argument('--labels', help='Path to labels.txt')
#     parser.add_argument('--no-display', action='store_true')
#     args = parser.parse_args()

#     client = RobotController(
#         ws_url=args.url,
#         mode=args.mode,
#         model_path=args.model,
#         labels_path=args.labels,
#         show_video=not args.no_display
#     )
#     client.start()
