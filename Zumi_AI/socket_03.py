import cv2
import threading
from PIL import Image, ImageTk
import customtkinter as ctk
from customtkinter import CTkImage   # ✅ 추가

from zumi_AI import ZumiAI


class ZumiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zumi AI Object Detection")
        self.geometry("900x700")

        # Zumi 연결
        self.zumi = ZumiAI()
        self.zumi.connect("192.168.0.59")

     


        # 카메라 + 객체 탐지 초기화
        self.zumi.camera_stream_start()
        
        self.zumi.camera_window_visible(False) # cv window창 닫        

        self.zumi.object_detector_init(performance_mode="balance")
        self.zumi.object_detector_start()
        self.zumi.object_check_add_obj("bus")
        self.zumi.object_check_add_obj("truck")
        self.zumi.object_check_add_obj("stop sign")

        # Tkinter UI
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack(expand=True, fill="both")

        # 영상 업데이트 스레드
        self.running = True
        threading.Thread(target=self.update_frame, daemon=True).start()

    def update_frame(self):
        while self.running:
            # 최신 프레임 (원본 스트림)
            #frame = self.zumi._connection_handler._WebSocketConnectionHandler__raw_img

            #frame = self.zumi.get_camera_frame()  #원본 이미지 데이
            frame = self.zumi.get_processed_frame() # 처리된 이미지 데이터
            
            if frame is None:
                continue

            # 객체 탐지 결과 받아오기
            try:
                detections = self.zumi.object_check_get_result()  # ★ 이 함수가 핵심
            except:
                detections = []

            # 탐지 결과 그리기
            if detections:
                for det in detections:
                    label = det.get("label", "")
                    conf = det.get("confidence", 0)
                    box = det.get("box", [0,0,0,0])

                    x, y, w, h = box
                    # 박스 그리기
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            # # Tkinter에 표시
            # img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # img = Image.fromarray(img)
            # imgtk = ImageTk.PhotoImage(image=img)
            #
            # self.video_label.configure(image=imgtk)
            # self.video_label.imgtk = imgtk
            # self.video_label.image = imgtk  # 참조 유지

            # OpenCV → PIL.Image 변환
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            # PIL.Image → CTkImage 변환
            ctk_img = CTkImage(light_image=img, dark_image=img, size=(320, 240))

            # CTkLabel 업데이트
            self.video_label.configure(image=ctk_img)
            self.video_label.image = ctk_img  # 참조 유지


    def on_closing(self):
        print("on closing")
        self.running = False
        self.zumi.stop()
        self.zumi.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = ZumiApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
