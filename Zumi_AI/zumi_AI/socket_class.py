#websocket
import cv2
import numpy as np
import websocket
#import argparse
import time
import threading
import queue

#import logging



#import pkg_resources
import copy
import os



#import mediapipe as mp
#from pupil_apriltags import Detector
#from ultralytics import YOLO

#import tensorflow as tf
# from tensorflow import keras

from .receiver import *

#from .face_landmark import FaceLandmark
#from .face_recognizer import FaceRecognizer
#from .number_recognizer import NumberRecognizer
#from .sketch_recognizer import SketchProcessor



class SketchData:
    def __init__(self, name:str, box:list, confidence:list):
        self.name = name
        self.box = box
        self.confidence = confidence

        self.centerX = int((self.box[0][0] + self.box[2][0]) / 2)
        self.centerY = int((self.box[0][1] + self.box[2][1]) / 2)

        self.size = abs(int(self.box[2][0] - self.box[0][0])) * abs(int(self.box[2][1] - self.box[0][1])) #w*h

# Define packet constants based on WebSocket test code and assumptions
WS_SENSOR_HEADER = bytes([0x24, 0x52]) # $R
WS_SENSOR_DATA_LENGTH = 7 # Header (2) + Sensor Values (5: FR, FL, BR, BL, BC)
# Assume a similar status packet exists over WebSocket
WS_STATUS_HEADER = bytes([0x24, 0x53]) # $S (Assuming a different header for status)
# Based on serial handler's data mapping (22 data bytes after 2 header bytes)
WS_STATUS_DATA_LENGTH = 24 # Header (2) + Status Data (22)

# Define data indices for the assumed status packet (relative to start of packet)
# These map to the serial handler's PacketDataIndex values directly, assuming the header is 2 bytes
# Using a dict or Enum would be better, but hardcoding based on serial code's _handler logic
_STATUS_INDEX_REQ_COM = 2
_STATUS_INDEX_REQ_INFO = 3
_STATUS_INDEX_REQ_REQ = 4
_STATUS_INDEX_REQ_PSTAT = 5
_STATUS_INDEX_DETECT_FACE = 8 # Start of 3 bytes (assuming serial's index 8 is 1st byte)
_STATUS_INDEX_DETECT_COLOR = 11 # Start of 3 bytes
_STATUS_INDEX_DETECT_MARKER = 14 # Start of 3 bytes
_STATUS_INDEX_DETECT_CAT = 17 # Start of 3 bytes
_STATUS_INDEX_BTN = 20
_STATUS_INDEX_BATTERY = 21
# Note: This mapping assumes indices relative to the start of the 24-byte status packet.
# Example: reqCOM is dataArray[PacketDataIndex.DATA_COM.vaFlue - self.headerLen] in serial.
# If PacketDataIndex.DATA_COM.value is 4 and self.headerLen is 2, it reads dataArray[2].
# So, in the 24-byte packet, this corresponds to index 2. This confirms the mapping.




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


        self.__text_offset = 18 #putText

        self.__screen_width = 320 #putText
        self.__screen_height = 240 #putText

        self.sensor_values = None

        # FPS frame rate
        self.__drawFPSFlag = True

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
        self.__faceRecognizedConfidenceScore = None


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
        self.__palm_center = [0, 0]
        self.__gestureCenter = [0, 0]
        self.__gestureSize = 0



        # yolo_v8
        self.__yoloDetectInitFlag = False
        self.__yoloDetectFlag = False
        self.__drawYoloAreaFlag = True
        self.__drawYoloNameFlag = True
        self.__drawYoloCenterFlag = True
        self.__drawYoloSizeFlag = True

        self.__yoloModel = None
        self.__yoloResults = []
        self.__yoloTarget_classes = set()
        self.__target_class_ids = [] # 감지할 클래스 ID를 저장할 리스트
        self.__yoloDetections = []
        self.__yoloTrafficLightColor = "UNKNOW"


        # sketch detector
        self.__sketchDetectFlag = False
        self.__sketchDetectInitFlag = False
        self.__drawSketchAreaFlag = True
        self.__drawSketchNameFlag = True
        self.__drawSketchPointFlag = True
        self.__drawSketchSizeFlag = True
        self.__sketchRecognizedList = []
        self.__sketchDetectedList = []
        self.__sketchConfidenceList= []
        self.__sketchDataDict = dict()
        self.__sketchTrainFlag = False
        self.__sketchTrainName = None


        #teachable machine
        self.__teachableInitFlag = False
        self.__teachableDetectFlag = False
        self.__drawTeachablAreaFlag  = True

        self.__teachableInterpreter = None

        self.__teachableInputDetails = None
        self.__teachableOutputDetails = None

        self.__teachableLabels = []

        self.teachableModelPath = None
        self.teachableLabelPath = None

        self.teachableClassName = None
        self.teachableConfidenceScore = None


        print("camera module ready")

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

    # --- for putText  ---
    def convert_center_pos(self, posX, posY):
        center_x = self.__screen_width  / 2
        center_y = self.__screen_height / 2

        new_x = int(posX - center_x)
        new_y =  int(-(posY - center_y)) # Y축은 위로 양수, 아래로 음수가 되도록 반전
        return new_x, new_y



    # --- face ---
    def _faceDetectorInit(self, face_recognize_threshold = 0.8):#0.2~2.0

        import mediapipe as mp
        from .face_recognizer import FaceRecognizer


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

                    self.__faceCenter[0], self.__faceCenter[1] = self.convert_center_pos(self.__faceCenter[0], self.__faceCenter[1])


                    # --- 얼굴 사이즈 계산
                    face_width = self.__current_face_bbox[2] - self.__current_face_bbox[0]
                    face_height = self.__current_face_bbox[3] - self.__current_face_bbox[1]
                    self.__faceSize = face_width * face_height

                     # --- 이름 체크
                    # recognized_array = self.__face_recognizer(self.__raw_img, [self.__current_face_bbox])

                    # if len(recognized_array) > 0:
                    #     self.__faceRecognizedName = recognized_array[0]
                    #     # recognized_names_on_frame.append(self.__faceRecognizedName)

                    #     color = (0, 255, 255) # 기본 노란색
                    #     if self.__faceRecognizedName != 'Unknown' and self.__faceRecognizedName != 'Too Small' and self.__faceRecognizedName != 'Error':
                    #         color = (0, 255, 0) # 인식된 이름이면 초록색

                    # --- 이름 및 신뢰도 체크 (수정된 부분) ---
                    # recognized_array는 이제 [(이름, 신뢰도), ...] 형태의 리스트
                    recognized_results = self.__face_recognizer(self.__raw_img, [self.__current_face_bbox])

                    if len(recognized_results) > 0:
                        recognized_name, confidence_score = recognized_results[0] # 첫 번째 얼굴 정보 추출
                        self.__faceRecognizedName = recognized_name
                        self.__faceRecognizedConfidenceScore = round(confidence_score, 2)

                        # 신뢰도 점수 활용 (예: 출력 또는 특정 로직에 사용)
                        #print(f"인식된 이름: {self.__faceRecognizedName}, 신뢰도: {confidence_score:.2f}")

                        # color = (0, 255, 255) # 기본 노란색
                        # if self.__faceRecognizedName != 'Unknown' and self.__faceRecognizedName != 'Too Small' and self.__faceRecognizedName != 'Error':
                        #     color = (0, 255, 0) # 인식된 이름이면 초록색
                        #     # 신뢰도 점수에 따라 색상 변경 등 추가 로직 가능
                        #     if confidence_score < 0.5: # 예시: 낮은 신뢰도일 경우 다른 색상
                        #         color = (0, 165, 255) # 주황색

                else:
                    self.__facecurrentResults  = False
                    self.__faceRecognizedName = 'Unknown'
                    self.__faceRecognizedConfidenceScore = 0
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

            #s0 = str(self.__faceRecognizedName)
            s0 = str(self.__faceRecognizedName) +" "+ str(self.__faceRecognizedConfidenceScore)
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
        if self.__faceDetectFlag == False:
            print("먼저 얼굴 인식 기능을 시작해주세요.")
            return

        if self.__faceTrainFlag == False:
            self.__faceTrainFlag = True
            self.__faceTrainName = name
            print("얼굴 학습 모드를 시작합니다.")

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

    def _getDetectedFaceConfidenceScore(self):
        return self.__faceRecognizedConfidenceScore

    def _getDetectedFaceResult(self):
        return self.__faceRecognizedName, self.__faceRecognizedConfidenceScore


    def _faceLandmarkVisible(self, flag):
        if flag == True:
            if self.__drawFaceLandmarkFlag == True:
                print("Face Landmark visible is already working.")
                return
            self.__drawFaceLandmarkFlag = True

        else:
            if self.__drawFaceLandmarkFlag == False:
                print("Face Landmark visible is already stopped.")
                return
            self.__drawFaceLandmarkFlag = False


    def _faceContoursVisible(self, flag):
        if flag == True:
            if self.__drawFaceContoursFlag == True:
                print("Face Contours visible is already working.")
                return
            self.__drawFaceContoursFlag = True

        else:
            if self.__drawFaceContoursFlag == False:
                print("Face Contours visible is already stopped.")
                return
            self.__drawFaceContoursFlag = False


    def _getFaceLandmark(self, landmark: face_landmark) -> list:
        if self.__facecurrentResults == True and self.__faceResults != None:

            convertPos = []
            if landmark == face_landmark.LEFT_EYE:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.LEFT_EYE][0], self.__faceDataDict[face_landmark.LEFT_EYE][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.LEFT_EYE]
            elif landmark == face_landmark.RIGHT_EYE:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.RIGHT_EYE][0], self.__faceDataDict[face_landmark.RIGHT_EYE][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.RIGHT_EYE]
            elif landmark == face_landmark.LEFT_EYEBROW:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.LEFT_EYEBROW][0], self.__faceDataDict[face_landmark.LEFT_EYEBROW][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.LEFT_EYEBROW]
            elif landmark == face_landmark.RIGHT_EYEBROW:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.RIGHT_EYEBROW][0], self.__faceDataDict[face_landmark.RIGHT_EYEBROW][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.RIGHT_EYEBROW]
            elif landmark == face_landmark.NOSE:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.NOSE][0], self.__faceDataDict[face_landmark.NOSE][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.NOSE]
            elif landmark == face_landmark.MOUTH:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.MOUTH][0], self.__faceDataDict[face_landmark.RMOUTHIGHT_EYE][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.MOUTH]
            elif landmark == face_landmark.JAW:
                convertPos = self.convert_center_pos(self.__faceDataDict[face_landmark.JAW][0], self.__faceDataDict[face_landmark.JAW][1])
                return convertPos
                #return self.__faceDataDict[face_landmark.JAW]
            else :
                return [0, 0]
        else :
                return [0, 0]

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

            #avg_x, avg_y = self.convert_center_pos(avg_x, avg_y)

            return int(avg_x), int(avg_y)
        else:
            return points[0] # 한 점만 정의된 경우 그 점을 반환

    # april
    def _aprilDetectorInit(self):

        from pupil_apriltags import Detector

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
            convertPos =[]
            convertPos = self.convert_center_pos(tag.center[0], tag.center[1])
            s1 = 'x=' + str(convertPos[0]) +' y='+str(convertPos[1])



            x = tag.corners[:, 0]
            y = tag.corners[:, 1]
            april_size = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

            s2 = 'size=' + str(int(april_size))


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
            convertPos =[]
            convertPos = self.convert_center_pos(self.__aprilTags[0].center[0], self.__aprilTags[0].center[1])
            return convertPos

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
        import mediapipe as mp

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
                        #self.__gestureCenter = (int(avg_x * w), int(avg_y * h))
                        self.__gestureCenter[0] = int(avg_x * w)
                        self.__gestureCenter[1] = int(avg_y * h)

                        self.__gestureCenter[0], self.__gestureCenter[1] = self.convert_center_pos(
                            self.__gestureCenter[0], self.__gestureCenter[1])

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
    def _yoloDetectorInit(self, performance_mode = "speed"):

        from ultralytics import YOLO

        if self.__yoloDetectInitFlag is False:
            self.__yoloDetectInitFlag = True
            self.__drawYoloAreaFlag = True

            model_map = {
                "speed": "yolov8n.pt",
                "balance": "yolov8s.pt",
                "power": "yolov8m.pt"
            }
            selected_model = model_map.get(performance_mode, "yolov8n.pt")

            if selected_model == "yolov8n.pt":
                print("🔧 mode set : speed")
            elif selected_model == "yolov8s.pt":
                print("🔧 mode set : balance")
            elif selected_model == "yolov8m.pt":
                print("🔧 mode set : power")

            self.__yoloModel = YOLO(selected_model)

           # self.__yoloModel = YOLO("yolov8n.pt")  # yolov8s.pt, yolov8m.pt 등으로 변경 가능
           # self.__yoloModel = YOLO("YOLOv8s.pt")  # yolov8s.pt, yolov8m.pt 등으로 변경 가능
           # self.__yoloModel = YOLO("yolov8m.pt")  # yolov8s.pt, yolov8m.pt 등으로 변경 가능

            self.__coco_class_names = self.__yoloModel.names
        print("Yolo detector initialized")

    def _yoloDetectorStart(self):
        if self.__yoloDetectInitFlag is False:
            print("Yolo detector is not initialized")
            return
        if self.__yoloDetectFlag == True:
            print("Yolo detector is already working.")
            return

        # Classes
        # names:
        #   0: person
        #   1: bicycle
        #   2: car
        #   3: motorcycle
        #   4: airplane
        #   5: bus
        #   6: train
        #   7: truck
        #   8: boat
        #   9: traffic light
        #   10: fire hydrant
        #   11: stop sign
        #   12: parking meter
        #   13: bench
        #   14: bird
        #   15: cat
        #   16: dog
        #   17: horse
        #   18: sheep
        #   19: cow
        #   20: elephant
        #   21: bear
        #   22: zebra
        #   23: giraffe
        #   24: backpack
        #   25: umbrella
        #   26: handbag
        #   27: tie
        #   28: suitcase
        #   29: frisbee
        #   30: skis
        #   31: snowboard
        #   32: sports ball
        #   33: kite
        #   34: baseball bat
        #   35: baseball glove
        #   36: skateboard
        #   37: surfboard
        #   38: tennis racket
        #   39: bottle
        #   40: wine glass
        #   41: cup
        #   42: fork
        #   43: knife
        #   44: spoon
        #   45: bowl
        #   46: banana
        #   47: apple
        #   48: sandwich
        #   49: orange
        #   50: broccoli
        #   51: carrot
        #   52: hot dog
        #   53: pizza
        #   54: donut
        #   55: cake
        #   56: chair
        #   57: couch
        #   58: potted plant
        #   59: bed
        #   60: dining table
        #   61: toilet
        #   62: tv
        #   63: laptop
        #   64: mouse
        #   65: remote
        #   66: keyboard
        #   67: cell phone
        #   68: microwave
        #   69: oven
        #   70: toaster
        #   71: sink
        #   72: refrigerator
        #   73: book
        #   74: clock
        #   75: vase
        #   76: scissors
        #   77: teddy bear
        #   78: hair drier
        #   79: toothbrush

        self._yoloCheckAddObj("person")
        # self._yoloCheckAddObj("bicycle")
        self._yoloCheckAddObj("car")
        # self._yoloCheckAddObj("motorcycle")
        # self._yoloCheckAddObj("airplane")
        self._yoloCheckAddObj("bus")
        # self._yoloCheckAddObj("train")
        self._yoloCheckAddObj("truck")
        # self._yoloCheckAddObj("boat")
        self._yoloCheckAddObj("traffic light")
        # self._yoloCheckAddObj("fire hydrant")
        self._yoloCheckAddObj("stop sign")
        # self._yoloCheckAddObj("parking meter")
        # self._yoloCheckAddObj("bench")
        # self._yoloCheckAddObj("bird")
        self._yoloCheckAddObj("cat")
        self._yoloCheckAddObj("dog")
        # self._yoloCheckAddObj("horse")
        # self._yoloCheckAddObj("sheep")
        # self._yoloCheckAddObj("cow")
        # self._yoloCheckAddObj("elephant")
        # self._yoloCheckAddObj("bear")
        # self._yoloCheckAddObj("zebra")
        # self._yoloCheckAddObj("giraffe")
        # self._yoloCheckAddObj("backpack")
        # self._yoloCheckAddObj("umbrella")
        # self._yoloCheckAddObj("handbag")
        # self._yoloCheckAddObj("tie")
        # self._yoloCheckAddObj("suitcase")
        # self._yoloCheckAddObj("frisbee")
        # self._yoloCheckAddObj("skis")
        # self._yoloCheckAddObj("snowboard")
        # self._yoloCheckAddObj("sports ball")
        # self._yoloCheckAddObj("kite")
        # self._yoloCheckAddObj("baseball bat")
        # self._yoloCheckAddObj("baseball glove")
        # self._yoloCheckAddObj("skateboard")
        # self._yoloCheckAddObj("surfboard")
        # self._yoloCheckAddObj("tennis racket")
        # self._yoloCheckAddObj("bottle")
        # self._yoloCheckAddObj("wine glass")
        # self._yoloCheckAddObj("cup")
        # self._yoloCheckAddObj("fork")
        # self._yoloCheckAddObj("knife")
        # self._yoloCheckAddObj("spoon")
        # self._yoloCheckAddObj("bowl")
        # self._yoloCheckAddObj("banana")
        # self._yoloCheckAddObj("apple")
        # self._yoloCheckAddObj("sandwich")
        # self._yoloCheckAddObj("orange")
        # self._yoloCheckAddObj("broccoli")
        # self._yoloCheckAddObj("carrot")
        # self._yoloCheckAddObj("hot dog")
        # self._yoloCheckAddObj("pizza")
        # self._yoloCheckAddObj("donut")
        # self._yoloCheckAddObj("cake")
        # self._yoloCheckAddObj("chair")
        # self._yoloCheckAddObj("couch")
        # self._yoloCheckAddObj("potted plant")
        # self._yoloCheckAddObj("bed")
        # self._yoloCheckAddObj("dining table")
        # self._yoloCheckAddObj("toilet")
        # self._yoloCheckAddObj("tv")
        # self._yoloCheckAddObj("laptop")
        # self._yoloCheckAddObj("mouse")
        # self._yoloCheckAddObj("remote")
        # self._yoloCheckAddObj("keyboard")
        # self._yoloCheckAddObj("cell phone")
        # self._yoloCheckAddObj("microwave")
        # self._yoloCheckAddObj("oven")
        # self._yoloCheckAddObj("toaster")
        # self._yoloCheckAddObj("sink")
        # self._yoloCheckAddObj("refrigerator")
        # self._yoloCheckAddObj("book")
        # self._yoloCheckAddObj("clock")
        # self._yoloCheckAddObj("vase")
        # self._yoloCheckAddObj("scissors")
        # self._yoloCheckAddObj("teddy bear")
        # self._yoloCheckAddObj("hair drier")
        # self._yoloCheckAddObj("toothbrush")


        # 인식할 대상 추가
        # self._yoloCheckAddObj("stop sign")
        # self._yoloCheckAddObj("traffic light")

        # self._yoloCheckAddObj("person")
        # self._yoloCheckAddObj("dog")
        # self._yoloCheckAddObj("cat")

        # self._yoloCheckAddObj("bicycle")
        # self._yoloCheckAddObj("car")
        # self._yoloCheckAddObj("motorcycle")
        # self._yoloCheckAddObj("bus")
        # self._yoloCheckAddObj("truck")


        # #self._yoloCheckAddObj("parking meter")
        # #self._yoloCheckAddObj("bench")
        # #self._yoloCheckAddObj("fire hydrant")

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

                self.__yoloDetections = []  # 감지된 객체들 리스트 초기화

                if self.__yoloResults and len(self.__yoloResults) > 0:
                    boxes = self.__yoloResults[0].boxes

                    if boxes is not None and len(boxes) > 0:
                        class_ids = boxes.cls.cpu().numpy().astype(int)
                        names = [self.__yoloModel.names[c] for c in class_ids]
                        confidences = boxes.conf.cpu().numpy()
                        xyxy = boxes.xyxy.cpu().numpy().astype(int)

                        for i, name in enumerate(names):
                            if name in self.__yoloTarget_classes:
                                x1, y1, x2, y2 = xyxy[i]

                                # ================================================
                                # ▼▼▼ 신호등 색상 판별 로직 추가 ▼▼▼
                                # ================================================
                                if name == "traffic light":
                                    # 신호등 영역(ROI) 이미지를 잘라냅니다.
                                    traffic_light_roi = self.__raw_img[y1:y2, x1:x2]
                                    # 새로 만든 헬퍼 함수로 색상을 판별합니다.
                                    color = self._determine_traffic_color(traffic_light_roi)
                                    self.__yoloTrafficLightColor = color
                                # ================================================
                                # ▲▲▲ 신호등 색상 판별 로직 끝 ▲▲▲
                                # ================================================


                                width = abs(x2 - x1)
                                height = abs(y2 - y1)
                                center_x = (x1 + x2) // 2
                                center_y = (y1 + y2) // 2
                                center_x, center_y = self.convert_center_pos(center_x, center_y)

                                detection = {
                                    "name": name,
                                    "confidence": round(float(confidences[i]), 2),
                                    "corner": (x1, y1, x2, y2),
                                    "center": (center_x, center_y),
                                    "size": width * height
                                }
                                self.__yoloDetections.append(detection)


            except Exception as e:
                print("Yolo detector error : " , e)
                continue

            time.sleep(0.001)


    def __overlay_yolo_boxes(self, frame):

        if self.__yoloResults and len(self.__yoloResults) > 0:

            for detection in self.__yoloDetections:
                x1, y1, x2, y2 = detection["corner"]
                name = detection["name"]
                confidence = detection["confidence"]
                center_x, center_y = detection["center"]
                size = detection["size"]

                # 박스 그리기
                color = (255, 0, 0)
                # ================================================
                # ▼▼▼ 신호등 색상 표시 로직 추가 ▼▼▼
                # ================================================

                if name == "traffic light":
                    if self.__yoloTrafficLightColor == 'RED':
                        color = (0, 0, 255)        # 빨강
                    elif self.__yoloTrafficLightColor == 'YELLOW':
                        color = (0, 255, 255)      # 노랑
                    elif self.__yoloTrafficLightColor == 'GREEN':
                        color = (0, 255, 0)        # 녹색

                # ================================================
                # ▲▲▲ 신호등 색상 표시 로직 끝 ▲▲▲
                # ================================================

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # 텍스트 정보
                y_offset = 0

                if self.__drawYoloNameFlag:
                    s0 = f"{name} {confidence}"
                    self._drawPutTextBox(frame, s0, x1, y1, y_offset, color)
                    y_offset += self.__text_offset

                if self.__drawYoloCenterFlag:
                    s1 = f"x={center_x} y={center_y}"
                    self._drawPutTextBox(frame, s1, x1, y1, y_offset, color)
                    y_offset += self.__text_offset

                if self.__drawYoloSizeFlag:
                    s2 = f"size={size}"
                    self._drawPutTextBox(frame, s2, x1, y1, y_offset, color)
                    y_offset += self.__text_offset


    def _determine_traffic_color(self, roi_image) -> str:
        """
        입력된 ROI 이미지에서 신호등 색상을 판별합니다.

        Args:
            roi_image: 신호등 영역만 잘라낸 이미지 (BGR)

        Returns:
            str: "RED", "YELLOW", "GREEN", "UNKNOWN" 중 하나
        """
        # ROI가 비어있거나 너무 작으면 바로 UNKNOWN 반환
        if roi_image is None or roi_image.size == 0:
            return "UNKNOWN"

        # HSV로 변환
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)

        # 색상 범위 정의
        # 빨강 (두 개의 범위를 합쳐서 사용)
        lower_red1 = (0, 70, 50)
        upper_red1 = (10, 255, 255)
        lower_red2 = (170, 70, 50)
        upper_red2 = (180, 255, 255)
        # 노랑
        lower_yellow = (15, 70, 70)
        upper_yellow = (35, 255, 255)
        # 초록
        lower_green = (40, 50, 50)
        upper_green = (90, 255, 255)

        # 각 색상에 대한 마스크 생성
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        # 각 색상의 픽셀 수 계산
        counts = {
            "RED": cv2.countNonZero(mask_red),
            "YELLOW": cv2.countNonZero(mask_yellow),
            "GREEN": cv2.countNonZero(mask_green)
        }

        # 가장 많은 픽셀을 가진 색상 찾기
        max_color = max(counts, key=counts.get)
        max_count = counts[max_color]

        # 최소 픽셀 개수 임계값 (노이즈 제거)
        pixel_threshold = 50  # 이 값은 실제 환경에 맞게 조정이 필요할 수 있습니다.
        if max_count > pixel_threshold:
            return max_color
        else:
            return "UNKNOWN"


    def _getTrafficLightColor(self):
        return self.__yoloTrafficLightColor


    def _isObjDetected(self, name: str) -> bool:
        """
        특정 이름의 클래스가 감지되었는지 확인합니다.

        Args:
            name (str): 확인할 클래스의 이름 (예: "person", "car")

        Returns:
            bool: 해당 클래스가 감지되었으면 True, 아니면 False
        """
        name = KOREAN_TO_ENGLISH_OBJ_MAP.get(name, name)

        for detection in self.__yoloDetections:
            if detection["name"] == name:
                return True
        return False

    def _getObjSize(self, name: str) -> int:
        """
        특정 이름의 클래스의 크기(면적)를 반환합니다.
        동일한 클래스가 여러 개 감지된 경우, 첫 번째 객체의 크기를 반환합니다.

        Args:
            name (str): 크기를 조회할 클래스의 이름

        Returns:
            int: 객체의 크기(면적). 객체가 없으면 0을 반환합니다.
        """
        name = KOREAN_TO_ENGLISH_OBJ_MAP.get(name, name)

        for detection in self.__yoloDetections:
            if detection["name"] == name:
                return detection["size"]
        return 0

    def _getObjCenter(self, name: str) -> tuple:
        """
        특정 이름의 클래스의 중심 좌표 (x, y)를 반환합니다.
        동일한 클래스가 여러 개 감지된 경우, 첫 번째 객체의 좌표를 반환합니다.

        Args:
            name (str): 중심 좌표를 조회할 클래스의 이름

        Returns:
            tuple: 객체의 중심 좌표 (x, y). 객체가 없으면 빈 튜플 ()을 반환합니다.
        """

        name = KOREAN_TO_ENGLISH_OBJ_MAP.get(name, name)

        for detection in self.__yoloDetections:
            if detection["name"] == name:
                return detection["center"]
        return ()

    def _getObjConfidence(self, name: str) -> float:
        """
        특정 이름의 클래스의 신뢰도(confidence)를 반환합니다.
        동일한 클래스가 여러 개 감지된 경우, 첫 번째 객체의 신뢰도를 반환합니다.

        Args:
            name (str): 신뢰도를 조회할 클래스의 이름

        Returns:
            float: 객체의 신뢰도. 객체가 없으면 0.0을 반환합니다.
        """

        name = KOREAN_TO_ENGLISH_OBJ_MAP.get(name, name)

        for detection in self.__yoloDetections:
            if detection["name"] == name:
                return detection["confidence"]
        return 0.0


    # 감지 대상에 객체 추가
    def _yoloCheckAddObj(self, obj_name=""):
        if not self.__yoloModel:
            print("❌ 모델이 로드되지 않았습니다. 객체를 추가할 수 없습니다.")
            return

        obj_name = KOREAN_TO_ENGLISH_OBJ_MAP.get(obj_name, obj_name)

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

        obj_name = KOREAN_TO_ENGLISH_OBJ_MAP.get(obj_name, obj_name)

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





    # --- scketch ---
    def _sketchDetectorInit(self):
        from .sketch_recognizer import SketchProcessor
        if self.__sketchDetectInitFlag is False:
            self.__sketchRecognizer = SketchProcessor()
            self.__sketchDetectInitFlag = True

        print("Sketch detector initialized")

    def _sketchDetectorStart(self):
        if self.__sketchDetectInitFlag is False:
            print("Sketch detector is not initialized")
            return

        if self.__sketchDetectFlag == True:
            print("Sketch detector is already working.")
            return
        self.__sketchDetectFlag = True

        th = threading.Thread(target=self.__sketchdetect)
        th.deamon = True
        th.start()

    def _sketchDetectorStop(self):
        if self.__sketchDetectFlag == False :
            print("Sketch detector is already stopped.")
            return

        self.__sketchDetectFlag = False
        time.sleep(1)

        print("Sketch detector off")

    def __sketchdetect(self):
        while self.__sketchDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                # print('no input frame yet')
                continue
            try:
                self.__sketchRecognizedList, self.__sketchDetectedList, self.__sketchConfidenceList = self.__sketchRecognizer(self.__raw_img)

                self.__sketchDataDict.clear()
                for i in range(0, len(self.__sketchDetectedList)):
                    self.__sketchDataDict[self.__sketchRecognizedList[i]] = SketchData( self.__sketchRecognizedList[i], self.__sketchDetectedList[i], self.__sketchConfidenceList[i])

            except Exception as e:
                print("Sketch detector error : " , e)
                continue

            time.sleep(0.01)

    def __overlay_sketch_boxes(self, frame):

        for sketchKey, sketchData in self.__sketchDataDict.items():

            color = (255, 0, 255) # 기본 보라색
            if self.__drawSketchAreaFlag:
                cv2.polylines(frame, np.array([sketchData.box], np.int32), True, color, 3)

            y_offset = 0

            #s0 = str(sketchData.name) + " " + str(sketchData.confidence)
            s0 = f"{sketchData.name} {sketchData.confidence:.2f}"


            #s1 = 'x=' + str(sketchData.centerX) +' y='+str(sketchData.centerY)

            convertPos = self.convert_center_pos(sketchData.centerX, sketchData.centerY)
            s1 = 'x=' + str(convertPos[0]) +' y='+str(convertPos[1])
            s2 = 'size=' + str(sketchData.size)

            color = (255, 0, 255) # 기본 보라색
            if self.__drawSketchNameFlag:
                # cv2.putText(frame, s, (int(sketchData.textX), int(sketchData.textY+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                # # cv2.putText(frame, s, (int(sketchData.box[1][0]), int(sketchData.box[1][1]+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                # addedY += 20
                self._drawPutTextBox(frame, s0, int(sketchData.box[1][0]), int(sketchData.box[1][1]), y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 15, 255) # 다음 색상 지정

            if self.__drawSketchPointFlag == True:

                self._drawPutTextBox(frame, s1, int(sketchData.box[1][0]), int(sketchData.box[1][1]), y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 30, 255) # 다음 색상 지정

            if self.__drawSketchSizeFlag == True:
                self._drawPutTextBox(frame, s2, int(sketchData.box[1][0]), int(sketchData.box[1][1]), y_offset,color)
                y_offset = y_offset + self.__text_offset  # 다음 위치 지정
                color = (255, 45, 255) # 다음 색상 지정



    def _sketchTrain(self, name:str):
        if self.__sketchDetectFlag == False:
            print("먼저 스케치 인식 기능을 시작해주세요. 취소합니다.")
            return
        if name == "":
            print("이름을 입력해주세요. 취소합니다.")
            return

        if self.__sketchTrainFlag == False:
            self.__sketchTrainFlag = True
            self.__sketchTrainName = name
            print("스케치 학습 모드를 시작합니다.")

    def _deleteSketchData(self, name:str):
        if self.__sketchDetectFlag == False:
            print("먼저 스케치 인식 기능을 시작해주세요. 취소합니다.")
            return
        if name == "":
            print("이름을 입력해주세요. 취소합니다.")
            return
        self.__sketchRecognizer.delete_model_by_name(name)

    def _deleteAllSketchData(self):
        if self.__sketchDetectFlag == False:
            print("먼저 스케치 인식 기능을 시작해주세요. 취소합니다.")
            return
        self.__sketchRecognizer.clear_all_models()


    def _isSketchDetected(self,name:str="Sketch") ->bool:
        return name in self.__sketchDataDict

    def _getSketchCenter(self, name:str) -> list:
        if name in self.__sketchDataDict:
            #return [self.__sketchDataDict[name].centerX,self.__sketchDataDict[name].centerY]
            convertPos = self.convert_center_pos(self.__sketchDataDict[name].centerX, self.__sketchDataDict[name].centerY)

            return convertPos

        pass

    def _getSketchSize(self, name:str):
        if name in self.__sketchDataDict:
            return self.__sketchDataDict[name].size
        pass

    def _getSketchResult(self, name:str):
        if name in self.__sketchDataDict:
            return self.__sketchDataDict[name].name, self.__sketchDataDict[name].confidence
        else:
            return None, None # 또는 원하는 다른 기본값 (예: None)

    def _getSketchConfidence(self, name:str):
        if name in self.__sketchDataDict:
            return self.__sketchDataDict[name].confidence
        pass

    def _getSketchName(self, name:str):
        if name in self.__sketchDataDict:
            return self.__sketchDataDict[name].name
        pass

    # teachable machine
    def _teachableInit(self, ModelPath = 'model_unquant.tflite', LabelPath = 'labels.txt'):
        import tensorflow as tf

        if self.__teachableInitFlag is False:
            self.__teachableInitFlag = True
            self.teachableModelPath = ModelPath
            self.teachableLabelPath = LabelPath
            print(self.teachableModelPath)
            print(self.teachableLabelPath)

    def _teachableStart(self):
        if self.__teachableInitFlag is False:
            print("Facedetector is not initialized")
            return

        if self.__teachableDetectFlag == True:
            print("Facedetector is already working.")
            return
        self.__teachableDetectFlag = True

        # --- 2. 모델 및 레이블 로드 ---
        print(f"TensorFlow Lite 모델 로딩 중: {self.teachableModelPath}")
        try:
            # TFLite 인터프리터 로드
            self.__teachableInterpreter = tf.lite.Interpreter(model_path=self.teachableModelPath)
            self.__teachableInterpreter.allocate_tensors() # 텐서 할당

            # 입력 및 출력 텐서 가져오기
            self.__teachableInputDetails = self.__teachableInterpreter.get_input_details()
            self.__teachableOutputDetails = self.__teachableInterpreter.get_output_details()

            print("TensorFlow Lite 모델 로드 완료.")
        except Exception as e:
            print(f"TensorFlow Lite 모델 로드 중 오류 발생: {e}")
            return

        print(f"레이블 로딩 중: {self.teachableLabelPath}")

        try:
            with open(self.teachableLabelPath, 'r', encoding='utf-8') as f:
                self.__teachableLabels = [line.strip() for line in f.readlines()]
            print("레이블 로드 완료.")
            print(f"로딩된 레이블: {self.__teachableLabels}")
        except Exception as e:
            print(f"레이블 로드 중 오류 발생: {e}")
            return

        th = threading.Thread(target=self.__teachable)
        th.deamon = True
        th.start()

    def _teachableStop(self):
        if self.__teachableInitFlag == False :
            print("Teachable detector is already stopped.")
            return

        self.__teachableInitFlag = False
        time.sleep(1)
        print("Teachable detector off")

    def __teachable(self):
        while self.__teachableDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                print('no input frame yet')
                continue
            try:
                IMAGE_WIDTH = 224
                IMAGE_HEIGHT = 224
                img_np = np.array(self.__raw_img)
                img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)

                # 이미지 전처리: 크기 조정 및 정규화
                img_resized = cv2.resize(img_rgb, (IMAGE_WIDTH, IMAGE_HEIGHT))
                normalized_image_array = (img_resized.astype(np.float32) / 255.0)

                # TFLite 모델 입력 형태에 맞추기: (1, HEIGHT, WIDTH, 3)
                input_data = np.expand_dims(normalized_image_array, axis=0)

                # --- 4. 모델 추론 (TFLite) ---
                self.__teachableInterpreter.set_tensor(self.__teachableInputDetails[0]['index'], input_data)
                self.__teachableInterpreter.invoke() # 추론 실행

                # 결과 가져오기
                output_data = self.__teachableInterpreter.get_tensor(self.__teachableOutputDetails[0]['index'])

                prediction = output_data[0] # 배치 차원 제거
                index = np.argmax(prediction)
                self.teachableClassName = self.__teachableLabels[index]
                self.teachableConfidenceScore = prediction[index]

                # --- 5. 결과 출력 ---
                #print(f"클래스: {self.teachableClassName[2:]}, 확률: {self.teachableConfidenceScore:.2f}")

            except Exception as e:
                print("Detect : " , e)
                continue

            time.sleep(0.001)

    def __overlay_teachable(self, frame):
        if self.teachableClassName != None or self.teachableConfidenceScore != None:
            #print(f"클래스: {self.teachableClassName[2:]}, 확률: {self.teachableConfidenceScore:.2f}")
            s0 = f"{self.teachableClassName[2:]} {self.teachableConfidenceScore:.2f}"

            self._drawPutTextBox(frame, s0, 125, frame.shape[0]-25, 0, (255, 100, 100))


    def _getTeachableResult(self):
        """
        Teachable Machine 모델의 예측 결과 (클래스 이름과 신뢰도 점수)를 반환합니다.

        Returns:
            tuple: (클래스 이름: str, 신뢰도 점수: float)
        """
        if self.teachableClassName == None or self.teachableConfidenceScore == None:
            # 이전에 run_inference()가 호출되지 않았거나 결과가 없을 경우
            print("경고: 아직 모델 추론이 실행되지 않았거나 결과가 없습니다. teachable_detector_init()를 먼저 실행하세요.")
            return None, None

        # 클래스 이름은 인덱스 2부터 반환 (인덱스 번호 제거)
        processed_class_name = self.teachableClassName[2:]
        # 신뢰도 점수는 소수점 두 자리까지 포맷팅 (float 형태로 유지)
        processed_confidence_score = round(self.teachableConfidenceScore, 2)

        return processed_class_name, processed_confidence_score


    # --- sensor ---
    def _sensorStart(self):
        if self.__sensorInitFlag is False:
            self._ws.send("sensor") # start

            self.__sensorInitFlag = True
            self.__drawSensorAreaFlag = True
            self.__sensorFlag = True
        print("Sensor initialized")

    def _sensorVisible(self, flag):
        if flag == True:
            if self.__drawSensorAreaFlag == True:
                print("Sensor visible is already working.")
                return
            self.__drawSensorAreaFlag = True

        else:
            if self.__drawSensorAreaFlag == False:
                print("Sensor visible is already stopped.")
                return
            self.__drawSensorAreaFlag = False


    def _frameRateVisible(self, flag):
        if flag == True:
            if self.__drawFPSFlag == True:
                print("FPS visible is already working.")
                return
            self.__drawFPSFlag = True

        else:
            if self.__drawFPSFlag == False:
                print("FPS visible is already stopped.")
                return
            self.__drawFPSFlag = False

    def _process_sensor_packet(self, data):
        """센서 데이터 처리"""
        if data[:2] != self.SENSOR_HEADER:
            self._debugger._printLog(f"Invalid sensor header: {data[:2].hex()}")
            return

        bat_offset = 0
        if data[8] > 100 :
            bat_offset = 3

        self.sensor_values = {
            'FL': data[3],
            'FR': data[2],
            'BL': data[5],
            'BC': data[6],
            'BR': data[4],
            'BTN': data[7],
            'BAT': data[8] - bat_offset,
            'STAT': data[9]
        }

        try:
            self._sensor_queue.put_nowait(self.sensor_values)
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

        if sensors:
            y = 20
            for key, value in sensors.items():
                if key != 'STAT' and key != 'BAT' and key != 'BTN':
                    text = f"{key}: {value}"
                    #self._drawPutTextBox(frame, text, 10, y, 0,(0, 255, 255))
                    cv2.putText(frame, text, (5, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, lineType=cv2.LINE_AA)
                    y += 18


    def _get_PSTAT_data(self):
        if self.__sensorFlag == True:
            return (self.sensor_values['STAT']) # Return a PSTAT flag
        else :
            print("sensor_start 를 먼저 실행해주세요.")
            return (0) # Return a PSTAT flag

    def _get_ir_all_readings(self):
        """Returns the latest IR sensor readings (FL, FR, BL, BC, BR)."""
        if self.__sensorFlag == True:
            return (self.sensor_values['FL'], self.sensor_values['FR'], self.sensor_values['BL'], self.sensor_values['BC'], self.sensor_values['BR']) # Return a tuple copy
        else :
            print("sensor_start 를 먼저 실행해주세요.")
            return (0, 0, 0, 0, 0) # Return a tuple copy

    def _get_btn_data(self):
        if self.__sensorFlag == True:
            return self.sensor_values['BTN']
        else :
            print("sensor_start 를 먼저 실행해주세요.")
            return (0)

    def _get_battery_data(self):
        if self.__sensorFlag == True:
            return self.sensor_values['BAT']
        else :
            print("sensor_start 를 먼저 실행해주세요.")
            return (0)


    # 프레임 표시
    def _FPS_overlay(self, frame):
        # FPS 표시 (기존 코드 유지)
        elapsed = time.time() - self._start_time
        fps = self._frame_count / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, frame.shape[0]-10),
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


    # --- vision ---

    def _cameraLeftRightFlip(self, flag:bool):
        self.__flipLRFlag = flag

    def _getCameraFrame(self):
        return self.__raw_img

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


        #-------------------------------------------------------------------------
        # MODEL_PATH = 'model_unquant.tflite' # Teachable Machine에서 내보낸 .tflite 파일 이름
        # LABELS_PATH = 'labels.txt'
        # IMAGE_WIDTH = 224
        # IMAGE_HEIGHT = 224

        # # --- 2. 모델 및 레이블 로드 ---
        # print(f"TensorFlow Lite 모델 로딩 중: {MODEL_PATH}")
        # try:
        #     # TFLite 인터프리터 로드
        #     interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
        #     interpreter.allocate_tensors() # 텐서 할당

        #     # 입력 및 출력 텐서 가져오기
        #     input_details = interpreter.get_input_details()
        #     output_details = interpreter.get_output_details()

        #     print("TensorFlow Lite 모델 로드 완료.")
        # except Exception as e:
        #     print(f"TensorFlow Lite 모델 로드 중 오류 발생: {e}")
        #     exit()

        # print(f"레이블 로딩 중: {LABELS_PATH}")
        # try:
        #     with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        #         labels = [line.strip() for line in f.readlines()]
        #     print("레이블 로드 완료.")
        #     print(f"로딩된 레이블: {labels}")
        # except Exception as e:
        #     print(f"레이블 로드 중 오류 발생: {e}")
        #     exit()
        #-------------------------------------------------------------------------

        #self._teachableInit()
        #self._teachableStart()

        #while self._connected:
        while self.__cameraStreamFlag:
            try:
                frame = self._frame_queue.get(timeout=2.0)
                self.__raw_img = frame.copy()

                # 얼굴 인식 화면 오버레이
                if self.__faceDetectFlag == True:
                    self.__overlay_face_boxes(frame)

                # 제스처 인식 화면 오버레이
                if self.__gestureDetectFlag == True:
                    if self.__drawGestureAreaFlag == True:
                        self.__overlay_gesture_boxes(frame)

                # yolo 인식 화면 오버레이
                if self.__yoloDetectFlag == True:
                    if self.__drawYoloAreaFlag == True:
                        self.__overlay_yolo_boxes(frame)

                # apriltag 인식 화면 오버레이
                if self.__aprilDetectFlag == True:
                    if self.__drawAprilAreaFlag == True:
                        self.__overlay_april_boxes(frame)

                # 센서 값 화면 오버레이
                if self.__sensorFlag == True:
                    sensors = self._get_latest_sensors()
                    if self.__drawSensorAreaFlag == True:
                        self._sensor_overlay(frame, sensors)

                # 센서 값 화면 오버레이
                if self.__drawFPSFlag == True:
                    self._FPS_overlay(frame)

                # 스케치 인식 화면 오버레이
                if self.__sketchDetectFlag == True:
                    if self.__drawSketchAreaFlag == True:
                        self.__overlay_sketch_boxes(frame)

                # teachable machine
                if self.__teachableInitFlag == True:
                    if self.__drawTeachablAreaFlag == True:
                        self.__overlay_teachable(frame)

                # # 숫자 인식 화면 오버레이
                # if self.__numberDetectFlag == True:
                #     if self.__drawNumberAreaFlag == True:
                #         self.__overlay_number_boxes(frame)

                # if self.__signDetectFlag == True:
                #    for (x, y, w, h) in self.__signDetectedRegions:
                #        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2) # 초록색 사각형

                if self.__faceTrainFlag == True or self.__sketchTrainFlag == True:
                    #r키를 눌러 연속 캡쳐, e키를 눌러 종료
                    self._drawPutTextBox(frame, "-press r : capture", 0, 202, 0,(50,50,250))
                    self._drawPutTextBox(frame, "-press e : end", 0, 220, 0,(50,50,250))

                cv2.imshow("ZumiAI Stream", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.__faceDetectFlag = False
                    self.__aprilDetectFlag = False
                    self.__sketchDetectFlag = False
                    self.__gestureDetectFlag = False
                    self.__teachableDetectFlag = False
                    break

                elif key == ord('s') and frame is not None:
                    # 's' 키를 누르면 현재 프레임 저장 (frame)
                    cv2.imwrite(f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg", frame)
                    print("img save")

                elif key == ord('d') and frame is not None:
                    # 's' 키를 누르면 현재 프레임 저장 (self.__raw_img)
                    cv2.imwrite(f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg", self.__raw_img)
                    print("img save")


                # 스케치 학습 모드
                if self.__sketchTrainFlag == True:
                    if key == ord('r'):
                        add_result = self.__sketchRecognizer.add_sketch_for_training(self.__raw_img, self.__sketchTrainName)
                        if add_result != 0:
                            print(f"스케치 추가 실패.")

                    elif key == ord('e'):
                        self.__sketchTrainFlag = False
                        self.__sketchRecognizer.train_from_captured_data()
                        print("---------------------------------------------------------")

                # 얼굴 학습 모드
                if self.__faceTrainFlag == True:
                    if key == ord('r'): # 'r' 키를 누르면 현재 얼굴 학습
                        if self.__facecurrentResults == True and self.__faceResults != None:
                            self.__face_recognizer.TrainModel(frame, self.__current_face_bbox, self.__faceTrainName)
                        else:
                            print("얼굴이 감지되지 않아 등록할 수 없습니다.")

                    elif key == ord('e'): # 'e' 키를 눌러 학습 모드 종료
                        if self.__faceTrainFlag == True:
                            self.__faceTrainFlag = False
                            if self.__faceTrainName is not None:
                                if self.__faceTrainName in self.__face_recognizer.registerd:
                                    print(f"'{self.__faceTrainName}' 학습 모드를 종료합니다. 등록된 얼굴 수: {self.__face_recognizer.registerd[self.__faceTrainName].extra.shape[0]}개.")
                                else:
                                    print(f"'{self.__faceTrainName}' 학습 모드를 종료합니다. 등록된 얼굴이 없습니다.")
                                self.__faceTrainName = None
                                self.__face_recognizer._save_registered_faces() # 학습 모드 종료 시 데이터 저장
                                print("---------------------------------------------------------")

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
