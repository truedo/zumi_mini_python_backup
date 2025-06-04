#websocket
import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue

import logging
import re # 정규 표현식 모듈 임포트




import pkg_resources
import copy
import os

import mediapipe as mp
from pupil_apriltags import Detector
from ultralytics import YOLO
# import tensorflow as tf
# from tensorflow import keras

from .receiver import *

#from .face_landmark import FaceLandmark
from .face_recognizer import FaceRecognizer
#from .number_recognizer import NumberRecognizer
from .sketch_recognizer import SketchRecognizer



class WebSocketConnectionHandler(): # BaseConnectionHandler 상속 가능
    """
    Handles communication with a robot via WebSocket.
    Receives sensor/status data and sends control commands.
    Mimics the interface of SerialConnectionHandler for data access.
    """
    def __init__(self, url, usePosCheckBackground=False, debugger=None):
        """
        Initializes the WebSocketConnectionHandler.

        Args:
            url (str): The WebSocket server URL (e.g., 'ws://192.168.0.59/ws').
            usePosCheckBackground (bool): Kept for compatibility, but message
                                          processing is push-based in on_message.
            debugger (DebugOutput, optional): An instance for logging and error output.
        """
        self._url = url
        self._ws = None
        self._ws_thread = None
        self._connected = False # Indicates if the websocket is connected
        self._running = False # Internal flag to control the handler's running state

        self._debugger = debugger # DebugOutput instance or None

        # --- Received Data ---
        # These variables store the latest data received from the robot.
        # Access should be protected by self._data_lock.
        self._data_lock = threading.Lock()

        # Sensor data (based on WS_SENSOR_HEADER packet)
        # Test code mapping: FR, FL, BR, BL, BC order in packet.
        # Serial handler getter order: FL, FR, BL, BC, BR.
        # Store according to packet, get according to serial handler's methods.
        self._packet_senFR = 0
        self._packet_senFL = 0
        self._packet_senBR = 0
        self._packet_senBL = 0
        self._packet_senBC = 0

        # Status/Detection data (based on WS_STATUS_HEADER packet assumption)
        self._reqCOM = 0
        self._reqINFO = 0
        self._reqREQ = 0
        self._reqPSTAT = 0

        self._detectFace = [0, 0, 0]
        self._detectColor = [0, 0, 0]
        self._detectMarker = [0, 0, 0]
        self._detectCat = [0, 0, 0]

        self._btn = 0
        self._battery = 0

        # --- Data to Send ---
        # These variables store the current control state to be sent to the robot.
        # Updates to these trigger sending a command packet.
        # Access should be protected by self._send_lock if set_* methods could be called concurrently.
        self._send_lock = threading.Lock()
        self._l_spd = 0
        self._r_spd = 0
        self._l_dir = 0
        self._r_dir = 0
        self._led_color = 0
        # Control packet header from test code (confusingly same as sensor data header)
        self.SENSOR_HEADER = bytes([0x24, 0x52])
        self.SENSOR_DATA_LENGTH = 10  # Header(2) + Data(5)

        # Config/Internal Flags
        self._usePosConnected = False # Kept for compatibility with serial handler's check
        self._usePosCheckBackground = usePosCheckBackground # Parameter kept for compatibility

        # Internal logging setup
        # self.logger = logging.getLogger(__name__)
        # if not self._debugger and not self.logger.handlers:
        #      # Configure basic logging if no debugger is provided and no handlers exist
        #      logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self._start_time = time.time()
        self._last_frame_time = time.time()
        self._frame_queue = queue.Queue(maxsize=2)
        self._sensor_queue = queue.Queue(maxsize=20)
        self._frame_count = 0
        self._frames_dropped = 0

        self.__flipLRFlag = False
        self.__raw_img = None
        self.__cameraStreamFlag = False

        self.__text_offset = 18



        # sensor
        self.__sensorInitFlag = False
        self.__sensorFlag = False
        self.__drawSensorAreaFlag = True


        # face
        self.__faceDetectInitFlag = False
        self.__faceDetectFlag = False
        self.__drawFaceAreaFlag = True



        self.__drawFaceMeshFlag = False
        self.__drawFaceContoursFlag = False

        self.__drawFaceLandmarkFlag = False



        self.__faceSize = 0
        self.__faceCenter = [0, 0]

        self.__drawFaceNameFlag = True
        self.__drawFaceCenterFlag = True
        self.__drawLandmarkFlag = True
        self.__drawFaceSizeFlag = True

        self.__faceDataDict = dict()

        self.__faceRecognizeInitFlag = False
        self.__facecurrentResults  = False
        self.__faceTrainFlag = False
        self.__faceTrainName = None
        self.__faceRecognizedName = None


        # apriltag detector
        self.__aprilDetectInitFlag = False
        self.__aprilDetectFlag = False
        self.__drawAprilAreaFlag = True
        self.__drawAprilSizeFlag = True
        self.__drawAprilCenterFlag = True
        self.__drawAprilIdFlag = True


        self.__aprilTags =[] # info, id, center
        self.__aprilSize = 0




        # gesture detector
        self.__gestureDetectInitFlag = False
        self.__gestureDetectFlag = False
        self.__drawGestureAreaFlag = True

        self.__drawGestureNameFlag = True

        self.__drawGestureStatusFlag = True
        self.__drawGestureRecognizeFlag = True

        self.__drawGestureCenterFlag = True
        self.__drawGestureSizeFlag = True

        self.__gestureLandmark = []
        self.__gestureFingersStatus = []
        self.__gestureDetect = False

        self.__gestureFingersRecognize = None
        self.__palm_center = [0 ,0]
        self.__gestureCenter = [0 ,0]
        self.__gestureSize = 0



        # yolo_v8
        self.__yoloDetectInitFlag = False
        self.__yoloDetectFlag = False
        self.__drawYoloAreaFlag = True
        self.__drawYoloNameFlag = True
        self.__drawYoloCenterFlag = True
        self.__drawYoloSizeFlag = True

        self.__drawYoloName = None


        self.__yoloModel = None
        self.__yoloResults = []

        #self.__yoloTarget_classes = set()
        self.__yoloTarget_classes = set()
        self.__target_class_ids = [] # 감지할 클래스 ID를 저장할 리스트
        #self.__coco_class_names = self.__yoloModel.names


        self.__yoloStopSignDetect = False
        self.__yoloStopSignCenter = [0, 0]
        self.__yoloStopSignSize = 0

        self.__yoloTrafficLightDetect = False
        self.__yoloTrafficLightCenter = [0, 0]
        self.__yoloTrafficLightSize = 0

        self.__yoloTrafficLightColor = "UNKNOW"


        self.__yoloCorner = [0, 0, 0, 0]



        # sketch detector
        self.__sketchDetectFlag = False
        self.__sketchDetectInitFlag = False
        self.__drawSketchAreaFlag = True
        self.__drawSketchNameFlag = True
        self.__drawSketchPointFlag = True
        self.__drawSketchSizeFlag = True
        self.__sketchRecognizedList = []
        self.__sketchDetectedList = []
        self.__sketchDataDict = dict()


        # sign detector
        self.__signDetectInitFlag = False
        self.__signDetectFlag = False
        self.__signModelPath = None

        self.__signDetectedRegions=[]
        self.__signModel = None

        # number recognizer
        self.__numberDetectInitFlag = False
        self.__numberDetectFlag = False
        self.__drawNumberAreaFlag = True
        self.__drawNumberFlag = True
        self.__drawNumberPointFlag = True
        self.__drawNumberSizeFlag = True

        self.__numberRecognizedStr = ''
        self.__numberDetectedList = []



        print("camera module ready")
        # self.april_detector = Detector(families='tag25h9',
        #                nthreads=1,
        #                quad_decimate=1.0,
        #                quad_sigma=0.0,
        #                refine_edges=1,
        #                decode_sharpening=0.25,
        #                debug=0) # 필요시 debug=1 로 변경하여 내부 디버그 정보 확인

    # --- WebSocket Callbacks ---

    def on_open(self, ws):
        """Callback for when the WebSocket connection is opened."""
        self._connected = True
       # self._running = True # Set running flag when connected
        self._usePosConnected = True # Indicate device connection
        self._debugger._printLog("WebSocket connection opened.")

        print("opened")
        print(time.ctime())

        # Send initial requests as seen in the test client
        # These are often needed to start data streams from the server
        try:
            # Request video stream (handler doesn't process video, but server might need this)
            #ws.send("stream")
            # Request sensor data stream
            #ws.send("sensor")
            self._debugger._printLog("Sent initial 'stream' and 'sensor' requests.")
        except Exception as e:
             self._error(f"Failed to send initial messages: {e}")

    def on_message(self, ws, message):
        """Callback for when a message is received."""
        # # self._debugger._printLog(f"Received message: {len(message)} bytes") # Optional: log raw message arrival
        # if isinstance(message, bytes):
        #     # Process binary data packets
        #     #self._process_packet(message)
        #     # print("_process_packet")
        #     self._process_image_frame(message)
        # else:
        #     # Handle text messages or other types if necessary
        #     self._debugger._printLog(f"Received non-byte message: {type(message)}")
        #     # If text messages are part of the protocol, handle them here

        try:
            if isinstance(message, bytes):
                #print(len(message))
                if len(message) == self.SENSOR_DATA_LENGTH:
                    self._process_sensor_packet(message)
                    #print("sen")
                else:
                    self._process_image_frame(message)
            else:
                self._debugger._printLog(f"Unknown message type: {type(message)}")
        except Exception as e:
            self._debugger._printLog(f"Message handling error: {str(e)}")



    def on_error(self, ws, error):
        """Callback for WebSocket errors."""
        self._error(f"WebSocket error: {error}")
        self._connected = False # Connection is likely broken
        # _running might remain True until on_close is called, or until run_forever exits.


    def on_close(self, ws, close_status_code, close_msg):
        """Callback for when the WebSocket connection is closed."""
        self._debugger._printLog(f"WebSocket connection closed. Status: {close_status_code}, Message: {close_msg}")
        self._connected = False
        self._running = False # Signal that the handler should stop running
        self._usePosConnected = False # Indicate device is disconnected

    def _get_text_color_for_bg(self,bg_color):
        # BGR → 밝기 추정 (가중 평균)
        brightness = 0.299 * bg_color[2] + 0.587 * bg_color[1] + 0.114 * bg_color[0]
        return (0, 0, 0) if brightness > 128 else (255, 255, 255)

    # --- for putText ---
    def _drawPutTextBox(self, frame, text, x1, y1, y_offset, bg_color):
        # 텍스트 정보
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        # 텍스트 크기 계산
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # 텍스트를 그릴 시작점 (좌측 하단)
        # 텍스트는 x1에 맞춰지고, y1에서 y_offset만큼 위로 이동한 후, baseline과 텍스트 높이를 고려합니다.
        # YOLO 스타일은 보통 박스 위에 텍스트가 위치하므로,
        # 박스 상단 y1에서 text_height + baseline 만큼 위로 이동하고, y_offset을 추가로 적용합니다.
        # 즉, 텍스트가 시작될 y좌표는 y1 - text_height - baseline - y_offset 입니다.
        # 이 함수에서는 사각형을 먼저 그리고 그 안에 텍스트를 넣는 방식이므로,
        # 텍스트의 실제 시작점 (org)을 사각형 기준으로 계산해야 합니다.

        # 텍스트 박스의 좌측 상단 모서리 (rect_x1, rect_y1)
        # x1: 감지 박스의 x1 시작점
        # y1: 감지 박스의 y1 시작점
        # y_offset: y1으로부터 추가적으로 얼마나 떨어뜨릴지 (음수 값으로 위로 이동)

        # 텍스트 박스 시작점 (x, y) = (감지 박스 x1, 감지 박스 y1 - 텍스트 박스 높이 - y_offset)
        # padding을 줘서 사각형과 텍스트 사이에 여백을 둡니다.
        padding_x = 5 # X축 패딩
        padding_y = 5 # Y축 패딩

        # 텍스트 박스의 실제 좌상단 좌표
        text_box_x1 = x1 + padding_x
        # 텍스트 박스의 실제 좌상단 y 좌표는 감지 박스의 y1에서 위로 그려질 공간을 확보합니다.
        # 즉, y1 - (text_height + 2 * padding_y) - y_offset
        text_box_y1 = y1 - (text_height + 2 * padding_y) - y_offset # 사각형의 맨 위 Y 좌표

        # 텍스트 박스의 실제 우하단 좌표
        text_box_x2 = text_box_x1 + text_width + padding_x * 2
        text_box_y2 = y1 - y_offset # 사각형의 맨 아래 Y 좌표 (감지 박스의 상단 y1에 근접)


        # 텍스트 그릴 위치 (org)는 텍스트 박스 내부의 좌하단입니다.
        # 텍스트 박스 좌상단 x1 + padding_x
        # 텍스트 박스 좌상단 y1 + padding_y + text_height
        org = (text_box_x1 + padding_x, text_box_y1 + padding_y + text_height)


        # 색상 지정
        text_color = self._get_text_color_for_bg(bg_color)

        # 배경 사각형 그리기
        cv2.rectangle(
            frame,
            (text_box_x1, text_box_y1),  # 좌측 상단
            (text_box_x2, text_box_y2),  # 우측 하단
            bg_color,
            thickness=cv2.FILLED
        )

        # 텍스트 그리기
        cv2.putText(frame, text, org, font, font_scale, text_color, thickness, lineType=cv2.LINE_AA)



   # --- for putText  ---
    def _drawPutTextBox(self,frame, text, x1, y1, y_offset, bg_color):

        # 텍스트 정보
        #text = s1
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        # 텍스트 크기 계산
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # YOLO 스타일 위치 지정: 상자 안쪽 상단
        # org은 텍스트 기준 baseline 위치이므로 y1 + text_height를 더해줍니다
        org = (x1 + 2, y1 + text_height + 2+y_offset)  # 약간 오른쪽으로 이동하면 더 보기 좋음

        # 색상 지정
        text_color = self._get_text_color_for_bg(bg_color)
        #text_color = (255, 255, 255)  # 흰색
        #bg_color = (255, 0, 0)        # 파란 배경 (BGR)

        # 배경 사각형 먼저 그림 (YOLO 스타일 텍스트 박스)
        cv2.rectangle(
            frame,
            (org[0], org[1] - text_height),  # 좌측 상단
            (org[0] + text_width, org[1] + baseline),   # 우측 하단
            bg_color,
            thickness=cv2.FILLED
        )

        # 텍스트 그리기
        cv2.putText(frame, text, org, font, font_scale, text_color, thickness, lineType=cv2.LINE_AA)






    # --- face ---
    def _faceDetectorInit(self, face_recognize_threshold = 0.8):#0.2~2.0

        if self.__faceDetectInitFlag is False:
            # self.__faceD = FaceDetector()

            self.__mp_face_mesh = mp.solutions.face_mesh
            self.__mp_face_drawing = mp.solutions.drawing_utils
            self.__face_mesh = self.__mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.__faceDetectInitFlag = True

        # if self.__faceLandmarkInitFlag is False:
        #     # self.__landD = FaceLandmark()
        #     self.__faceLandmarkInitFlag = True

        if self.__faceRecognizeInitFlag is False:
            #self.__faceR = FaceRecognizer()
            # FaceRecognizer 초기화
            try:
                self.__face_recognizer = FaceRecognizer(face_recognaze_threshold= face_recognize_threshold) # 임계값 조정 가능 (0.2~1.0 사이)
            except FileNotFoundError:
                print("얼굴 인식 모델을 찾을 수 없어 FaceRecognizer를 초기화할 수 없습니다.")
                #exit()
            except Exception as e:
                print(f"FaceRecognizer 초기화 중 오류 발생: {e}.")
                #exit()

            self.__faceRecognizeInitFlag = True

        print("Facedetector initialized")

    def _faceDetectorStart(self):
        if self.__faceDetectInitFlag is False:
            print("Facedetector is not initialized")
            return

        if self.__faceDetectFlag == True:
            print("Facedetector is already working.")
            return
        self.__faceDetectFlag = True

        th = threading.Thread(target=self.__facedetect)
        th.deamon = True
        th.start()

    def _faceDetectorStop(self):
        if self.__faceDetectFlag == False :
            print("Facedetector is already stopped.")
            return

        self.__faceDetectFlag = False
        time.sleep(1)

        print("Facedetector off")

    def __facedetect(self):
        while self.__faceDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                print('no input frame yet')
                continue
            try:
                rgb_frame = cv2.cvtColor(self.__raw_img, cv2.COLOR_BGR2RGB)
                # FaceMesh 모델로 얼굴 랜드마크 처리
                # results 객체에 감지된 얼굴 랜드마크 정보가 포함됩니다.

                self.__faceResults = self.__face_mesh.process(rgb_frame)

                if self.__faceResults.multi_face_landmarks:

                    self.__facecurrentResults  = True

                    h, w, c = self.__raw_img.shape # 이미지 높이, 너비

                    # 감지된 첫 번째 얼굴의 랜드마크를 가져옴
                    self.__first_face_landmarks = self.__faceResults.multi_face_landmarks[0]

                    # --- 특정 랜드마크 좌표 추출 및 화면에 표시 예시 ---
                    self.__faceDataDict = {}
                    for landmark_type in face_landmark: # 모든 Enum 멤버에 대해 반복
                        coords = self.get_face_landmark_coordinates(self.__first_face_landmarks, landmark_type, w, h)
                        if coords:
                            self.__faceDataDict[landmark_type] = coords


                    # --- 얼굴 테두리 계산
                    x_coords = [landmark.x for landmark in self.__first_face_landmarks.landmark]
                    y_coords = [landmark.y for landmark in self.__first_face_landmarks.landmark]

                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)

                    bbox_x1 = int(x_min * w)
                    bbox_y1 = int(y_min * h)
                    bbox_x2 = int(x_max * w)
                    bbox_y2 = int(y_max * h)

                    padding_ratio = 0.1
                    bbox_width = bbox_x2 - bbox_x1
                    bbox_height = bbox_y2 - bbox_y1

                    pad_x = int(bbox_width * padding_ratio)
                    pad_y = int(bbox_height * padding_ratio)

                    bbox_x1 = max(0, bbox_x1 - pad_x)
                    bbox_y1 = max(0, bbox_y1 - pad_y)
                    bbox_x2 = min(w, bbox_x2 + pad_x)
                    bbox_y2 = min(h, bbox_y2 + pad_y)

                    self.__current_face_bbox = [bbox_x1, bbox_y1, bbox_x2, bbox_y2]

                    # --- 사각형의 중심점 계산
                    self.__faceCenter[0] = (self.__current_face_bbox[0] + self.__current_face_bbox[2]) // 2
                    self.__faceCenter[1] = (self.__current_face_bbox[1] + self.__current_face_bbox[3]) // 2

                    # --- 얼굴 사이즈 계산
                    face_width = self.__current_face_bbox[2] - self.__current_face_bbox[0]
                    face_height = self.__current_face_bbox[3] - self.__current_face_bbox[1]
                    self.__faceSize = face_width * face_height



                     # --- 이름 체크
                    recognized_array = self.__face_recognizer(self.__raw_img, [self.__current_face_bbox])
                    if len(recognized_array) > 0:
                        self.__faceRecognizedName = recognized_array[0]
                        # recognized_names_on_frame.append(self.__faceRecognizedName)

                        color = (0, 255, 255) # 기본 노란색
                        if self.__faceRecognizedName != 'Unknown' and self.__faceRecognizedName != 'Too Small' and self.__faceRecognizedName != 'Error':
                            color = (0, 255, 0) # 인식된 이름이면 초록색

                else:
                    self.__facecurrentResults  = False
                    self.__faceRecognizedName = 'Unknown'
                    self.__faceCenter = [0, 0]
                    self.__faceDataDict = {}
                    self.__faceSize=0

            except Exception as e:
                print("Detect : " , e)
                continue

            time.sleep(0.001)

    def __overlay_face_boxes(self, frame):

        if self.__facecurrentResults == True and self.__faceResults != None:
            color = (0, 255, 255) # 기본 노란색

            # 랜드마크 표시
            if self.__drawLandmarkFlag == True:

                if self.__drawFaceMeshFlag == True:
                    self.__mp_face_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=self.__first_face_landmarks,
                        connections=self.__mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.__mp_face_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                    )

                if self.__drawFaceContoursFlag == True:
                    self.__mp_face_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=self.__first_face_landmarks,
                        connections=self.__mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.__mp_face_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
                    )

                if self.__drawFaceLandmarkFlag == True:
                    # --- 딕셔너리에서 랜드마크 좌표를 가져와 화면에 표시 예시 ---
                    if face_landmark.LEFT_EYE in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.LEFT_EYE]
                        cv2.circle(frame, coords, 3, (255, 0, 0), -1) # 파란색 점

                    if face_landmark.RIGHT_EYE in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.RIGHT_EYE]
                        cv2.circle(frame, coords, 3, (0, 0, 255), -1) # 빨간색 점

                    if face_landmark.LEFT_EYEBROW in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.LEFT_EYEBROW]
                        cv2.circle(frame, coords, 3, (255, 100, 100), -1) # 파란색 점

                    if face_landmark.RIGHT_EYEBROW in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.RIGHT_EYEBROW]
                        cv2.circle(frame, coords, 3, (100, 100, 255), -1) # 빨간색 점

                    if face_landmark.NOSE in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.NOSE]
                        cv2.circle(frame, coords, 3, (0, 255, 0), -1) # 초록색 점

                    if face_landmark.MOUTH in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.MOUTH]
                        cv2.circle(frame, coords, 3, (0, 255, 255), -1) # 노란색 점

                    if face_landmark.JAW in self.__faceDataDict:
                        coords = self.__faceDataDict[face_landmark.JAW]
                        cv2.circle(frame, coords, 3, (255, 255, 0), -1) # 하늘색 점

            # 얼굴 테두리 표시
            if self.__drawFaceAreaFlag:
                cv2.rectangle(frame, (self.__current_face_bbox[0], self.__current_face_bbox[1]), (self.__current_face_bbox[2], self.__current_face_bbox[3]), color, 2)

            x1 = self.__current_face_bbox[0]
            y1 = self.__current_face_bbox[1]

            s0 = str(self.__faceRecognizedName)
            s1 = 'x=' + str(self.__faceCenter[0]) +' y='+str(self.__faceCenter[1])
            s2 = 'size=' + str(int(self.__faceSize))

            y_offset = 0
            color = (0, 255, 255) # 기본 노란색

            # 이름 표시
            if self.__drawFaceNameFlag == True:
                self._drawPutTextBox(frame, s0, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (30, 255, 255) # 다음 색상 지정

            # 중심점 표시
            if self.__drawFaceCenterFlag == True:
                self._drawPutTextBox(frame, s1, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (60, 255, 255) # 다음 색상 지정

            if self.__drawFaceSizeFlag == True:
                self._drawPutTextBox(frame, s2, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (90, 255, 255) # 다음 색상 지정


    def _faceTrain(self, name:str):
        if self.__faceTrainFlag == False:
            #print("FaceTrain")
            self.__faceTrainFlag = True
            self.__faceTrainName = name

    def _deleteFaceData(self, name:str):
        self.__face_recognizer.RemoveFace(name)
        self.__faceTrainFlag = False
        self.__faceTrainName = None

    def _deleteAllFaceData(self):
        self.__face_recognizer.RemoveAllFace() # 파일 시스템에서 이미지 및 .pkl 삭제
        self.__faceTrainFlag = False
        self.__faceTrainName = None

    def _isFaceDetected(self, name:str="Unknown") -> bool:
        _findName = False
        if self.__faceRecognizedName == name:
            _findName = True
        return _findName

    def _getDetectedFaceName(self) -> str:
        return self.__faceRecognizedName

    def _getFaceCenter(self) -> list:
        return self.__faceCenter

    def _getFaceSize(self) -> int:
        return self.__faceSize

    def _getFaceLandmark(self, landmark: face_landmark) -> list:
        if self.__facecurrentResults == True and self.__faceResults != None:
            if landmark == face_landmark.LEFT_EYE:
                return self.__faceDataDict[face_landmark.LEFT_EYE]
            elif landmark == face_landmark.RIGHT_EYE:
                return self.__faceDataDict[face_landmark.RIGHT_EYE]
            elif landmark == face_landmark.LEFT_EYEBROW:
                return self.__faceDataDict[face_landmark.LEFT_EYEBROW]
            elif landmark == face_landmark.RIGHT_EYEBROW:
                return self.__faceDataDict[face_landmark.RIGHT_EYEBROW]
            elif landmark == face_landmark.NOSE:
                return self.__faceDataDict[face_landmark.NOSE]
            elif landmark == face_landmark.MOUTH:
                return self.__faceDataDict[face_landmark.MOUTH]
            elif landmark == face_landmark.JAW:
                return self.__faceDataDict[face_landmark.JAW]
            else :
                return [0, 0]
        else :
                return [0, 0]

    # april
    def _aprilDetectorInit(self):
        if self.__aprilDetectInitFlag is False:

            self.__aprilD = Detector(families='tag25h9',
                        nthreads=1,
                        quad_decimate=1.0,
                        quad_sigma=0.0,
                        refine_edges=1,
                        decode_sharpening=0.25,
                        debug=0) # 필요시 debug=1 로 변경하여 내부 디버그 정보 확인

            self.__aprilDetectInitFlag = True
            self.__drawAprilAreaFlag = True
        print("April detector initialized")

    def _aprilDetectorStart(self):
        if self.__aprilDetectInitFlag is False:
            print("April detector is not initialized")
            return

        if self.__aprilDetectFlag == True:
            print("April detector is already working.")
            return
        self.__aprilDetectFlag = True

        th = threading.Thread(target=self.__aprildetect)
        th.deamon = True
        th.start()

    def _aprildetectorStop(self):
        if self.__aprilDetectFlag == False :
            print("April detector is already stopped.")
            return

        self.__aprilDetectFlag = False
        time.sleep(1)

        print("April detector off")

    def __aprildetect(self):
        while self.__aprilDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                print('no input frame yet')
                continue
            try:
                gray = cv2.cvtColor(self.__raw_img, cv2.COLOR_BGR2GRAY)
                # AprilTag 감지
                self.__aprilTags = self.__aprilD.detect(gray)

                for tag in self.__aprilTags:
                    x = self.__aprilTags[0].corners[:, 0]
                    y = self.__aprilTags[0].corners[:, 1]

                    self.__aprilSize = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


                #print(self.__aprilTags)

                # # 예시 detection object에서 corners 값 추출
                # detection_corners = np.array([
                #     [161.55827332, 165.22029114],
                #     [231.51037598, 154.01533508],
                #     [221.08227539, 82.63665009],
                #     [149.89685059, 92.12716675]
                # ])

                # # 모든 X 좌표 중 최소/최대값, 모든 Y 좌표 중 최소/최대값 찾기
                # min_x = np.min(detection_corners[:, 0])
                # max_x = np.max(detection_corners[:, 0])
                # min_y = np.min(detection_corners[:, 1])
                # max_y = np.max(detection_corners[:, 1])

                # # 바운딩 박스 너비와 높이
                # bbox_width = max_x - min_x
                # bbox_height = max_y - min_y

                # print(f"바운딩 박스 너비: {bbox_width:.2f} 픽셀")
                # print(f"바운딩 박스 높이: {bbox_height:.2f} 픽셀")


                # 슈레이스 공식 (Shoelace formula)을 사용하여 다각형 면적 계산
                # (x1y2 + x2y3 + x3y4 + x4y1) - (y1x2 + y2x3 + y3x4 + y4x1)
                # x = self.__aprilTags[0].corners[:, 0]
                # y = self.__aprilTags[0].corners[:, 1]

                # self.__aprilSize = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
                # print(f"다각형 면적: {self.__aprilSize:.2f} 픽셀^2")

                # [Detection object:
                # tag_family = b'tag25h9'
                # tag_id = 4
                # hamming = 0
                # decision_margin = 45.611053466796875
                # homography = [[ 3.77331906e+01  6.80398211e+00  1.91501846e+02]
                #  [-3.59211993e+00  3.69436373e+01  1.23676557e+02]
                #  [ 1.28310501e-02  6.73024659e-03  1.00000000e+00]]
                # center = [191.50184647 123.67655733]
                # corners = [[161.55827332 165.22029114]
                #  [231.51037598 154.01533508]
                #  [221.08227539  82.63665009]
                #  [149.89685059  92.12716675]]
                # pose_R = None
                # pose_t = None
                # pose_err = None
                # ]


                #coners, ids, markerDict = self.__aprilD(self.__raw_img)

                # if ids is not None:
                #     self.__aprilDetectedCorners = list(coners)
                #     self.__aprilDetectedIds = ids
                #     self.__aprilDataDict = copy.deepcopy(markerDict)
                # else:
                #     self.__aprilDetectedCorners = []
                #     self.__aprilDetectedIds = []
                #     self.__aprilDataDict = dict()

                #time.sleep(0.1)

            except Exception as e:
                print("April detector error : " , e)
                continue

            time.sleep(0.001)

    def __overlay_april_boxes(self,frame):

        duplicateId = []
        color = (0, 255, 0) #녹색

        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # # AprilTag 감지
        # tags = self.__aprilD.detect(gray)

        # 감지된 태그 정보 출력 및 시각화
        for tag in self.__aprilTags:
            #print(f"Tag ID: {tag.tag_id}, Center: {tag.center}, Corners: {tag.corners}")

            # Tag ID: 4,
            # Center: [206.1433955  138.54275798],
            # Corners: [[243.91590881 103.00775146]
            # [171.52641296  98.70207977]
            # [167.60879517 174.79470825]
            # [240.3183136  177.87466431]]

            # 태그 주변에 사각형 그리기
            for i in range(4):
                pt1 = tuple(map(int, tag.corners[i]))
                pt2 = tuple(map(int, tag.corners[(i + 1) % 4]))
                cv2.line(frame, pt1, pt2, color, 2)

            # 태그 ID 표시
            x1 = int(tag.corners[3][0])
            y1 = int(tag.corners[3][1])

            s0 = str(tag.tag_id)
            s1 = 'x=' + str(int(self.__aprilTags[0].center[0])) +' y='+str(int(self.__aprilTags[0].center[1]))
            s2 = 'size=' + str(int(self.__aprilSize))

            y_offset = 0
            color = (0, 255, 0) #녹색

            if self.__drawAprilIdFlag == True:
                self._drawPutTextBox(frame, s0, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (30, 255, 0) # 다음 색상 지정

            if self.__drawAprilCenterFlag == True:
                self._drawPutTextBox(frame, s1, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (60, 255, 0) # 다음 색상 지정

            if self.__drawAprilSizeFlag == True:
                self._drawPutTextBox(frame, s2, x1, y1, y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (90, 255, 0) # 다음 색상 지정


    def _isMarkerDetected(self,id:int)->bool:
        if self.__aprilTags is None or len(self.__aprilTags) == 0:
            return False
        else:
            if self.__aprilTags[0].tag_id == id:
                return True
            else :
                return False

    def _getAprilId(self) -> int:
        #print(self.__aprilTags)
        if self.__aprilTags is None or len(self.__aprilTags) == 0:
            return -1
        else:
            return self.__aprilTags[0].tag_id

    def _getAprilCenter(self) -> list:
        if self.__aprilTags is None or len(self.__aprilTags) == 0:
            pass
        else:
            return self.__aprilTags[0].center

    def _getAprilSize(self):
        if self.__aprilTags is None or len(self.__aprilTags) == 0:
            return 0
        else:
            # x = self.__aprilTags[0].corners[:, 0]
            # y = self.__aprilTags[0].corners[:, 1]

            # self.__aprilSize = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
            return self.__aprilSize


    # gesture
    def _gestureDetectorInit(self):
        if self.__gestureDetectInitFlag is False:

            # Mediapipe 설정
            self.__mp_hands = mp.solutions.hands
            self.__hands = self.__mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.__mp_drawing = mp.solutions.drawing_utils

            self.__gestureDetectInitFlag = True
            self.__drawGestureAreaFlag = True
        print("Gesture detector initialized")

    def _gestureDetectorStart(self):
        if self.__gestureDetectInitFlag is False:
            print("Gesture detector is not initialized")
            return

        if self.__gestureDetectFlag == True:
            print("Gesture detector is already working.")
            return
        self.__gestureDetectFlag = True

        th = threading.Thread(target=self.__gesturedetect)
        th.deamon = True
        th.start()

    def _gestureDetectorStop(self):
        if self.__gestureDetectFlag == False :
            print("Gesture detector is already stopped.")
            return

        self.__gestureDetectFlag = False
        time.sleep(1)

        print("Gesture detector off")

    def __gesturedetect(self):
        while self.__gestureDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                print('no input frame yet')
                continue
            try:

                img_rgb = cv2.cvtColor(self.__raw_img, cv2.COLOR_BGR2RGB)
                result = self.__hands.process(img_rgb)

                # if not result.multi_hand_landmarks:
                #     self.__gestureLandmark = []
                h, w, c = self.__raw_img.shape # 이미지 높이, 너비

                if result.multi_hand_landmarks:

                    self.__gestureDetect = True

                #     wrist_landmark = self.__gestureLandmark.landmark[mp.solutions.hands.HandLandmark.WRIST]
                #    # self.__current_hand_center = (int(wrist_landmark.x * w), int(wrist_landmark.y * h))
                #     print(int(wrist_landmark.x ))
                #방법 2: 모든 랜드마크의 평균을 중심점으로 사용 (더 정확할 수 있음)

                    for self.__gestureLandmark in result.multi_hand_landmarks:
                        #hand_landmarks = result.multi_hand_landmarks[0]
                        __hand_type_label = result.multi_handedness[0].classification[0].label
                        self.__gestureFingersStatus = self.__get_finger_status(self.__gestureLandmark,__hand_type_label)
                        self.__gestureFingersRecognize = self._getGestureRecognize()
                        #print(self.__recognize_gesture(fingers_status))
                        #print(self.__gestureLandmark)
                        # 손 랜드마크와 연결선 그리기
                        #self.__mp_drawing.draw_landmarks(frame, self.__gestureLandmark, self.__mp_hands.HAND_CONNECTIONS)


                        # 랜드마크 2번 (Thumb_CMC)
                        lm_2_x = int(self.__gestureLandmark.landmark[2].x * w)
                        lm_2_y = int(self.__gestureLandmark.landmark[2].y * h)

                        # 랜드마크 17번 (Pinky_MCP)
                        lm_17_x = int(self.__gestureLandmark.landmark[17].x * w)
                        lm_17_y = int(self.__gestureLandmark.landmark[17].y * h)

                        if 'Right' == __hand_type_label:
                            self.__palm_center[0] = lm_2_x
                            self.__palm_center[1] = (lm_2_y + lm_17_y) // 2
                        else: #Left
                            self.__palm_center[0] = lm_17_x
                            self.__palm_center[1] = (lm_2_y + lm_17_y) // 2

                        x_coords = [lm.x for lm in self.__gestureLandmark.landmark]
                        y_coords = [lm.y for lm in self.__gestureLandmark.landmark]
                        avg_x = np.mean(x_coords)
                        avg_y = np.mean(y_coords)
                        self.__gestureCenter = (int(avg_x * w), int(avg_y * h))
                        #print(self.__current_hand_center)

                        # --- 손의 크기 계산 로직 시작 ---
                        # 모든 랜드마크의 X, Y 좌표 추출 (정규화된 값)
                        all_x_coords = [lm.x for lm in self.__gestureLandmark.landmark]
                        all_y_coords = [lm.y for lm in self.__gestureLandmark.landmark]

                        # 이미지 픽셀 값으로 변환 (min/max 찾기 위해)
                        min_x_pixel = int(min(all_x_coords) * w)
                        max_x_pixel = int(max(all_x_coords) * w)
                        min_y_pixel = int(min(all_y_coords) * h)
                        max_y_pixel = int(max(all_y_coords) * h)

                        # 바운딩 박스 너비와 높이 계산
                        bbox_width = max_x_pixel - min_x_pixel
                        bbox_height = max_y_pixel - min_y_pixel

                        self.__gestureSize = bbox_width * bbox_height # (너비, 높이) 튜플로 저장


                else:
                        self.__gestureDetect = False
                        self.__gestureLandmark = []
                        self.__gestureFingersStatus= []

            except Exception as e:
                print("Gesture detector error : " , e)
                continue

            time.sleep(0.001)

    def __overlay_gesture_boxes(self, frame):

        self.__mp_drawing.draw_landmarks(frame, self.__gestureLandmark, self.__mp_hands.HAND_CONNECTIONS)

        if self.__gestureDetect == True:

            s0 = str(self.__gestureFingersStatus)
            s1 = self.__gestureFingersRecognize
            s2 = 'x=' + str(self.__gestureCenter[0]) +' y='+str(self.__gestureCenter[1])
            s3 = 'size=' + str(self.__gestureSize)

            y_offset = 0
            color = (255, 0, 0)        # 파랑

            if  self.__drawGestureStatusFlag == True:
                self._drawPutTextBox(frame, s0, self.__palm_center[0], self.__palm_center[1], y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 30, 0) # 다음 색상 지정

            if  self.__drawGestureRecognizeFlag == True:
                self._drawPutTextBox(frame, s1, self.__palm_center[0], self.__palm_center[1], y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 60, 0) # 다음 색상 지정

            if  self.__drawGestureCenterFlag == True:
                self._drawPutTextBox(frame, s2, self.__palm_center[0], self.__palm_center[1], y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 90, 0) # 다음 색상 지정

            if  self.__drawGestureSizeFlag == True:
                self._drawPutTextBox(frame, s3, self.__palm_center[0], self.__palm_center[1], y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 120, 0) # 다음 색상 지정


    def __get_finger_status(self, hand_landmarks, hand_type_label: str) -> list[int]:
        """
        손가락이 펴져 있는지 접혀 있는지 확인하는 내부 함수
        Args:
            hand_landmarks: MediaPipe에서 감지된 손 랜드마크 객체 (예: results.multi_hand_landmarks[0])
            hand_type_label (str): 'Left' 또는 'Right' 문자열 (MediaPipe에서 감지된 손의 타입)
        Returns:
            list[int]: [엄지, 검지, 중지, 약지, 새끼] 각 손가락의 상태 (1: 펴짐, 0: 쥐어짐)
        """
        fingers = []
        landmarks = hand_landmarks.landmark # 간결한 접근을 위해

        # 엄지손가락 판단 로직 (손 타입에 따라 X축 방향 반전)
        # 엄지 끝(landmark[4])이 엄지 중간(landmark[3])보다
        # 오른손의 경우 왼쪽에 있으면 펴짐 (x 값이 작음)
        # 왼손의 경우 오른쪽에 있으면 펴짐 (x 값이 큼)
        if hand_type_label == 'Right':
            if landmarks[4].x < landmarks[3].x:
                fingers.append(1) # 펴짐
            else:
                fingers.append(0) # 쥐어짐
        elif hand_type_label == 'Left':
            if landmarks[4].x > landmarks[3].x: # X축 방향 반대
                fingers.append(1) # 펴짐
            else:
                fingers.append(0) # 쥐어짐
        else:
            self._debugger._printLog(f"Warning: Unknown hand type label: {hand_type_label}. Cannot determine thumb status.")
            fingers.append(0) # 기본값으로 쥐어짐 처리

        # 나머지 손가락 (검지, 중지, 약지, 새끼손가락) 판단 로직 (Y축 기준)
        # 각 손가락의 팁(끝) (8, 12, 16, 20)이 PIP (6, 10, 14, 18) 위에 있으면 펼쳐진 상태 (Y값이 더 작음)
        tips = [8, 12, 16, 20]
        pip_joints = [6, 10, 14, 18]
        for tip_idx, pip_idx in zip(tips, pip_joints):
            if landmarks[tip_idx].y < landmarks[pip_idx].y:
                fingers.append(1) # 펴짐
            else:
                fingers.append(0) # 쥐어짐

        return fingers

    def _getGestureRecognize(self):
        if self.__gestureFingersStatus == [0, 0, 0, 0, 0]:
            return 'fist'
        elif self.__gestureFingersStatus == [0, 1, 0, 0, 0]:
            return 'point'
        elif self.__gestureFingersStatus == [1, 1, 1, 1, 1]:
            return 'open'
        elif self.__gestureFingersStatus == [0, 1, 1, 0, 0]:
            return 'peace'
        elif self.__gestureFingersStatus == [1, 1, 0, 0, 0]:
            return 'standby'
        elif self.__gestureFingersStatus == [1, 0, 0, 0, 0]:
            return 'thumbs_up'
        else:
            return 'None'



    def _isGestureDetected(self):
        return self.__gestureDetect

    def _getGestureFinger(self):
        return self.__gestureFingersStatus

    def _getGestureCenter(self):
        return self.__gestureCenter

    def _getGestureSize(self):
        return self.__gestureSize


    # yolo
    def _yoloDetectorInit(self):
        if self.__yoloDetectInitFlag is False:
            self.__yoloDetectInitFlag = True
            self.__drawYoloAreaFlag = True

            self.__yoloModel = YOLO("yolov8n.pt")  # yolov8s.pt, yolov8m.pt 등으로 변경 가능
            self.__coco_class_names = self.__yoloModel.names
        print("Yolo detector initialized")

    def _yoloDetectorStart(self):
        if self.__yoloDetectInitFlag is False:
            print("Yolo detector is not initialized")
            return
        if self.__yoloDetectFlag == True:
            print("Yolo detector is already working.")
            return

        # 인식할 대상 추가
        self._yoloCheckAddObj("stop sign")
        self._yoloCheckAddObj("traffic light")

        self.__yoloDetectFlag = True

        th = threading.Thread(target=self.__yolodetect)
        th.deamon = True
        th.start()

    def _yoloDetectorStop(self):
        if self.__yoloDetectFlag == False :
            print("Yolo detector is already stopped.")
            return

        self.__yoloDetectFlag = False
        time.sleep(1)
        print("Yolo detector off")

    def __yolodetect(self):
        while self.__yoloDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                print('no input frame yet')
                continue
            try:
                #self.__yoloResults = self.__yoloModel(self.__raw_img, verbose=False, imgsz=320, conf=0.6)  # 신뢰도(confidence) 설정
                self.__yoloResults = self.__yoloModel(self.__raw_img, verbose=False, imgsz=320, conf=0.6, classes=self.__target_class_ids)

                if self.__yoloResults and len(self.__yoloResults) > 0:

                    boxes = self.__yoloResults[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        class_ids = boxes.cls.cpu().numpy().astype(int)
                        names = [self.__yoloModel.names[c] for c in class_ids]

                        for i, name in enumerate(names):
                            if name in self.__yoloTarget_classes:

                                x1, y1, x2, y2 = map(int, boxes.xyxy[0])
                                width = abs(x2 - x1)
                                height = abs(y2 - y1)

                                self.__yoloCorner[0] = x1
                                self.__yoloCorner[1] = y1
                                self.__yoloCorner[2] = x2
                                self.__yoloCorner[3] = y2

                                self.__drawYoloName = name

                                if name == "stop sign":
                                    self.__yoloStopSignDetect = True
                                    self.__yoloStopSignCenter[0] = (x1 + y1) // 2
                                    self.__yoloStopSignCenter[1] = (x2 + y2) // 2
                                    self.__yoloStopSignSize = width * height

                                elif name == "traffic light":
                                    self.__yoloTrafficLightDetect = True
                                    self.__yoloTrafficLightCenter[0] = (x1 + y1) // 2
                                    self.__yoloTrafficLightCenter[1] = (x2 + y2) // 2
                                    self.__yoloTrafficLightSize = width * height

                                    traffic_light_roi = self.__raw_img[y1:y2, x1:x2]

                                    # HSV 변환
                                    hsv = cv2.cvtColor(traffic_light_roi, cv2.COLOR_BGR2HSV)
                                    # 빨강 범위 1 (0~10)
                                    lower_red1 = (0, 70, 50)
                                    upper_red1 = (10, 255, 255)

                                    # 빨강 범위 2 (170~180)
                                    lower_red2 = (170, 70, 50)
                                    upper_red2 = (180, 255, 255)

                                    # 색상 마스크 정의 (범위는 조정 가능)
                                    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
                                    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
                                    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
                                    mask_yellow = cv2.inRange(hsv, (15, 70, 70), (35, 255, 255))
                                    mask_green  = cv2.inRange(hsv, (40, 50, 50),  (90, 255, 255))

                                    # 픽셀 개수 기준 판단
                                    red_count    = cv2.countNonZero(mask_red)
                                    yellow_count = cv2.countNonZero(mask_yellow)
                                    green_count  = cv2.countNonZero(mask_green)

                                    counts = {
                                        'RED': red_count,
                                        'YELLOW': yellow_count,
                                        'GREEN': green_count
                                    }
                                    max_color = max(counts, key=counts.get)
                                    max_count = counts[max_color]

                                    if max_count > 50:
                                        if max_color == 'RED':
                                            self.__yoloTrafficLightColor = "RED"
                                        elif max_color == 'YELLOW':
                                            self.__yoloTrafficLightColor = "YELLOW"
                                        elif max_color == 'GREEN':
                                            self.__yoloTrafficLightColor = "GREEN"
                                    else:
                                        self.__yoloTrafficLightColor = "UNKNOW"

                    else:
                        self.__yoloStopSignDetect = False
                        self.__yoloStopSignCenter = [0, 0]
                        self.__yoloTrafficLightDetect = False
                        self.__yoloTrafficLightCenter = [0, 0]
                        self.__yoloTrafficLightColor = "UNKNOW"

                else:
                    self.__yoloStopSignDetect = False
                    self.__yoloStopSignCenter = [0, 0]
                    self.__yoloTrafficLightDetect = False
                    self.__yoloTrafficLightCenter = [0, 0]
                    self.__yoloTrafficLightColor = "UNKNOW"


            except Exception as e:
                print("Yolo detector error : " , e)
                continue

            time.sleep(0.001)

    def __overlay_yolo_boxes(self, frame):

        if self.__yoloResults and len(self.__yoloResults) > 0:
            boxes = self.__yoloResults[0].boxes
            if boxes is not None and len(boxes) > 0:

                x1 = self.__yoloCorner[0]
                y1 = self.__yoloCorner[1]
                x2 = self.__yoloCorner[2]
                y2 = self.__yoloCorner[3]

                if self.__yoloStopSignDetect == True:

                    color = (255, 0, 0)        # 파란 배경 (BGR)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    s0 = "stop sign"
                    s1 = 'x=' + str(self.__yoloStopSignCenter[0]) +' y='+str(self.__yoloStopSignCenter[1])
                    s2 = 'size=' + str(self.__yoloStopSignSize)

                    y_offset = 0
                    color = (255, 0, 0)        # 파랑

                    if self.__drawYoloNameFlag == True:
                        self._drawPutTextBox(frame,s0,x1,y1,y_offset,color)
                        y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                        color = (255, 30, 0) # 다음 색상 지정

                    if self.__drawYoloCenterFlag == True:
                        self._drawPutTextBox(frame,s1,x1,y1,y_offset,color)
                        y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                        color = (255, 60, 0) # 다음 색상 지정

                    if self.__drawYoloSizeFlag == True:
                        self._drawPutTextBox(frame,s2,x1,y1,y_offset,color)
                        y_offset = y_offset + 18  # 다음 위치 지정
                        color = (255, 90, 0) # 다음 색상 지정

                elif self.__yoloTrafficLightDetect == True:

                    color = (255, 0, 0)        # 파란 배경 (기본)

                    if self.__yoloTrafficLightColor == 'RED':
                        color = (0, 0, 255)        # 빨강
                    elif self.__yoloTrafficLightColor == 'YELLOW':
                        color = (0, 255, 255)      # 노랑
                    elif self.__yoloTrafficLightColor == 'GREEN':
                        color = (0, 255, 0)        # 녹색

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    s0 = self.__yoloTrafficLightColor
                    s1 = 'x=' + str(self.__yoloTrafficLightCenter[0]) +' y='+str(self.__yoloTrafficLightCenter[1])
                    s2 = 'size=' + str(self.__yoloTrafficLightSize)

                    new_color = (color[0], color[1], color[2])
                    y_offset = 0
                    if self.__drawYoloNameFlag == True:

                        self._drawPutTextBox(frame, s0, x1, y1, y_offset, new_color)
                        y_offset = y_offset + self.__text_offset
                        new_color = (30, color[1], color[2])
                    if self.__drawYoloCenterFlag == True:

                        self._drawPutTextBox(frame, s1, x1, y1, y_offset, new_color)
                        y_offset = y_offset + self.__text_offset
                        new_color = (60, color[1], color[2])

                    if self.__drawYoloSizeFlag == True:
                        self._drawPutTextBox(frame, s2, x1, y1, y_offset, new_color)
                        y_offset = y_offset + self.__text_offset
                        new_color = (90, color[1], color[2])


    def _isStopSignDetected(self):
        return self.__yoloStopSignDetect

    def _getStopSignCenter(self):
        return self.__yoloStopSignCenter

    def get_stop_sign_size(self):
        return self.__yoloStopSignSize

    def _isTrafficLightDetected(self):
        return self.__yoloTrafficLightDetect

    def _getTrafficLightCenter(self):
        return self.__yoloTrafficLightCenter

    def _getTrafficLightSize(self):
        return self.__yoloTrafficLightSize

    def _getTrafficLightColor(self):
        return self.__yoloTrafficLightColor


    # 감지 대상에 객체 추가
    def _yoloCheckAddObj(self, obj_name=""):
        if not self.__yoloModel:
            print("❌ 모델이 로드되지 않았습니다. 객체를 추가할 수 없습니다.")
            return

        if obj_name:
            # 클래스 이름으로 ID 찾기
            found_id = None
            for class_id, class_name in self.__coco_class_names.items():
                if class_name == obj_name:
                    found_id = class_id
                    break

            if found_id is not None:
                if obj_name not in self.__yoloTarget_classes:
                    self.__yoloTarget_classes.add(obj_name)
                    self.__target_class_ids.append(found_id)
                    print(f"✅ '{obj_name}' (ID: {found_id}) 추가됨")
                else:
                    print(f"ℹ️ '{obj_name}' 이미 감지 대상에 있습니다.")
            else:
                print(f"❌ '{obj_name}' 모델의 클래스 목록에 없습니다.")


    # 감지 대상에서 객체 제거
    def _yoloCheckDelObj(self, obj_name=""):
        if not self.__yoloModel:
            print("❌ 모델이 로드되지 않았습니다. 객체를 제거할 수 없습니다.")
            return

        if obj_name:
            if obj_name in self.__yoloTarget_classes:
                self.__yoloTarget_classes.remove(obj_name)
                # 제거된 객체의 ID도 self.__target_class_ids에서 제거해야 합니다.
                # 클래스 ID는 중복될 수 없으므로, obj_name에 해당하는 첫 번째 ID만 제거하면 됩니다.
                found_id = None
                for class_id, class_name in self.__coco_class_names.items():
                    if class_name == obj_name:
                        found_id = class_id
                        break
                if found_id is not None and found_id in self.__target_class_ids:
                    self.__target_class_ids.remove(found_id)
                print(f"🗑️ '{obj_name}' 제거됨")
            else:
                print(f"ℹ️ '{obj_name}' 감지 대상에 없습니다.")

    # 전체 클래스 추가
    def _yoloCheckAllAddObj(self):
        if not self.__yoloModel:
            print("❌ 모델이 로드되지 않았습니다. 전체 클래스를 추가할 수 없습니다.")
            return

        self.__yoloTarget_classes.clear() # 기존 대상 초기화
        self.__target_class_ids.clear()   # 기존 ID 초기화

        for class_id, class_name in self.__coco_class_names.items():
            self.__yoloTarget_classes.add(class_name)
            self.__target_class_ids.append(class_id)
        print(f"➕ 모든 {len(self.__coco_class_names)}개 클래스가 감지 대상에 추가됨.")

    # 감지 대상 전체 제거
    def _yoloCheckAllDelObj(self):
        self.__yoloTarget_classes.clear()
        self.__target_class_ids.clear()
        print("➖ 모든 감지 대상이 제거됨.")



    # --- sensor ---
    def _sensorInit(self):
        if self.__sensorInitFlag is False:
            self._ws.send("sensor")

            self.__sensorInitFlag = True
            self.__drawSensorAreaFlag = True
        print("Sensor initialized")


    def _sensorStart(self):
        if self.__sensorInitFlag is False:
            print("Sensor is not initialized")
            return

        if self.__sensorFlag == True:
            print("Sensor is already working.")
            return
        self.__sensorFlag = True


    def _sensorStop(self):
        if self.__sensorFlag == False :
            print("Sensor is already stopped.")
            return

        self.__sensorFlag = False
        time.sleep(1)

        print("Sensor off")





    def _process_sensor_packet(self, data):
        """센서 데이터 처리"""
        if data[:2] != self.SENSOR_HEADER:
            self._debugger._printLog(f"Invalid sensor header: {data[:2].hex()}")
            return

        bat_offset = 0
        if data[8] > 100 :
            bat_offset = 3

        sensor_values = {
            'FR': data[2],
            'FL': data[3],
            'BR': data[4],
            'BL': data[5],
            'BC': data[6],
            'BTN': data[7],
            'BAT': data[8] - bat_offset,
            'STAT': data[9]
        }

        try:
            self._sensor_queue.put_nowait(sensor_values)
            #self.last_sensor_time = time.time()
        except queue.Full:
            self._debugger._printLog("Sensor queue overflow")


    def _get_latest_sensors(self):
        """최신 센서 값 가져오기"""
        latest = {}
        while not self._sensor_queue.empty():
            latest = self._sensor_queue.get_nowait()
        return latest

    def _sensor_overlay(self, frame, sensors):
        """마지막 센서 값 유지 기능 추가"""
        # 클래스 변수로 마지막 센서 값 저장
        if not hasattr(self, '_last_sensors'):
            self._last_sensors = {}

        # 새 센서 값이 있으면 업데이트, 없으면 마지막 값 사용
        if sensors:
            self._last_sensors = sensors.copy()
        else:
            sensors = self._last_sensors.copy()

        # 센서 값 표시
        if sensors:
            y = 30
            for key, value in sensors.items():
                text = f"{key}: {value}"
                cv2.putText(frame, text, (10, y),
                           cv2.FONT_ITALIC, 0.5, (0, 255, 255), 2)
                y += 20

        # FPS 표시 (기존 코드 유지)
        elapsed = time.time() - self._start_time
        fps = self._frame_count / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, frame.shape[0]-20),
                   cv2.FONT_ITALIC, 0.5, (255, 255, 0), 2)



    def send(self, data):
        """
        """
        if not self.isConnected():
            self._debugger._printLog("Not connected, cannot send raw data.")
            return

        if not isinstance(data, (bytes, bytearray)):
            self._error("Send data must be bytes or bytearray.")
            return

        with self._send_lock: # Protects the underlying ws.send call
            # try:
            #     self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
            #     # self._debugger._printLog(f"Sent raw data: {data.hex(' ')}") # Optional: log sent data
            # except websocket.WebSocketException as e:
            #     self._error(f"Failed to send raw WebSocket data: {e}")
            #     self._connected = False # Assume connection issue
            if self._connected and self._ws:
                try:
                    self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                    print("패킷 전송 성공:", data.hex(' '))
                except Exception as e:
                    print("패킷 전송 실패:", e)





    def get_face_landmark_coordinates(self, face_landmarks_result, landmark_enum: face_landmark, image_width, image_height): # FaceLandmark -> face_landmark
        """
        MediaPipe FaceMesh 결과에서 특정 얼굴 랜드마크의 좌표를 추출합니다.

        Args:
            face_landmarks_result: MediaPipe `results.multi_face_landmarks` 리스트의 단일 얼굴 랜드마크 객체 (예: results.multi_face_landmarks[0]).
            landmark_enum (face_landmark): 추출할 랜드마크 유형 (face_landmark Enum). # FaceLandmark -> face_landmark
            image_width (int): 원본 이미지의 너비.
            image_height (int): 원본 이미지의 높이.

        Returns:
            tuple[int, int] or None: 지정된 랜드마크의 (x, y) 픽셀 좌표.
                                    여러 랜드마크가 정의된 경우 평균 좌표를 반환합니다.
                                    감지되지 않거나 유효하지 않은 경우 None.
        """
        if not face_landmarks_result:
            return None

        landmark_indices = MEDIAPIPE_LANDMARK_MAP.get(landmark_enum)
        if not landmark_indices:
            print(f"오류: 알 수 없는 랜드마크 유형입니다: {landmark_enum.name}")
            return None

        points = []
        for idx in landmark_indices:
            # 랜드마크 인덱스가 유효한지 확인
            if 0 <= idx < len(face_landmarks_result.landmark):
                landmark = face_landmarks_result.landmark[idx]
                # 랜드마크 좌표는 0.0 ~ 1.0 범위의 정규화된 값입니다. 픽셀 단위로 변환합니다.
                x = int(landmark.x * image_width)
                y = int(landmark.y * image_height)
                points.append((x, y))
            else:
                print(f"경고: 랜드마크 인덱스 {idx}가 범위를 벗어납니다. (총 {len(face_landmarks_result.landmark)}개)")
                # 하나의 중요한 랜드마크라도 없으면 이 부위의 좌표는 얻을 수 없다고 판단
                return None

        if not points:
            return None

        # 여러 점이 정의된 경우 평균 좌표를 반환하여 해당 부위의 중심점을 나타냅니다.
        if len(points) > 1:
            avg_x = sum([p[0] for p in points]) / len(points)
            avg_y = sum([p[1] for p in points]) / len(points)
            return int(avg_x), int(avg_y)
        else:
            return points[0] # 한 점만 정의된 경우 그 점을 반환

    # --- vision ---

    def _cameraLeftRightFlip(self, flag:bool):
        self.__flipLRFlag = flag

    def _cameraStream(self):

        if self.__cameraStreamFlag == True :
            print("The camera is already working.")
            return

        self.__cameraStreamFlag = True

        self._ws.send("stream")

        self._display_thread = threading.Thread(target=self.__camera_display)
        # 스레드를 데몬 스레드로 설정하면 메인 프로그램 종료 시 함께 종료됩니다. 필요에 따라 설정하세요.
        # self._display_thread.daemon = True
        # 스레드 시작
        self._display_thread.start()

    def __camera_display(self):
        print("start_display")
        """영상 디스플레이 메인 루프"""

        # print("\n---------------------------------------------------------")
        # print("웹캠을 시작합니다. 'q' 키를 눌러 종료하세요.")
        # print("  - 'r' 키: 얼굴 등록 모드 시작 (이름 입력 후 여러 번 등록 가능)")
        # print("  - 'e' 키: 얼굴 등록 모드 종료")
        # print("  - 'c' 키: 등록된 모든 얼굴 데이터 삭제")
        # print("---------------------------------------------------------\n")

        #-------------------------------------------------------------------------

        #while self._connected:
        while self.__cameraStreamFlag:
            try:
                frame = self._frame_queue.get(timeout=2.0)
                self.__raw_img = frame.copy()

                # 센서 값 화면 오버레이
                if self.__sensorFlag == True:
                    if self.__drawSensorAreaFlag == True:
                        sensors = self._get_latest_sensors()
                        self._sensor_overlay(frame, sensors)

                # 얼굴 인식 화면 오버레이
                if self.__faceDetectFlag == True:
                    self.__overlay_face_boxes(frame)

                # apriltag 인식 화면 오버레이
                if self.__aprilDetectFlag == True:
                    if self.__drawAprilAreaFlag == True:
                        #print("ap")
                        self.__overlay_april_boxes(frame)

                # 제스처 인식 화면 오버레이
                if self.__gestureDetectFlag == True:
                    if self.__drawGestureAreaFlag == True:
                        self.__overlay_gesture_boxes(frame)

                # yolo 인식 화면 오버레이
                if self.__yoloDetectFlag == True:
                    if self.__drawYoloAreaFlag == True:
                        # if self.__yoloResults and len(self.__yoloResults) > 0:
                        #      frame = self.__yoloResults[0].plot()
                        self.__overlay_yolo_boxes(frame)

                # # 스케치 인식 화면 오버레이
                # if self.__sketchDetectFlag == True:
                #     if self.__drawSketchAreaFlag == True:
                #         self.__overlay_sketch_boxes(frame)


                # # 숫자 인식 화면 오버레이
                # if self.__numberDetectFlag == True:
                #     if self.__drawNumberAreaFlag == True:
                #         self.__overlay_number_boxes(frame)

                # if self.__signDetectFlag == True:
                #    for (x, y, w, h) in self.__signDetectedRegions:
                #        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2) # 초록색 사각형

                if self.__faceTrainFlag == True:
                    #r키를 눌러 연속 캡쳐, e키를 눌러 종료
                    cv2.putText(frame, "-press r : capture", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50,50,250), 2)
                    cv2.putText(frame, "-press e : end", (10, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50,50,250), 2)

                cv2.imshow("ZumiAI Stream", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.__faceDetectFlag = False
                    self.__aprilDetectFlag = False
                    self.__numberDetectFlag = False
                    self.__sketchDetectFlag = False
                    self.__gestureDetectFlag = True
                    break

                elif key == ord('s') and frame is not None:
                    # 's' 키를 누르면 현재 프레임 저장
                    cv2.imwrite(f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg", frame)
                    print("img save")

                elif key == ord('r'): # 'r' 키를 누르면 현재 얼굴 등록
                    if self.__faceTrainFlag == True:
                        if self.__facecurrentResults == True and self.__faceResults != None:
                            # if current_registration_name is None:
                            #     # 등록할 이름이 아직 정해지지 않았다면 입력받기
                            #     print("\n--- 얼굴 등록 모드 ---")
                            #     name_input = input("등록할 얼굴의 이름을 입력하세요 (영문/숫자): ")
                            #     if not name_input.strip():
                            #         print("이름이 입력되지 않았습니다. 등록을 취소합니다.")
                            #         continue
                            #     current_registration_name = name_input.strip()
                            #     print(f"'{current_registration_name}' 등록 모드를 시작합니다. 이 상태에서 'r' 키를 여러 번 눌러 얼굴을 추가 등록하세요.")
                            #     print("등록 모드 종료는 'e' 키를 누르세요.")

                            # 현재 감지된 첫 번째 얼굴을 등록
                            face_landmarks = self.__faceResults.multi_face_landmarks[0]
                            h, w, c = frame.shape # 이미지 높이, 너비
                            x_coords = [landmark.x for landmark in face_landmarks.landmark]
                            y_coords = [landmark.y for landmark in face_landmarks.landmark]
                            x_min, x_max = min(x_coords), max(x_coords)
                            y_min, y_max = min(y_coords), max(y_coords)

                            bbox_x1 = int(x_min * w)
                            bbox_y1 = int(y_min * h)
                            bbox_x2 = int(x_max * w)
                            bbox_y2 = int(y_max * h)

                            # 등록 시에도 여백 추가 (일관된 전처리)
                            padding_ratio = 0.1
                            bbox_width = bbox_x2 - bbox_x1
                            bbox_height = bbox_y2 - bbox_y1
                            pad_x = int(bbox_width * padding_ratio)
                            pad_y = int(bbox_height * padding_ratio)
                            bbox_x1 = max(0, bbox_x1 - pad_x)
                            bbox_y1 = max(0, bbox_y1 - pad_y)
                            bbox_x2 = min(w, bbox_x2 + pad_x)
                            bbox_y2 = min(h, bbox_y2 + pad_y)

                            self.__face_recognizer.TrainModel(frame, [bbox_x1, bbox_y1, bbox_x2, bbox_y2], self.__faceTrainName)
                        else:
                            print("얼굴이 감지되지 않아 등록할 수 없습니다.")

                elif key == ord('e'): # 'e' 키를 눌러 등록 모드 종료
                    if self.__faceTrainFlag == True:
                        self.__faceTrainFlag = False
                        if self.__faceTrainName is not None:
                            if self.__faceTrainName in self.__face_recognizer.registerd:
                                print(f"'{self.__faceTrainName}' 등록 모드를 종료합니다. 등록된 얼굴 수: {self.__face_recognizer.registerd[self.__faceTrainName].extra.shape[0]}개.")
                            else:
                                print(f"'{self.__faceTrainName}' 등록 모드를 종료합니다. 등록된 얼굴이 없습니다.")
                            self.__faceTrainName = None
                            self.__face_recognizer._save_registered_faces() # 등록 모드 종료 시 데이터 저장
                            print("---------------------------------------------------------")
                        else:
                            print("현재 등록 모드가 아닙니다.")

                #-------------------------------------------------------------------------
                # elif key == ord('r'): # 'r' 키를 누르면 현재 얼굴 등록
                #     if results.multi_face_landmarks:
                #         if current_registration_name is None:
                #             # 등록할 이름이 아직 정해지지 않았다면 입력받기
                #             print("\n--- 얼굴 등록 모드 ---")
                #             name_input = input("등록할 얼굴의 이름을 입력하세요 (영문/숫자): ")
                #             if not name_input.strip():
                #                 print("이름이 입력되지 않았습니다. 등록을 취소합니다.")
                #                 continue
                #             current_registration_name = name_input.strip()
                #             print(f"'{current_registration_name}' 등록 모드를 시작합니다. 이 상태에서 'r' 키를 여러 번 눌러 얼굴을 추가 등록하세요.")
                #             print("등록 모드 종료는 'e' 키를 누르세요.")

                #         # 현재 감지된 첫 번째 얼굴을 등록
                #         face_landmarks = results.multi_face_landmarks[0]

                #         x_coords = [landmark.x for landmark in face_landmarks.landmark]
                #         y_coords = [landmark.y for landmark in face_landmarks.landmark]
                #         x_min, x_max = min(x_coords), max(x_coords)
                #         y_min, y_max = min(y_coords), max(y_coords)

                #         bbox_x1 = int(x_min * w)
                #         bbox_y1 = int(y_min * h)
                #         bbox_x2 = int(x_max * w)
                #         bbox_y2 = int(y_max * h)

                #         # 등록 시에도 여백 추가 (일관된 전처리)
                #         bbox_width = bbox_x2 - bbox_x1
                #         bbox_height = bbox_y2 - bbox_y1
                #         pad_x = int(bbox_width * padding_ratio)
                #         pad_y = int(bbox_height * padding_ratio)
                #         bbox_x1 = max(0, bbox_x1 - pad_x)
                #         bbox_y1 = max(0, bbox_y1 - pad_y)
                #         bbox_x2 = min(w, bbox_x2 + pad_x)
                #         bbox_y2 = min(h, bbox_y2 + pad_y)

                #         face_recognizer.TrainModel(frame, [bbox_x1, bbox_y1, bbox_x2, bbox_y2], current_registration_name)
                #     else:
                #         print("얼굴이 감지되지 않아 등록할 수 없습니다.")

                # elif key == ord('e'): # 'e' 키를 눌러 등록 모드 종료
                #     if current_registration_name is not None:
                #         if current_registration_name in face_recognizer.registerd:
                #             print(f"'{current_registration_name}' 등록 모드를 종료합니다. 등록된 얼굴 수: {face_recognizer.registerd[current_registration_name].extra.shape[0]}개.")
                #         else:
                #             print(f"'{current_registration_name}' 등록 모드를 종료합니다. 등록된 얼굴이 없습니다.")
                #         current_registration_name = None
                #         face_recognizer._save_registered_faces() # 등록 모드 종료 시 데이터 저장
                #         print("---------------------------------------------------------")
                #     else:
                #         print("현재 등록 모드가 아닙니다.")

                # elif key == ord('c'): # 'c' 키를 누르면 모든 등록된 얼굴 지우기
                #     if input("정말로 모든 등록된 얼굴을 지우시겠습니까? (y/n): ").lower() == 'y':
                #         face_recognizer.RemoveAllFace() # 파일 시스템에서 이미지 및 .pkl 삭제
                #         face_recognizer.registerd = {} # 메모리에서도 등록 정보 지우기
                #         current_registration_name = None # 등록 모드도 초기화
                #         print("모든 등록된 얼굴이 지워졌습니다.")
                #     else:
                #         print("모든 얼굴 삭제를 취소했습니다.")


                #-------------------------------------------------------------------------




            except queue.Empty:
                if time.time() - self._last_frame_time > 5:
                    self._error("No frames received for 5 seconds")
                    print(time.ctime())
                    #self._connected = False
                #continue
        self.stop()


    def stop(self):
        """리소스 정리"""
        print("stop")
        print(time.ctime())
        self.running = False
        if self._ws:
            self._ws.close()
        # ws 스레드가 있다면 join 시도 (데몬 스레드이므로 프로그램 종료시 함께 종료됨)
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=1)
        cv2.destroyAllWindows()


    def _process_image_frame(self, data):

        """영상 프레임 처리"""
        try:
            # 비동기 디코딩을 위한 스레드 풀 사용
            self._decode_frame_async(data)
        except Exception as e:
            self._error(f"Frame processing error: {str(e)}")

    def _decode_frame_async(self, data):
        """별도 스레드에서 프레임 디코딩"""
        import threading
        threading.Thread(target=self._async_decode_task, args=(data,)).start()

    def _async_decode_task(self, data):
        """실제 디코딩 작업"""
        try:
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            #img = cv2.flip(img, 1) # 별도의 함수 필요
            if self.__flipLRFlag == True:
                img = cv2.flip(img, 1)

            if img is not None:
                self._enqueue_frame(img)
            else:
                self._debugger._printLog("Failed to decode image")
        except Exception as e:
            self._error(f"Decoding error: {str(e)}")

    def _enqueue_frame(self, frame):
        """프레임 큐에 안전하게 저장"""
        try:
            self._frame_queue.put_nowait(frame)
            self._frame_count += 1
            self._last_frame_time = time.time()
        except queue.Full:
            self._frames_dropped += 1
            if self._frames_dropped % 30 == 0:
                self._error(f"Dropped frames: {self._frames_dropped}")

    # --- Internal Data Processing ---


    def _process_packet(self, data):
        """Internal method to process received binary data packets."""
        # self._debugger._printLog(f"Processing packet: {data.hex(' ')}") # Optional: log packet hex

        with self._data_lock:
            # Check for Sensor Data Packet (7 bytes, Header $R)
            if data.startswith(WS_SENSOR_HEADER) and len(data) == WS_SENSOR_DATA_LENGTH:
                # Process sensor data (5 bytes after header) - mapping from test code
                try:
                    # Test code mapping: FR, FL, BR, BL, BC
                    self._packet_senFR = data[2]
                    self._packet_senFL = data[3]
                    self._packet_senBR = data[4]
                    self._packet_senBL = data[5]
                    self._packet_senBC = data[6]
                    # self._debugger._printLog("Processed sensor packet") # Optional: log specific packet type
                except IndexError:
                    self._error(f"Received sensor packet with unexpected length: {len(data)} bytes")

            # Check for Status/Detection Data Packet (assumed 24 bytes, Header $S)
            # This is based on the serial handler's data fields
            elif data.startswith(WS_STATUS_HEADER) and len(data) == WS_STATUS_DATA_LENGTH:
                 try:
                     # Process status/detection data based on assumed indices
                     self._reqCOM = data[_STATUS_INDEX_REQ_COM]
                     self._reqINFO = data[_STATUS_INDEX_REQ_INFO]
                     self._reqREQ = data[_STATUS_INDEX_REQ_REQ]
                     self._reqPSTAT = data[_STATUS_INDEX_REQ_PSTAT]

                     # Assuming 3 bytes each for detection data
                     self._detectFace = list(data[_STATUS_INDEX_DETECT_FACE : _STATUS_INDEX_DETECT_FACE + 3])
                     self._detectColor = list(data[_STATUS_INDEX_DETECT_COLOR : _STATUS_INDEX_DETECT_COLOR + 3])
                     self._detectMarker = list(data[_STATUS_INDEX_MARKER : _STATUS_INDEX_MARKER + 3])
                     self._detectCat = list(data[_STATUS_INDEX_CAT : _STATUS_INDEX_CAT + 3])

                     self._btn = data[_STATUS_INDEX_BTN]
                     self._battery = data[_STATUS_INDEX_BATTERY]
                     # self._debugger._printLog("Processed status packet") # Optional: log specific packet type

                 except IndexError:
                     self._error(f"Received status packet with unexpected length or index error: {len(data)} bytes")

            # Add other packet types here if known (e.g., Image data header check)
            # elif data.startswith(IMAGE_HEADER):
            #     # If you needed to queue raw image data for external processing
            #     pass

            else:
                 # Log packets that don't match known types or lengths
                 header_hex = data[:2].hex(' ') if len(data) >= 2 else data.hex(' ')
                 self._debugger._printLog(f"Received unknown packet type or length: {len(data)} bytes, Header: {header_hex}")


    # --- Connection Management ---

    def connect(self, url=None):
        """
        Establishes the WebSocket connection to the specified URL.
        Starts a background thread to run the WebSocket client.
        """

        if self.isConnected():
            self._debugger._printLog("WebSocket handler is already connected.")
            return True

        if url:
            self._url = url
        if not self._url:
            self._error("WebSocket URL is not set. Cannot connect.")
            return False

        #self._debugger._printLog("aa")

        self._debugger._printLog(f"Attempting to connect to WebSocket: {self._url}")
        self._running = True # Indicate that the handler is starting its process

        try:
            # Create WebSocketApp instance with callbacks
            self._ws = websocket.WebSocketApp(
                self._url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Start the connection loop in a separate thread.
            # run_forever is blocking, so needs a thread.
            self._ws_thread = threading.Thread(target=self._ws.run_forever)
            self._ws_thread.daemon = True # Allow the main program to exit even if this thread is running
            self._ws_thread.start()

            # Wait briefly for the connection to potentially establish
            # The on_open callback will set self._connected = True asynchronously
            time.sleep(1) # Adjust sleep time as needed

            if self.isConnected():
                self._debugger._printLog("WebSocket connection initiated successfully.")
                # Note: self._connected is set True in on_open callback
                return True
            else:
                # Connection might still be pending or failed quickly before on_error/on_close fired
                self._debugger._printLog("WebSocket connection initiation status: Pending or failed.")
                # The on_error/on_close callbacks will provide final status.
                return False

        except Exception as e:
            # Catch exceptions during WebSocketApp creation or thread start
            self._error(f"Failed to create or start WebSocket client: {e}")
            self._running = False # Ensure running flag is false on failure
            self._connected = False
            self._usePosConnected = False
            self._ws = None # Clear the instance
            return False


    def close(self):
        """
        Closes the WebSocket connection and stops the background thread.
        """
        if not self._running and not self.isConnected():
             self._debugger._printLog("WebSocket handler is not running or connected.")
             return

        self._debugger._printLog("Closing WebSocket connection.")
        self._running = False # Signal the thread/callbacks to stop gracefuly

        if self._ws:
            try:
                # Initiate the WebSocket closing handshake
                self._ws.close()
                self._debugger._printLog("WebSocket close method called.")
            except Exception as e:
                self._error(f"Error calling WebSocket close: {e}")

        # Wait for the WebSocket thread to terminate.
        # Daemon threads don't strictly need joining for program exit,
        # but joining ensures cleanup finishes if needed.
        if self._ws_thread and self._ws_thread.is_alive():
            self._debugger._printLog("Joining WebSocket thread.")
            self._ws_thread.join(timeout=5) # Wait up to 5 seconds

        self._ws = None # Clear the WebSocket instance
        self._connected = False
        self._usePosConnected = False
        self._debugger._printLog("WebSocket connection closed.")


    def isOpen(self):
        """
        Checks if the underlying WebSocket object exists.
        Note: Use isConnected() to check if the connection is active.
        """
        # This method is more relevant for serial ports. For WebSocket,
        # self._connected is the main indicator of an active link.
        # Kept for compatibility, but self._connected is preferred.
        return self._ws is not None #and self._connected # prefer isConnected


    def isConnected(self):
        """
        Checks if the WebSocket connection is currently active.
        This relies on the internal `connected` flag updated by the callbacks.
        """
        # Both our internal running flag and the connected state should be true
        return self._connected and self._running

    # Add more set_* methods here for other robot control commands (e.g., set_arm_angle)
    # def set_arm_angle(self, angle):
    #     with self._send_lock:
    #         self._arm_angle = max(0, min(180, int(angle)))
    #     self._send_arm_packet() # Requires defining a new packet type/method


    def send(self, data):
        """
        Sends arbitrary raw data bytes over the WebSocket connection.
        For standard control commands (motor, LED), use set_motor/set_led methods
        as they handle packet formatting. This method is for sending custom
        or unformatted binary data if needed by the protocol.

        Args:
            data (bytes or bytearray): The binary data to send.
        """
        if not self.isConnected():
            self._debugger._printLog("Not connected, cannot send raw data.")
            return

        if not isinstance(data, (bytes, bytearray)):
            self._error("Send data must be bytes or bytearray.")
            return

        with self._send_lock: # Protects the underlying ws.send call
            try:
                self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                # self._debugger._printLog(f"Sent raw data: {data.hex(' ')}") # Optional: log sent data
            except websocket.WebSocketException as e:
                self._error(f"Failed to send raw WebSocket data: {e}")
                self._connected = False # Assume connection issue


    # --- Getting Received Data ---
    # These methods provide access to the latest received data values.
    # Access is thread-safe due to the self._data_lock in _process_packet.

    # --- Debug/Logging Helpers ---

    def _log(self, message):
        """Logs an informational message using the debugger or standard logging."""
        if self._debugger:
            self._debugger._printLog(message)
        else:
            self.logger.info(message)

    def _error(self, message):
        """Logs an error message using the debugger or standard logging."""
        if self._debugger:
            self._debugger._printError(message)
        else:
            self.logger.error(message)
