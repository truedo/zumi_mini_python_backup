import sys
import serial
import time
import queue
from queue import Queue
from time import sleep
import threading
from threading import Thread
from colorama import Fore, Back, Style
from serial.tools.list_ports import comports
from pynput import keyboard


#websocket
import cv2
import numpy as np
import websocket
import argparse
import time
import threading
import queue

import logging



#from protocol import * # make html 사용시 적용
#from receiver import * # make html 사용시 적용

from .protocol import *
from .receiver import *


from .face_detector import FaceDetector
from .face_landmark import FaceLandmark
from .face_recognizer import FaceRecognizer
from .number_recognizer import NumberRecognizer
from .sketch_recognizer import SketchRecognizer

import mediapipe as mp

import pkg_resources
import copy
import os
from pupil_apriltags import Detector

def convertByteArrayToString(dataArray):
    """
    바이트를 스트링으로 변환 합니다.
    """
    if dataArray == None:
        return ""

    string = ""

    if (isinstance(dataArray, bytes)) or (isinstance(dataArray, bytearray)) or (not isinstance(dataArray, list)):
        for data in dataArray:
            string += "{0:02X} ".format(data)

    return string


class FaceData:
    def __init__(self):
        self.name = ''
        self.box = []
        self.landMarks = None
        self.centerX = 0
        self.centerY = 0
        self.size = 0

    def SetData(self, name:str, box, landmarks):
        self.name = name
        self.box = box
        self.landMarks = landmarks
        self.centerX = int((box[0] + box[2]) / 2)
        self.centerY = int((box[1] + box[3]) / 2)
        self.size = self.landMarks[16][0] - self.landMarks[0][0]

class SketchData:
    def __init__(self, name:str, box:list):
        self.name = name
        self.box = box
        self.centerX = int((self.box[0][0] + self.box[2][0]) / 2)
        self.centerY = int((self.box[0][1] + self.box[2][1]) / 2)
        self.size = abs(int(self.box[2][0] - self.box[0][0]))
        self.textX = 0
        self.textY = 20000
        for i in range(4):
            if self.textX < self.box[i][0]:
                self.textX = self.box[i][0]
            if self.textY > self.box[i][1]:
                self.textY = self.box[i][1]

class DebugOutput:
    def __init__(self, show_log=True, show_error=True, show_transfer=False, show_receive=False):
        # 프로그램 시작 시간 저장 (인스턴스 생성 시점)
        self._time_start_program = time.time()

        # 출력 제어 플래그
        self._usePos_show_log_message = show_log
        self._usePos_show_error_message = show_error
        self._usePos_show_transfer_data = show_transfer
        self._usePos_show_receive_data = show_receive

        # 수신 데이터 출력이 부분적으로 이루어질 수 있으므로,
        # 마지막에 줄바꿈이 필요할 경우를 대비한 상태 플래그 (선택 사항)
        self._receiving_line_in_progress = False


    def _printLog(self, message):
        # 일반 로그 출력
        if self._usePos_show_log_message and message is not None:
            elapsed_time = time.time() - self._time_start_program
            print(Fore.GREEN + "[{0:10.03f}] {1}".format(elapsed_time, message) + Style.RESET_ALL)
            self._ensure_newline_after_receive() # 수신 데이터 출력 중이었으면 줄바꿈

    def _printError(self, message):
        # 에러 메시지 출력
        if self._usePos_show_error_message and message is not None:
            elapsed_time = time.time() - self._time_start_program
            print(Fore.RED + "[{0:10.03f}] {1}".format(elapsed_time, message) + Style.RESET_ALL)
            self._ensure_newline_after_receive() # 수신 데이터 출력 중이었으면 줄바꿈

    def _printTransferData(self, data_array):
        # 송신 데이터 출력
        if self._usePos_show_transfer_data and (data_array is not None) and (len(data_array) > 0):
            print(Back.YELLOW + Fore.BLACK + convertByteArrayToString(data_array) + Style.RESET_ALL)
            self._ensure_newline_after_receive() # 수신 데이터 출력 중이었으면 줄바꿈


    def _printReceiveData(self, data_array):
        # 수신 데이터 출력 (줄바꿈 없이 이어붙임)
        if self._usePos_show_receive_data and (data_array is not None) and (len(data_array) > 0):
            print(Back.CYAN + Fore.BLACK + convertByteArrayToString(data_array) + Style.RESET_ALL, end='')
            self._receiving_line_in_progress = True # 수신 라인이 진행 중임을 표시

    def _printReceiveDataEnd(self):
        # 수신 데이터 출력 라인 종료
        if self._usePos_show_receive_data and self._receiving_line_in_progress:
            print("") # 줄바꿈 출력
            self._receiving_line_in_progress = False # 수신 라인 종료 표시

    def _ensure_newline_after_receive(self):
        # 다른 메시지 출력 전에 수신 라인이 끝나지 않았으면 강제 줄바꿈
        if self._receiving_line_in_progress:
            print("")
            self._receiving_line_in_progress = False

# try:
#     import websocket # websocket-client 라이브러리
#     import threading
#     import time
#     import queue
#     import cv2
#     import numpy as np
#     import ssl # WSS (WebSocket Secure) 사용 시 필요
#     WEBSOCKET_LIB_IS_AVAILABLE = True
# except ImportError:
#     WEBSOCKET_LIB_IS_AVAILABLE = False
#     print("Warning: 웹소켓을 위한 라이브러리가 없습니다.")


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
        self.url = url
        self._ws = None
        self._ws_thread = None
        self.connected = False # Indicates if the websocket is connected
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
        self.SENSOR_DATA_LENGTH = 7  # Header(2) + Data(5)

        # Config/Internal Flags
        self._usePosConnected = False # Kept for compatibility with serial handler's check
        self._usePosCheckBackground = usePosCheckBackground # Parameter kept for compatibility

        # Internal logging setup
        # self.logger = logging.getLogger(__name__)
        # if not self._debugger and not self.logger.handlers:
        #      # Configure basic logging if no debugger is provided and no handlers exist
        #      logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.start_time = time.time()
        self.last_frame_time = time.time()
        self.frame_queue = queue.Queue(maxsize=2)
        self.sensor_queue = queue.Queue(maxsize=20)
        self.frame_count = 0
        self.frames_dropped = 0

        self.__flipLRFlag = False



        # sensor
        self.__sensorInitFlag = False
        self.__sensorFlag = False
        self.__drawSensorAreaFlag = True



        self.__raw_img = None

        # face
        self.__faceDetectFlag = False
        self.__drawFaceAreaFlag = True
        self.__drawFaceNameFlag = True
        self.__drawFacePointFlag = True
        self.__drawFaceSizeFlag = True
        self.__drawLandmarkFlag = True

        self.__faceDetectInitFlag = False
        self.__faceDetectedList = []

        self.__faceLandmarkInitFlag = False
        self.__faceLandmarkList = []

        self.__faceRecognizeInitFlag = False
        self.__faceRecognizedList = []
        self.__faceDataDict = dict()


        # apriltag


        # april detector
        self.__aprilDetectFlag = False
        self.__aprilDetectInitFlag = False
        self.__drawAprilAreaFlag = True
        self.__drawAprilIdFlag = True
        self.__drawAprilPointFlag = True
        self.__drawAprilSizeFlag = True
        self.__drawAprilDistanceFlag = True
        self.__aprilDetectedCorners = []
        self.__aprilDetectedIds = []
        self.__aprilDataDict = dict()

        self.__tags =[]

        # number recognizer
        self.__numberDetectInitFlag = False
        self.__numberDetectFlag = False
        self.__drawNumberAreaFlag = True
        self.__drawNumberFlag = True
        self.__drawNumberPointFlag = True
        self.__drawNumberSizeFlag = True

        self.__numberRecognizedStr = ''
        self.__numberDetectedList = []


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


        # gesture detector
        self.__gestureDetectFlag = False
        self.__gestureDetectInitFlag = False
        self.__drawGestureAreaFlag = True
        self.__drawGestureIdFlag = True
        self.__drawGesturePointFlag = True
        self.__drawGestureSizeFlag = True
        self.__drawGestureDistanceFlag = True
        self.__gestureDetectedCorners = []
        self.__gestureDetectedIds = []
        self.__gestureDataDict = dict()

        self.__gestureLandmark = []



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
        self.connected = True
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
        self.connected = False # Connection is likely broken
        # _running might remain True until on_close is called, or until run_forever exits.


    def on_close(self, ws, close_status_code, close_msg):
        """Callback for when the WebSocket connection is closed."""
        self._debugger._printLog(f"WebSocket connection closed. Status: {close_status_code}, Message: {close_msg}")
        self.connected = False
        self._running = False # Signal that the handler should stop running
        self._usePosConnected = False # Indicate device is disconnected


    # --- face ---
    def FacedetectorInit(self):
        if self.__faceDetectInitFlag is False:
            self.__faceD = FaceDetector()
            self.__faceDetectInitFlag = True

        if self.__faceLandmarkInitFlag is False:
            self.__landD = FaceLandmark()
            self.__faceLandmarkInitFlag = True

        if self.__faceRecognizeInitFlag is False:
            self.__faceR = FaceRecognizer()
            self.__faceRecognizeInitFlag = True

        print("Facedetector initialized")


    def FacedetectorStart(self):

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

    def FacedetectorStop(self):
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
                self.__faceDetectedList = self.__faceD(self.__raw_img)
                self.__faceLandmarkList = self.__landD.batch_call (self.__raw_img, copy.deepcopy(self.__faceDetectedList))
                self.__faceRecognizedList = self.__faceR(self.__raw_img, copy.deepcopy(self.__faceDetectedList))

                self.__faceDataDict.clear()
                for i in range(0,len(self.__faceDetectedList)):
                    #print(self.__faceDetectedList)
                    #print(self.__faceLandmarkList)
                    #print(self.__faceRecognizedList)

                    faceData = FaceData()
                    faceData.SetData(self.__faceRecognizedList[i],
                                     list(self.__faceDetectedList[i]),
                                     self.__faceLandmarkList[i])
                    self.__faceDataDict[self.__faceRecognizedList[i]] = faceData

                #print(len(self.__faceDataDict))


            except Exception as e:
                print("Detect : " , e)
                continue

            time.sleep(0.001)

    def __overlay_face_boxes(self, frame):
        color =  (0, 255, 0)
        if self.__faceDetectedList is not None:

            for faceKey,faceData in self.__faceDataDict.items():
                addedY = 20
                if self.__drawFaceAreaFlag:
                    cv2.rectangle(frame, (int(faceData.box[0]), int(faceData.box[1])), (int(faceData.box[2]), int(faceData.box[3])), color, 3)

                if self.__drawFacePointFlag == True:
                    s = 'x=' + str(faceData.centerX) +' y='+str(faceData.centerY)
                    cv2.putText(frame, s, (int(faceData.box[0]),int(faceData.box[3]+addedY)), cv2.FONT_ITALIC,0.7, (0,255,0), 2)
                    addedY += 20

                if self.__drawFaceSizeFlag == True:
                    s = 'size=' + str(faceData.size)
                    cv2.putText(frame, s, (int(faceData.box[0]),int(faceData.box[3]+addedY)), cv2.FONT_ITALIC,0.7, (0,255,0), 2)
                    addedY += 20
                if self.__drawFaceNameFlag == True:
                    s = 'name=' + str(faceData.name)
                    cv2.putText(frame, s, (int(faceData.box[0]),int(faceData.box[3]+addedY)), cv2.FONT_ITALIC,0.7, (0,255,0), 2)
                    addedY += 20
                if self.__drawLandmarkFlag == True:
                    for faces in faceData.landMarks:
                        cv2.circle(frame, (int(faces[0]),int(faces[1])), 3, (255,0,255), -1)

                # pointIdx = 0
                    # if pointIdx != 0 and pointIdx != 17 and pointIdx != 22 and pointIdx != 27 and pointIdx != 36 and pointIdx != 42 and pointIdx != 48 and pointIdx != 60:
                    #     cv2.line(frame, (self.__faceLandmarkList[faceIdx][pointIdx][0], self.__faceLandmarkList[faceIdx][pointIdx][1]), (self.__faceLandmarkList[faceIdx][pointIdx-1][0], self.__faceLandmarkList[faceIdx][pointIdx-1][1]), (255,255,0), 1)
                    # pointIdx += 1
                # cv2.line(frame, (self.__faceLandmarkList[faceIdx][41][0], self.__faceLandmarkList[faceIdx][41][1]), (self.__faceLandmarkList[faceIdx][36][0], self.__faceLandmarkList[faceIdx][36][1]), (255,255,0), 1)
                # cv2.line(frame, (self.__faceLandmarkList[faceIdx][47][0], self.__faceLandmarkList[faceIdx][47][1]), (self.__faceLandmarkList[faceIdx][42][0], self.__faceLandmarkList[faceIdx][42][1]), (255,255,0), 1)
                # cv2.line(frame, (self.__faceLandmarkList[faceIdx][59][0], self.__faceLandmarkList[faceIdx][59][1]), (self.__faceLandmarkList[faceIdx][48][0], self.__faceLandmarkList[faceIdx][48][1]), (255,255,0), 1)
                # cv2.line(frame, (self.__faceLandmarkList[faceIdx][67][0], self.__faceLandmarkList[faceIdx][67][1]), (self.__faceLandmarkList[faceIdx][60][0], self.__faceLandmarkList[faceIdx][60][1]), (255,255,0), 1)
        #else:
        #    print('__faceDataDict none')



    def FaceCapture(self, name:str, captureCount:int=5, path:str=pkg_resources.resource_filename(__package__,"res/face/")):
        if bool(name) == False:
            print("Name parameter is Empty.")
            return

        if os.path.isdir(path) is False:
            os.mkdir(path)

        if self.__faceDetectFlag is False:
            print("Facedetector did not run")
            return

        cnt = 0
        while cnt < captureCount:
            if len(self.__faceDataDict) == 0:
                print("Doesn't have a any face in Frame")
                continue

            bbox = (0, copy.deepcopy(self.__faceDetectedList.copy())[0])

            result = self.__faceR.SaveFace(self.__raw_img,bbox,name)
            if result == 0:
                cnt += 1
                time.sleep(0.1)
        print( name, " is saved")

    def DeleteFaceData(self, name:str, facePath:str=pkg_resources.resource_filename(__package__,"res/face/")):
        if os.path.isdir(facePath) is False:
            print(facePath +" is not directory.")
            return

        self.__faceR.RemoveFace(name, facePath)

        print(name + ' is deleted')

    def DeleteAllFaceData(self, facePath:str=pkg_resources.resource_filename(__package__,"res/face/")):
        if os.path.isdir(facePath) is False:
            print(facePath +"is not directory.")
            return

        self.__faceR.RemoveAllFace(facePath)

        print('all face is deleted')


    def TrainFaceData(self, facePath:str =pkg_resources.resource_filename(__package__,"res/face/")):

        print(facePath)

        if os.path.isdir(facePath) is False:
            print(facePath +" is not directory.")
            return

        faceD = FaceDetector()
        self.__faceR.registerd.clear()

        filenames = os.listdir(facePath)
        for filename in filenames:
            name = os.path.basename(filename)
            image = cv2.imread(facePath + filename, cv2.IMREAD_ANYCOLOR)
            facedetectedList = faceD(image)

            if np.any(facedetectedList) == False:
                print("Doesn't have a any face in Frame")
                continue

            name = name.split('_')[0]
            #print(name)
            bbox = (0, facedetectedList[0])
            self.__faceR.TrainModel(image, bbox, name)



    def GetFaceCount(self) -> int:
        """
        카메라에 확인된 얼굴들의 이름을 list 형태로 반환하는 함수입니다.
        현재 인식된 얼굴이 없다면 빈 리스트를 반환합니다.
        """
        return len(self.__faceDataDict)

    def GetFaceExist(self, name:str="Human0") -> bool:
        """""
        카메라에 인식된 얼굴 중, name의 이름을 가진 얼굴이 있는지 반환하는 함수입니다.
        name : 검출할 얼굴의 이름입니다.
        """""

        return name in self.__faceDataDict

    def GetFaceNames(self) -> list:
        """""
        카메라에 확인된 얼굴들의 이름을 list 형태로 반환하는 함수입니다.
        현재 인식된 얼굴이 없다면 빈 리스트를 반환합니다.
        """""
        if len(self.__faceRecognizedList) == 0:
            return []

        return list(self.__faceRecognizedList)


    def GetFaceSize(self, name:str="Human0") -> int:

        """""
        카메라에 인식된 얼굴 중, name의 이름을 가진 얼굴의 크기를 반환하는 함수입니다.
        name : 크기를 구할 얼굴의 이름입니다.
        입력하지 않는다면, 학습되지 않은 얼굴의 사이즈를 반환합니다.
        """""
        if name in self.__faceDataDict:
            return self.__faceDataDict[name].size
        pass

    def GetFaceCenterPoint(self, name:str="Human0") -> list:
        """""
        카메라에 인식된 얼굴들 중 name의 이름을 가진 얼굴의 중심 좌표를 반환하는 함수입니다.
        name : 좌표를 구할 얼굴의 이름입니다.
        입력하지 않는다면, 학습되지 않은 얼굴의 사이즈를 반환합니다.
        """""

        if name in self.__faceDataDict:
            return [self.__faceDataDict[name].centerX,self.__faceDataDict[name].centerY]
        pass


    def GetFaceLandmarkPoint(self, landmark: face_landmark, name: str = "Human0") -> list:
        x = y = 0

        if name not in self.__faceDataDict:
            return [x, y]

        lm = self.__faceDataDict[name].landMarks

        if landmark == face_landmark.LEFT_EYE:
            x = (lm[36][0] + lm[39][0]) / 2
            y = (lm[36][1] + lm[39][1]) / 2
        elif landmark == face_landmark.RIGHT_EYE:
            x = (lm[42][0] + lm[45][0]) / 2
            y = (lm[42][1] + lm[45][1]) / 2
        elif landmark == face_landmark.LEFT_EYEBROW:
            x, y = lm[19]
        elif landmark == face_landmark.RIGHT_EYEBROW:
            x, y = lm[24]
        elif landmark == face_landmark.NOSE:
            x, y = lm[33]
        elif landmark == face_landmark.MOUTH:
            x = (lm[48][0] + lm[54][0]) / 2
            y = (lm[48][1] + lm[54][1]) / 2
        elif landmark == face_landmark.JAW:
            x, y = lm[8]
        else :
            print("else")


        return [x, y]

    # april
    def AprilDetectorInit(self):
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

    def AprilDetectorStart(self):
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

    def AprildetectorStop(self):
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
                self.__tags = self.__aprilD.detect(gray)
                #print(self.__tags)

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
        color = (0, 255, 0)

        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # # AprilTag 감지
        # tags = self.__aprilD.detect(gray)

        # 감지된 태그 정보 출력 및 시각화
        for tag in self.__tags:
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
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

            # 태그 ID 표시
            cv2.putText(frame, str(tag.tag_id), tuple(map(int, tag.center)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)


        # if self.__aprilDetectedIds is None:
        #     pass
        # else:
        #     idx = 0
        #     for corners in self.__aprilDetectedCorners:
        #         addedY = 0
        #         id = self.__aprilDetectedIds[idx]
        #         if id in duplicateId:
        #             color = self.__UnregisterdColor
        #         else:
        #             color =self.__RegisterdColor
        #             duplicateId.append(id)

        #         x = int((corners[0][0][0] + corners[0][2][0]) / 2)
        #         y = int((corners[0][0][1] + corners[0][2][1]) / 2)
        #         if self.__drawAprilAreaFlag == True:
        #             cv2.polylines(frame, np.array([corners[0]], np.int32), True, color, 3)
        #         if self.__drawAprilIdFlag == True:
        #             s = 'id='+str(id)
        #             cv2.putText(frame, s, (int(corners[0][3][0]),int(corners[0][3][1])+addedY), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
        #             addedY += 20
        #         if self.__drawAprilPointFlag == True:
        #             s = 'x=' + str(x) +' y='+str(y)
        #             cv2.putText(frame, s, (int(corners[0][3][0]),int(corners[0][3][1])+addedY), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
        #             addedY += 20
        #         if self.__drawAprilSizeFlag == True:
        #             april_perimeter = cv2.arcLength(corners[0], True) / 7
        #             s = 'size='+ str(int(april_perimeter))
        #             cv2.putText(frame, s, (int(corners[0][3][0]),int(corners[0][3][1])+addedY), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
        #             addedY += 20
        #         if self.__drawAprilDistanceFlag == True:
        #             s = 'distance={:.2f}'.format(self.__aprilDataDict[id].distance)
        #             cv2.putText(frame, s, (int(corners[0][3][0]),int(corners[0][3][1])+addedY), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
        #             addedY += 20
        #         idx+=1


    def GetAprilId(self) -> int:
        #print(self.__tags)
        if self.__tags is None or len(self.__tags) == 0:
            return -1
        else:
            return self.__tags[0].tag_id

    def GetAprilCenterPoint(self) -> list:
        if self.__tags is None or len(self.__tags) == 0:
            pass
        else:
            return self.__tags[0].center

    def GetAprilExist(self,id:int)->bool:
        if self.__tags is None or len(self.__tags) == 0:
            return False
        else:
            if self.__tags[0].tag_id == id:
                return True
            else :
                return False

    # --- numbers ---

    def NumberRecognizerInit(self):
        if self.__numberDetectInitFlag is False:
            self.__numberR = NumberRecognizer()
            self.__numberDetectInitFlag = True

        print("Number recognizer initialized")

    def GetRecognizedNumbers(self)->str:
        if self.__numberRecognizedStr:
            return self.__numberRecognizedStr

    def GetRecognizedNumberPoint(self)->list:
        if self.__numberDetectedList is not None and len(self.__numberDetectedList) > 0:
            x = int((self.__numberDetectedList[0][0][0] + self.__numberDetectedList[0][2][0]) / 2)
            y = int((self.__numberDetectedList[0][0][1] + self.__numberDetectedList[0][2][1]) / 2)
            return [x, y]
        pass

    def GetRecognizedNumberSize(self)->int:
        if self.__numberDetectedList is not None and len(self.__numberDetectedList) > 0:
            return abs(int(self.__numberDetectedList[0][2][0] - self.__numberDetectedList[0][0][0]))

    def NumberRecognizerStart(self):
        if self.__numberDetectInitFlag is False:
            print("Number recognizer is not initialized")
            return

        if self.__numberDetectFlag == True:
            print("Number recognizer is already working.")
            return
        self.__numberDetectFlag = True

        th = threading.Thread(target=self.__numberdetect)
        th.deamon = True
        th.start()

    def NumberRecognizerStop(self):
        if self.__numberDetectFlag == False :
            print("Number recognizer is already stopped.")
            return

        self.__numberDetectFlag = False
        time.sleep(1)

        print("Number recognizer off")


    def __numberdetect(self):
        while self.__numberDetectFlag:
            if self.__raw_img is None:
                time.sleep(0.1)
                # print('no input frame yet')
                continue
            try:
                self.__numberRecognizedStr,self.__numberDetectedList = self.__numberR(self.__raw_img)
            except Exception as e:
                # print("Number recognizer error : " , e)
                continue

            time.sleep(0.05)


    def __overlay_number_boxes(self, frame):
        color = (0, 255, 0)

        # print(self.__numberDetectedList)
        # print(" ")
        for detected in self.__numberDetectedList:
            addedY = 0
            x = int((detected[0][0] + detected[2][0]) / 2)
            y = int((detected[0][1] + detected[2][1]) / 2)
            _x = int((self.__numberDetectedList[0][0][0] + self.__numberDetectedList[0][2][0]) / 2)
            _y = int((self.__numberDetectedList[0][0][1] + self.__numberDetectedList[0][2][1]) / 2)

            if self.__drawNumberAreaFlag == True:
                cv2.polylines(frame, np.array([detected], np.int32), True, color, 3)
            if self.__drawNumberFlag == True:
                s = 'number='+str(self.__numberRecognizedStr)
                cv2.putText(frame, s, (_x, _y+addedY), cv2.FONT_ITALIC,0.5, (0,255,0), 1)
                addedY += 20
            if self.__drawNumberPointFlag == True:
                s = 'x=' + str(x) +' y='+str(y)
                cv2.putText(frame, s, (_x, _y+addedY), cv2.FONT_ITALIC,0.5, (0,255,0), 1)
                addedY += 20
            if self.__drawNumberSizeFlag == True:
                s = 'size=' + str( abs ( int ( detected[2][0] - detected[0][0])))
                cv2.putText(frame, s, (_x, _y+addedY), cv2.FONT_ITALIC,0.5, (0,255,0), 1)
                addedY += 20


    # --- scketch ---
    def SketchDetectorInit(self):
        if self.__sketchDetectInitFlag is False:
            self.__sketchR = SketchRecognizer()
            self.__sketchDetectInitFlag = True

        print("Sketch detector initialized")

    def SketchDetectorStart(self):
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


    def SketchDetectorStop(self):
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
                self.__sketchRecognizedList, self.__sketchDetectedList = self.__sketchR(self.__raw_img)
                self.__sketchDataDict.clear()
                for i in range(0, len(self.__sketchDetectedList)):
                    self.__sketchDataDict[self.__sketchRecognizedList[i]] = SketchData( self.__sketchRecognizedList[i], self.__sketchDetectedList[i])

                if len(self.__sketchRecognizedList) == 0:
                    time.sleep(0.0)
                    continue
            except Exception as e:
                # print("Sketch detector error : " , e)
                continue

            time.sleep(0.01)

    def __overlay_sketch_boxes(self, frame):
        color = (0, 255, 0)

        for sketchKey, sketchData in self.__sketchDataDict.items():
            addedY = 0
            if self.__drawSketchAreaFlag:
                cv2.polylines(frame, np.array([sketchData.box], np.int32), True, color, 3)
            if self.__drawSketchNameFlag:
                s = 'id='+str(sketchData.name)
                cv2.putText(frame, s, (int(sketchData.textX), int(sketchData.textY+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                # cv2.putText(frame, s, (int(sketchData.box[1][0]), int(sketchData.box[1][1]+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                addedY += 20
            if self.__drawSketchPointFlag == True:
                s = 'x=' + str(sketchData.centerX) +' y='+str(sketchData.centerY)
                cv2.putText(frame, s, (int(sketchData.textX), int(sketchData.textY+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                # cv2.putText(frame, s, (int(sketchData.box[1][0]), int(sketchData.box[1][1]+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                addedY += 20
            if self.__drawSketchSizeFlag == True:
                s = 'size=' + str(sketchData.size)
                cv2.putText(frame, s, (int(sketchData.textX), int(sketchData.textY+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                # cv2.putText(frame, s, (int(sketchData.box[1][0]), int(sketchData.box[1][1]+addedY)), cv2.FONT_HERSHEY_COMPLEX,0.8, (0,255,0), 1)
                addedY += 20

    def SketchCapture(self, name:str, captureCount:int=5, path:str=pkg_resources.resource_filename(__package__,"res/sketch/")):
        if bool(name) == False:
            print("Name parameter is Empty.")
            return

        if os.path.isdir(path) is False:
            os.mkdir(path)

        if self.__sketchDetectFlag is False:
            print("Sketchdetector did not run")
            return

        cnt = 0
        while cnt < captureCount:
            if len(self.__sketchRecognizedList) == 0:
                print("Doesn't have a any sketch in Frame")
                time.sleep(0.0)
                continue

            result = self.__sketchR.SaveSketch(self.__raw_img,name)
            if result == 0:
                cnt += 1
                time.sleep(0.1)
        print( name, " is saved")

    def TrainSketchData(self, sketchPath:str = pkg_resources.resource_filename(__package__,"res/sketch/")):
        if os.path.isdir(sketchPath) is False:
            print(sketchPath +" is not directory.")
            return

        orbDescriptors = []
        nameIndexList = []
        nameIntList = []

        sketchD = SketchRecognizer()
        filenames = os.listdir(sketchPath)
        for filename in filenames:
            name = os.path.basename(filename)
            image = cv2.imread(sketchPath+filename, cv2.IMREAD_GRAYSCALE)
            image = cv2.resize(image, (150,150))
            _, des = sketchD.orbDetector.detectAndCompute(image, None)
            name = name.split('_')[0]

            if not(name in nameIndexList):
                nameIndexList.append(name)
            nameIntList.append(nameIndexList.index(name))
            orbDescriptors.append(des)

        self.__sketchR.TrainModel(nameIndexList, nameIntList, orbDescriptors)

    def DeleteSketchData(self, name:str, sketchPath:str=pkg_resources.resource_filename(__package__,"res/sketch/")):

        if os.path.isdir(sketchPath) is False:
            print(sketchPath +" is not directory.")
            return

        self.__sketchR.RemoveSketch(name, sketchPath)

        print(name + ' is deleted')


    def GetSketchExist(self,name:str="Sketch") ->bool:
        return name in self.__sketchDataDict

    def GetSketchCenterPoint(self, name:str) -> list:
        if name in self.__sketchDataDict:
            return [self.__sketchDataDict[name].centerX,self.__sketchDataDict[name].centerY]
        pass



    # gesture

    def GestureDetectorInit(self):
        if self.__gestureDetectInitFlag is False:

            # Mediapipe 설정
            self.__mp_hands = mp.solutions.hands
            self.__hands = self.__mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.__mp_drawing = mp.solutions.drawing_utils

            self.__gestureDetectInitFlag = True
            self.__drawGestureAreaFlag = True
        print("Gesture detector initialized")

    def GestureDetectorStart(self):
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

    def GestureDetectorStop(self):
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

                if result.multi_hand_landmarks:
                    for self.__gestureLandmark in result.multi_hand_landmarks:
                        fingers_status = self.__get_finger_status(self.__gestureLandmark)
                        #print(self.__recognize_gesture(fingers_status))
                        #print(self.__gestureLandmark)
                        # 손 랜드마크와 연결선 그리기
                        #self.__mp_drawing.draw_landmarks(frame, self.__gestureLandmark, self.__mp_hands.HAND_CONNECTIONS)
                else:
                        self.__gestureLandmark = []
            except Exception as e:
                print("Gesture detector error : " , e)
                continue

            time.sleep(0.001)

    def __overlay_gesture_boxes(self, frame):
        self.__mp_drawing.draw_landmarks(frame, self.__gestureLandmark, self.__mp_hands.HAND_CONNECTIONS)


    def __get_finger_status(self,hand):
        """
        손가락이 펴져 있는지 접혀 있는지 확인하는 함수
        """
        # 오른손만 사용
        fingers = []

        # 엄지: 랜드마크 4가 랜드마크 2의 오른쪽에 있으면 펼쳐진 상태
        if hand.landmark[4].x < hand.landmark[3].x:
            fingers.append(1)
        else:
            fingers.append(0)

        # 나머지 손가락: 각 손가락의 팁 (8, 12, 16, 20)이 PIP (6, 10, 14, 18) 위에 있으면 펼쳐진 상태
        tips = [8, 12, 16, 20]
        pip_joints = [6, 10, 14, 18]
        for tip, pip in zip(tips, pip_joints):
            if hand.landmark[tip].y < hand.landmark[pip].y:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers


    def __recognize_gesture(self,fingers_status):
        if fingers_status == [0, 0, 0, 0, 0]:
            return 'fist'
        elif fingers_status == [0, 1, 0, 0, 0]:
            return 'point'
        elif fingers_status == [1, 1, 1, 1, 1]:
            return 'open'
        elif fingers_status == [0, 1, 1, 0, 0]:
            return 'peace'
        elif fingers_status == [1, 1, 0, 0, 0]:
            return 'standby'





    # --- sensor ---
    def sensorInit(self):
        if self.__sensorInitFlag is False:
            self._ws.send("sensor")

            self.__sensorInitFlag = True
            self.__drawSensorAreaFlag = True
        print("Sensor initialized")


    def sensorStart(self):
        if self.__sensorInitFlag is False:
            print("Sensor is not initialized")
            return

        if self.__sensorFlag == True:
            print("Sensor is already working.")
            return
        self.__sensorFlag = True


    def sensorStop(self):
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

        sensor_values = {
            'FR': data[2],
            'FL': data[3],
            'BR': data[4],
            'BL': data[5],
            'BC': data[6]
        }

        try:
            self.sensor_queue.put_nowait(sensor_values)
            #self.last_sensor_time = time.time()
        except queue.Full:
            self._debugger._printLog("Sensor queue overflow")


    def _get_latest_sensors(self):
        """최신 센서 값 가져오기"""
        latest = {}
        while not self.sensor_queue.empty():
            latest = self.sensor_queue.get_nowait()
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
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
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
            #     self.connected = False # Assume connection issue
            if self.connected and self._ws:
                try:
                    self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                    print("패킷 전송 성공:", data.hex(' '))
                except Exception as e:
                    print("패킷 전송 실패:", e)


    # --- vision ---

    def LeftRightFlipMode(self, flag:bool):
        self.__flipLRFlag = flag

    def ws_start_display(self):
        self._display_thread = threading.Thread(target=self._video_display)
        # 스레드를 데몬 스레드로 설정하면 메인 프로그램 종료 시 함께 종료됩니다. 필요에 따라 설정하세요.
        # self._display_thread.daemon = True
        # 스레드 시작
        self._display_thread.start()

    def _video_display(self):
        print("start_display")
        """영상 디스플레이 메인 루프"""
        self._ws.send("stream")

        mp_face_mesh = mp.solutions.face_mesh
        mp_drawing = mp.solutions.drawing_utils
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        while self.connected:
            try:
                frame = self.frame_queue.get(timeout=2.0)
                self.__raw_img = frame.copy()


                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # FaceMesh 모델로 얼굴 랜드마크 처리
                # results 객체에 감지된 얼굴 랜드마크 정보가 포함됩니다.
                results = face_mesh.process(rgb_frame)

                # 얼굴 랜드마크가 감지되었는지 확인
                if results.multi_face_landmarks:
                    # 감지된 각 얼굴에 대해 랜드마크 그리기
                    for face_landmarks in results.multi_face_landmarks:
                        # 랜드마크를 화면에 그립니다.
                        # mp_face_mesh.FACEMESH_TESSELATION: 얼굴의 삼각형 메시를 그림
                        # mp_face_mesh.FACEMESH_CONTOURS: 얼굴의 주요 윤곽선을 그림
                        # mp_face_mesh.FACEMESH_IRISES: 눈동자 윤곽선을 그림 (FaceMesh 버전 0.8.x 이상)

                        # 얼굴 메시의 삼각형 연결을 그립니다.
                        mp_drawing.draw_landmarks(
                            image=frame,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None, # 랜드마크 점은 그리지 않음
                            connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1) # 녹색 선
                        )
                        # 얼굴의 주요 윤곽선(눈, 코, 입 등)을 그립니다.
                        mp_drawing.draw_landmarks(
                            image=frame,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_CONTOURS,
                            landmark_drawing_spec=None, # 랜드마크 점은 그리지 않음
                            connection_drawing_spec=mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2) # 파란색 선
                        )

                        # //눈동자 윤곽선을 그립니다. (지원하는 경우)
                        # //mp_face_mesh.FACEMESH_IRISES는 MediaPipe 0.8.x 이상에서 사용 가능
                        # try:
                        #     mp_drawing.draw_landmarks(
                        #         image=frame,
                        #         landmark_list=face_landmarks,
                        #         connections=mp_face_mesh.FACEMESH_IRISES,
                        #         landmark_drawing_spec=None,
                        #         connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=1, circle_radius=1) # 빨간색 선
                        #     )
                        # except AttributeError:
                        #     pass # 해당 버전에서 FACEMESH_IRISES가 없을 경우 무시


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

                # 숫자 인식 화면 오버레이
                if self.__numberDetectFlag == True:
                    if self.__drawNumberAreaFlag == True:
                        self.__overlay_number_boxes(frame)

                # 스케치 인식 화면 오버레이
                if self.__sketchDetectFlag == True:
                    if self.__drawSketchAreaFlag == True:
                        self.__overlay_sketch_boxes(frame)

                # 제스처 인식 화면 오버레이
                if self.__gestureDetectFlag == True:
                    if self.__drawGestureAreaFlag == True:
                        self.__overlay_gesture_boxes(frame)


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


            except queue.Empty:
                if time.time() - self.last_frame_time > 5:
                    self._error("No frames received for 5 seconds")
                    print(time.ctime())
                    #self.connected = False
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
            self.frame_queue.put_nowait(frame)
            self.frame_count += 1
            self.last_frame_time = time.time()
        except queue.Full:
            self.frames_dropped += 1
            if self.frames_dropped % 30 == 0:
                self._error(f"Dropped frames: {self.frames_dropped}")

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
            self.url = url
        if not self.url:
            self._error("WebSocket URL is not set. Cannot connect.")
            return False

        #self._debugger._printLog("aa")

        self._debugger._printLog(f"Attempting to connect to WebSocket: {self.url}")
        self._running = True # Indicate that the handler is starting its process

        try:
            # Create WebSocketApp instance with callbacks
            self._ws = websocket.WebSocketApp(
                self.url,
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
            # The on_open callback will set self.connected = True asynchronously
            time.sleep(1) # Adjust sleep time as needed

            if self.isConnected():
                self._debugger._printLog("WebSocket connection initiated successfully.")
                # Note: self.connected is set True in on_open callback
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
            self.connected = False
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
        self.connected = False
        self._usePosConnected = False
        self._debugger._printLog("WebSocket connection closed.")


    def isOpen(self):
        """
        Checks if the underlying WebSocket object exists.
        Note: Use isConnected() to check if the connection is active.
        """
        # This method is more relevant for serial ports. For WebSocket,
        # self.connected is the main indicator of an active link.
        # Kept for compatibility, but self.connected is preferred.
        return self._ws is not None #and self.connected # prefer isConnected


    def isConnected(self):
        """
        Checks if the WebSocket connection is currently active.
        This relies on the internal `connected` flag updated by the callbacks.
        """
        # Both our internal running flag and the connected state should be true
        return self.connected and self._running

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
                self.connected = False # Assume connection issue


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


class SerialConnectionHandler(): # BaseConnectionHandler 상속
    def __init__(self,usePosCheckBackground, debugger=None):
        #self._portname = portname
        # self._baudrate = baudrate
        # self._timeout = timeout
        self._serialport = None
        self._bufferQueue = Queue(4096)
        self._bufferHandler = bytearray()


        self._usePosConnected = False  # Lets you know if you're connected to a device when you connect automatically

        self._debugger = debugger # DebugOutput 인스턴스

        self._receiver = Receiver()
        self._usePosCheckBackground = usePosCheckBackground

        self.headerLen = 2


        self.reqCOM = 0
        self.reqINFO = 0
        self.reqREQ = 0
        self.reqPSTAT = 0


        self.senFL = 0
        self.senFR = 0
        self.senBL = 0
        self.senBR = 0
        self.senBC = 0

        self.detectFace = [0, 0, 0]
        self.detectColor = [0, 0, 0]
        self.detectMarker = [0, 0, 0]
        self.detectCat = [0, 0, 0]

        self.btn = 0
        self.battery = 0

    def _handler(self, dataArray):

        # for i in range(0, 24):
        #     print("0x%02X" % dataArray[i])
        # self.senFL = dataArray[4]
        # self.senFR = dataArray[3]
        # self.senBL = dataArray[7]
        # self.senBC = dataArray[6]
        # self.senBR = dataArray[5]

        # self.detectFace = dataArray[8]

        self.reqCOM = dataArray[PacketDataIndex.DATA_COM.value - self.headerLen]
        self.reqINFO = dataArray[PacketDataIndex.DATA_INFO.value - self.headerLen]
        self.reqREQ = dataArray[PacketDataIndex.DATA_REQ.value - self.headerLen]
        self.reqPSTAT = dataArray[PacketDataIndex.DATA_PSTAT.value - self.headerLen]

        # if(dataArray[0] == 1)
        self.senFR = dataArray[PacketDataIndex.DATA_SEN_FR.value - self.headerLen]
        self.senFL = dataArray[PacketDataIndex.DATA_SEN_FL.value - self.headerLen]
        self.senBR = dataArray[PacketDataIndex.DATA_SEN_BR.value - self.headerLen]
        self.senBC = dataArray[PacketDataIndex.DATA_SEN_BC.value - self.headerLen]
        self.senBL = dataArray[PacketDataIndex.DATA_SEN_BL.value - self.headerLen]

        self.detectFace[0] = dataArray[PacketDataIndex.DATA_DETECT_FACE.value - self.headerLen]
        self.detectFace[1] = dataArray[PacketDataIndex.DATA_DETECT_FACE_X.value - self.headerLen]
        self.detectFace[2] = dataArray[PacketDataIndex.DATA_DETECT_FACE_Y.value - self.headerLen]

        self.detectColor[0] = dataArray[PacketDataIndex.DATA_DETECT_COLOR.value - self.headerLen]
        self.detectColor[1] = dataArray[PacketDataIndex.DATA_DETECT_COLOR_X.value - self.headerLen]
        self.detectColor[2] = dataArray[PacketDataIndex.DATA_DETECT_COLOR_Y.value - self.headerLen]

        self.detectMarker[0] = dataArray[PacketDataIndex.DATA_DETECT_MARKER.value - self.headerLen]
        self.detectMarker[1] = dataArray[PacketDataIndex.DATA_DETECT_MARKER_X.value - self.headerLen]
        self.detectMarker[2] = dataArray[PacketDataIndex.DATA_DETECT_MARKER_Y.value - self.headerLen]

        self.detectCat[0] = dataArray[PacketDataIndex.DATA_DETECT_CAT.value - self.headerLen]
        self.detectCat[1] = dataArray[PacketDataIndex.DATA_DETECT_CAT_X.value - self.headerLen]
        self.detectCat[2] = dataArray[PacketDataIndex.DATA_DETECT_CAT_Y.value - self.headerLen]

        self.btn = dataArray[PacketDataIndex.DATA_BTN_INPUT.value - self.headerLen]
        self.battery = dataArray[PacketDataIndex.DATA_BATTERY.value - self.headerLen]

        # Verify data processing complete
        self._receiver.checked()

        #return header.dataType

    def _receiving(self):
        while self._usePosThreadRun:

            self._bufferQueue.put(self._serialport.read())

            # Automatic update of data when incoming data background check is enabled
            if self._usePosCheckBackground:
                # while self.check() != DataType.None_:
                #     pass

                while self.check() != 0:
                    #print("check")
                    pass

            # sleep(0.001)

    def check(self):

        #
        while not self._bufferQueue.empty():
            dataArray = self._bufferQueue.get_nowait()
            self._bufferQueue.task_done()

            if (dataArray is not None) and (len(dataArray) > 0):
                # receive data output
                self._debugger._printReceiveData(dataArray)
                self._bufferHandler.extend(dataArray)

        while len(self._bufferHandler) > 0:
            stateLoading = self._receiver.call(self._bufferHandler.pop(0))

            # error output
            if stateLoading == StateLoading.Failure:
                # Incoming data output (skipped)
                self._debugger._printReceiveDataEnd()
                # Error message output
                self._debugger._printError(self._receiver.message)

            # log output
            if stateLoading == StateLoading.Loaded:
                # Incoming data output (skipped)
                self._debugger._printReceiveDataEnd()
                # Log output
                self._debugger._printLog(self._receiver.message)

            if self._receiver.state == StateLoading.Loaded:

                self._handler(self._receiver.data)
                return 1
        return 0

    def isOpen(self):
        if self._serialport is not None:
            return self._serialport.isOpen()
        else:
            return False

    def isConnected(self):
        if not self.isOpen():
            return False
        else:
            return self._usePosConnected

    def connect(self, portname = None):
        zumi_dongle_pid = 6790

        try:
           print("Serial connect")
           ser = serial.Serial()  # open first serial port
           ser.close()
        except:
            print("Serial library not installed")
            self.close()
           # exit()
            return False

        if portname is None:
            nodes = comports()
            size = len(nodes)
            for item in nodes:
                #print(item.device, item.vid)
                if item.vid == zumi_dongle_pid:
                    portname = item.device
                    print("Found zumiAI Dongle.", portname)
                    break
        try:
            print("Connecting to ZumiAI.")
            self._serialport = serial.Serial(
                port=portname,
                baudrate=115200)

            if self.isOpen():
                self._usePosThreadRun = True
                self._thread = Thread(target=self._receiving, args=(), daemon=True)
                self._thread.start()
                self._debugger._printLog("Connected.({0})".format(portname))

            else:
                self._debugger._printError("Could not connect to device.")
                print("Serial port could not open. Check the dognle and port.")
                self.close()
                exit()
                return False

        # Could not find device
        except:
            self._debugger._printError("Could not connect to device.")
            print("Could not find ZumiAI dongle.")
            self.close()
            exit()
            return False

        # 정지 신호 보내기
        #for i in range(10):
            #self.stop()
            #time.sleep(0.1)

    def close(self):
        # if self._serial_port and self._serial_port.isOpen():
        #     self._serial_port.close()
        #     self._serial_port = None

        # log output
        if self.isOpen():
            self._debugger._printLog("Closing serial port.")
        else:
            self._debugger._printLog("not connected.")


        self._debugger._printLog("Thread usePos False.")

        if self._usePosThreadRun:
            self._usePosThreadRun = False
            time.sleep(0.1)

        self._debugger._printLog("Thread Join.")

        if self._thread is not None:
            self._thread.join(timeout=1)

        self._debugger._printLog("Port Close.")

        if self.isOpen():
            self._serialport.close()
            time.sleep(0.2)

    def send(self, data):
        if not self.isOpen():
            return
        self._serialport.write(data)

        # if not self._serial_port or not self._serial_port.isOpen():
        #     raise ConnectionError("Serial port not open.")
        # try:
        #     # 데이터 인코딩 필요 시
        #     self._serial_port.write(data.encode('utf-8'))
        # except serial.SerialException as e:
        #      raise ConnectionError(f"Serial write error: {e}") from e
        # except Exception as e:
        #      raise ConnectionError(f"Error sending serial data: {e}") from e

    def get_req_datas(self):
        return (self.reqCOM, self.reqINFO, self.reqREQ, self.reqPSTAT) # Return a tuple copy


    def get_ir_all_readings(self):
        """Returns the latest IR sensor readings (FL, FR, BL, BC, BR)."""
        #with self._data_lock:
        return (self.senFL, self.senFR, self.senBL, self.senBC, self.senBR) # Return a tuple copy

    def get_ir_front_readings(self):
        """Returns the latest IR sensor readings (FL, FR, BL, BC, BR)."""
        #with self._data_lock:
        return (self.senFL, self.senFR)

    def get_ir_bottom_readings(self):
        """Returns the latest IR sensor readings (FL, FR, BL, BC, BR)."""
        #with self._data_lock:
        return (self.senBL, self.senBC, self.senBR)

    def get_detect_face_data(self):
        return self.detectFace

    def get_detect_color_data(self):
        return self.detectColor

    def get_detect_marker_data(self):
        return self.detectMarker

    def get_detect_cat_data(self):
        return self.detectCat

    def get_btn_data(self):
        return self.btn

    def get_battery_data(self):
        return self.battery


class ZumiAI:
    def __init__(self, usePosInterruptKey=False, usePosCheckBackground=True, usePosShowErrorMessage=True, usePosShowLogMessage=False,
                 usePosShowTransferData=True, usePosShowReceiveData=False):

        #self.timeStartProgram = time.time()  # Program Start Time Recording

        debugger = DebugOutput(
            show_log=usePosShowLogMessage,          # 일반 로그
            show_error=usePosShowErrorMessage,      # 에러 로그
            show_transfer=usePosShowTransferData,   # 송신 데이터 로그
            show_receive=usePosShowReceiveData      # 수신 데이터 로그
            )

        # 로거 인스턴스를 저장 (Dependency Injection)
        self._debugger = debugger if debugger is not None else DebugOutput() # 인자가 없으면 기본 DebugOutput 생성

        self._usePosCheckBackground = usePosCheckBackground

        # 인식 상태 저장
        self._current_request = RequestType.None_

        if usePosInterruptKey == True:
            """
            필요한 속성들을 초기화하고 키보드 리스너를 설정합니다.
            """
            # 작업 중지를 위한 이벤트 객체
            self._stop_event = threading.Event()
            # 인터럽트 명령 실행 트리거 플래그
            self._command_triggered = False

            # 키보드 리스너 설정
            # on_press 콜백으로 클래스 내부 메서드를 지정합니다.
            # on_release는 사용하지 않으므로 None
            self._listener = keyboard.Listener(on_press=self._on_press, on_release=None)

            # 리스너를 실행할 별도의 스레드 생성
            # daemon=False로 설정하여 메인 스레드 종료 시 명시적으로 join 대기
            self._listener_thread = threading.Thread(target=self._listener.start, daemon=False)

            self._listener_thread.start()

        # 외부 등록 명령 사용
        self._external_key_callbacks = {}
        # 키보드 리스너 객체 및 스레드
        self._external_listener = None
        self._external_listener_thread = None


        self._connection_handler = None


    def connect(self, portname=None):
        """
        주미 미니를 연결합니다.
        포트이름을 입력하지 않으면 동글을 자동검색하여 연결합니다.

        Args:
            portname : 연결된 포트이름(COM1~)

        Returns:
            없음

        Examples:
            >>> from zumi_AI.zumi_AI import *
                zumi = ZumiAI()
                zumi.connect(portname="COM84") # 사용 중인 포트명을 입력
        """
        #self._connection_handler = SerialConnectionHandler(self._usePosCheckBackground, debugger=self._debugger)
        #self._connection_handler.connect(portname)

        self._connection_handler = WebSocketConnectionHandler('ws://192.168.0.59/ws', self._usePosCheckBackground, debugger=self._debugger)
       # self._connection_handler = WebSocketConnectionHandler('ws://192.168.0.82/ws', self._usePosCheckBackground, debugger=self._debugger)
        self._connection_handler.connect()
        #self._connection_handler.start_display()


    def disconnect(self):
        """
        주미 미니를 연결을 종료합니다.

        Args:
            없음

        Returns:
            없음

        Examples:
            >>> zumi.disconnect()
        """
        self._connection_handler.close()



    def _parse_key_string(self, key_str):
        """
        문자열 키 이름을 pynput 키 객체로 변환합니다.
        (클래스 내부의 _parse_interrupt_key와 유사)
        """
        special_keys = {
            'space': keyboard.Key.space,
            'esc': keyboard.Key.esc,
            'enter': keyboard.Key.enter,
            'shift': keyboard.Key.shift,
            'ctrl': keyboard.Key.ctrl,
            'alt': keyboard.Key.alt,
            'up': keyboard.Key.up,
            'down': keyboard.Key.down,
            'left': keyboard.Key.left,
            'right': keyboard.Key.right,
            # 필요에 따라 다른 특수 키 추가
        }

        key_str_lower = key_str.lower()

        if key_str_lower in special_keys:
            return special_keys[key_str_lower]

        # 문자 키 처리
        if len(key_str) == 1:
            # pynput 1.0.0 이상
            try:
                return keyboard.KeyCode(char=key_str)
            except Exception:
                print(f"경고: 문자 '{key_str}'에 대한 KeyCode 생성 실패.")
                return None

        # 변환 실패
        return None

    def _external_on_press(self, key):
        """
        단일 외부 리스너에 연결될 콜백 함수.
        눌린 키에 해당하는 등록된 콜백이 있는지 확인하고 실행합니다.
        """
        # 눌린 키가 등록된 키보드 콜백 딕셔너리에 있는지 확인
        if key in self._external_key_callbacks:
            # 등록된 함수가 있다면 호출
            callback_func = self._external_key_callbacks[key]
            try:
                # 콜백 함수에 눌린 키 정보를 전달할 수도 있습니다.
                # callback_func(key)
                callback_func() # 여기서는 간단히 인자 없이 호출하도록 함. 필요시 변경.
                # print(f"-> 외부 콜백 실행: {key}") # 디버깅용
            except Exception as e:
                print(f"외부 콜백 실행 중 오류 발생 ({key}): {e}")
            # 참고: 여기서 return False를 반환하면 이 리스너 자체는 중지되지만,
            # 보통 외부 유틸리티 리스너는 여러 키에 반응하고 계속 실행되는 경우가 많으므로
            # 특정 키에 대한 콜백 실행이 리스너를 멈추게 하지는 않습니다.
            # 만약 특정 키(예: 'end' 키)가 눌리면 모든 외부 리스닝을 멈추고 싶다면
            # 해당 키에 연결된 콜백에서 external_key_interrupt_stop()을 호출하도록 구현합니다.


    def key_press_set(self, key_str, callback_func):
        """
        특정 키가 눌렸을 때 실행될 함수를 등록합니다.
        key_str: 등록할 키 이름 문자열 (예: "a", "esc", "space")
        callback_func: 해당 키가 눌렸을 때 호출될 함수
        """
        if not callable(callback_func):
            print(f"오류: '{key_str}'에 연결하려는 객체가 호출 가능한 함수가 아닙니다.")
            return

        key_obj = self._parse_key_string(key_str)

        if key_obj is None:
            print(f"경고: 알 수 없는 키 이름 '{key_str}'입니다. 등록되지 않았습니다.")
            return

        # 키와 함수 매핑 등록/업데이트
        self._external_key_callbacks[key_obj] = callback_func
        # print(f"'{key_str}' ({key_obj})에 콜백 함수 등록됨.") # 디버깅용

    def key_press_start(self):
        """
        등록된 키보드 인터럽트 리스너를 시작합니다.
        프로그램 시작 시 한 번만 호출하면 됩니다.
        """

        if self._external_listener_thread is not None and self._external_listener_thread.is_alive():
            print("키보드 인터럽트 리스너가 이미 실행 중입니다.")
            return

        if not self._external_key_callbacks:
            print("경고: 등록된 키보드 인터럽트 콜백 함수가 없습니다. 리스너를 시작하지 않습니다.")
            return

        # 단일 키보드 리스너 생성 및 설정
        self._external_listener = keyboard.Listener(on_press=self._external_on_press, on_release=None)

        # 리스너를 실행할 별도의 스레드 생성 및 시작
        # 데몬 스레드로 설정하여 메인 스레드 종료 시 자동으로 종료되도록 함 (간편한 유틸리티 목적)
        # 만약 확실한 정리가 필요하다면 daemon=False로 하고 external_key_interrupt_stop() 시 join() 호출
        self._external_listener_thread = threading.Thread(target=self._external_listener.start, daemon=True)
        self._external_listener_thread.start()

        print("외부 키보드 인터럽트 리스너 시작됨.")
        # 등록된 키 목록 출력 (선택 사항)
        # print("감지 대기 중인 키:", [_get_key_repr(k) for k in _external_key_callbacks.keys()])

    def key_press_stop(self):
        """
        실행 중인 외부 키보드 인터럽트 리스너를 중지합니다.
        프로그램 종료 시 명시적으로 호출할 수 있습니다.
        """
        if self._external_listener is not None and self._external_listener.running:
            print("외부 키보드 인터럽트 리스너 중지 요청.")
            self._external_listener.stop()
            # 데몬 스레드라면 join()은 필수는 아니지만, 기다리고 싶다면 호출
            if self._external_listener_thread is not None and self._external_listener_thread.is_alive():
                    self._external_listener_thread.join()
                    print("외부 키보드 인터럽트 리스너 스레드 종료됨.")
        else:
            print("실행 중인 외부 키보드 인터럽트 리스너가 없습니다.")

    def _on_press(self, key):
        """
        키가 눌렸을 때 키보드 리스너 스레드에서 호출되는 콜백 메서드.
        스페이스바 감지 시 중지 명령 실행 신호를 보냅니다.
        """
        try:
            if key == keyboard.Key.space:

                # 외부 설정 인터럽트도 종료
                self.key_press_stop()


                print(f"\n--- EMERGENCY STOP! ---\n")
                #self._stop_event.set() # 메인 루프 중지 신호
                #self._command_triggered = True # 특정 명령 실행 신호

                for i in range(3):
                    self.stop()
                    time.sleep(0.5)

                self.disconnect()
                # 스페이스바가 눌리면 리스너 자체를 즉시 중지합니다.
                # 리스너 스레드가 on_press에서 return False를 받은 것처럼 동작하게 함.

                return False # 리스너 중지

        except AttributeError:
            # 특수 키가 아닌 경우
            pass



    def buildHeader(self) -> bytearray:
        """
        고정 헤더를 구성합니다.
        header1: '$' (0x24)
        header2: 'R' (0x52)
        """
        return bytearray([0x24, 0x52])

    def set_request(self, request: RequestType):
        """
        전역적으로 사용할 request 값을 설정합니다.
        이 값은 따로 none 처리하기 전까지 계속 유지됩니다.
        """
        self._current_request |= request
        return self.sendCommand(CommandType.None_)


    def clear_request(self, request: RequestType):
        """
        전역적으로 설정된 request 값에서 특정 request 값을 제거합니다.
        """
        self._current_request &= ~request.value
        return self.sendCommand(CommandType.None_)


    def build_request_section(self, request: int) -> bytearray:
        """
        리퀘스트 값을 구성합니다.
        (이 예제에서는 커맨드 섹션과 별도로 리퀘스트를 구성하고 최종 데이터에 삽입합니다.)
        """
        return bytearray([request])


    def makeTransferDataArray(self, data):
        if (data is None):
            return None

        if isinstance(data, ISerializable):
            data = data.toArray()

        header = self.buildHeader()

        request_section = self.build_request_section(self._current_request)

        # 최종 데이터 배열 구성: 헤더 + command byte + request byte + 나머지 파라미터
        dataArray = header + bytearray([data[0]]) + request_section + data[1:]

        return dataArray


    def transfer(self, data):
        #if not self.isOpen():
        #    return
        dataArray = self.makeTransferDataArray(data)

        self._connection_handler.send(dataArray)

        # send data output
        self._debugger._printTransferData(dataArray)

        return dataArray

    def update_size(self,commandType):
        """
        commandType에 해당하는 CommandType_SIZE 값을 찾아서 size를 설정합니다.
        만약 commandType이 CommandType_SIZE에 없다면 기본값(예: 8)을 사용합니다.
        """
        try:
            self.size = CommandType_SIZE[commandType.name].value + 1

            if self.size > 8:
                self.size = 8

        except KeyError:
            # 기본 사이즈를 지정할 수 있음 (필요에 따라 조정)
            self.size = 8
        return self.size


    def sendCommand_test(self):
        """
        테스트 명령을 전송합니다.

        Args:
            없음

        Returns:
            없음

        Examples:
            없음

        """
        # self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)

        # data = Command_variable_byte()

        # data.commandType = commandType
        # data.size = self.update_size(data.commandType)

        # data.param1 = 20
        # data.param2 = 20
        # data.param3 = 20
        # data.param4 = 20
        # data.param5 = 20
        # data.param6 = 0x06
        # data.param7 = 0x07

        # data.param7 = 0x07

        # data = bytearray()
        # data.append(210)
        # data.append(210)
        # data.append(200)
        # data.append(200)
        # data.append(200)

        # #data = [0x200] * 5
        # byte_array = bytearray()





        text = ""
        encoded_bytes = text.encode('utf-8')
        #print(encoded_bytes)
        #print(len(encoded_bytes))

        # 첫 번째 바이트로 0x20을 갖는 bytearray 생성
        prefix = bytearray([CommandType.COMMAND_TEXT_INPUT.value])

        null_terminator = b'\x00'

        # 기존 encoded_bytes를 뒤에 추가
        final_bytes = prefix + encoded_bytes + null_terminator

        #print(final_bytes)
        print(len(final_bytes))
        # for value in data:
        #     # "<h"는 little-endian ( < ) 방식의 short ( h, 2바이트 부호 있는 정수)를 의미합니다.
        #     packed_bytes = pack("<h", value)
        #     byte_array.extend(data)
        # return self.sendCommand_text(CommandType.COMMAND_TEXT_INPUT, encoded_bytes)



        return self.transfer(final_bytes)






    def sendCommand(self,*args):
        """
        명령을 전송합니다.

        Args:
            가변 인자 : args

        """
        print(f"받은 인자의 개수: {len(args)}")
        for arg in args:
            print(arg)

        # self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)

        data = Command_variable_byte()

        data.commandType = args[0]
        data.size = self.update_size(data.commandType)

        if len(args) >= 2:
            data.param1 = args[1]

        if len(args) >= 3:
            data.param2 = args[2]

        if len(args) >= 4:
            data.param3 = args[3]

        if len(args) >= 5:
            data.param4 = args[4]

        if len(args) >= 6:
            data.param5 = args[5]

        if len(args) >= 7:
            data.param6 = args[6]
        if len(args) >= 8:
            data.param7 = args[7]

        return self.transfer(data)


    def send_move_dist(self, speed=0, dist=0, dir=0):
        """
        거리 만큼 이동하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            dist  : 거리
            dir   : 방향 (0 : 전진, 1: 후진)

        Returns:
            없음

        Examples:
            >>> zumi.send_move_dist(1, 20, 0)
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(dist < 0) :dist = 0
        if(dist > 300) :dist = 300

        if(dir < 0) :dir = 0
        if(dir > 1) :dir = 1

        return self.sendCommand(CommandType.COMMAND_GO_UNTIL_DIST, speed, dist, dir)


    def forward_dist(self, speed=1, dist=10):
        """
        거리 만큼 전진하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            dist  : 거리

        Returns:
            없음

        Examples:
            >>> zumi.forward_dist(1, 20)
        """
        return self.send_move_dist(speed, dist, 0)

    def reverse_dist(self, speed=1, dist=10):
        """
        거리 만큼 후진하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            dist  : 거리

        Returns:
            없음

        Examples:
            >>> zumi.reverse_dist(1, 20)
        """
        return self.send_move_dist(speed, dist, 1)


    def send_turn(self, speed=0, deg=0, dir=0):
        """
        각도 만큼 회전하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            deg  : 각도
            dir   : 방향 (0 : 전진, 1: 후진)

        Returns:
            없음

        Examples:
            >>> zumi.send_turn(1, 20, 0)
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(dir < 0) :dir = 0
        if(dir > 1) :dir = 1

        #if(deg < 0) :deg = 0
        #if(deg > 360) :deg = 360

        deg_high = 0
        deg_low = 0

        if(deg < 255) : deg_low = deg

        else :
            deg_high = deg // 256  # 상위 바이트 (몫)
            deg_low = deg % 256   # 하위 바이트 (나머지)

        return self.sendCommand(CommandType.COMMAND_FREE_TURN_PYTHON, speed, deg_low, deg_high, dir)


    def left_turn(self, speed=1, deg=90):
        """
        각도 만큼 왼쪽으로 회전하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            deg  : 각도

        Returns:
            없음

        Examples:
            >>> zumi.left_turn(1, 90)
        """
        return self.send_turn(speed, deg, 0)

    def right_turn(self, speed=1, deg=90):
        """
        각도 만큼 오른쪽으로 회전하기 명령을 전송합니다.

        Args:
            speed : 속도 (1, 2, 3)
            deg  : 각도

        Returns:
            없음

        Examples:
            >>> zumi.right_turn(1, 90)
        """
        return self.send_turn(speed, deg, 1)











    def forward_dist_quick(self, dist=20):
        """
        빠르게 거리 만큼 전진하기 명령을 전송합니다.

        Args:
            dist : 거리

        Returns:
            없음

        Examples:
            zumi.forward_dist_quick(20)
        """

        if(dist < 0) :dist = 0
        if(dist > 300) :dist = 300

        return self.sendCommand(CommandType.COMMAND_QUICK_GOGO, dist)

    def reverse_dist_quick(self, dist=20):
        """
        빠르게 거리 만큼 후진하기 명령을 전송합니다.

        Args:
            dist : 거리

        Returns:
            없음

        Examples:
            >>> zumi.reverse_dist_quick(20)
        """

        if(dist < 0) :dist = 0
        if(dist > 300) :dist = 300

        return self.sendCommand(CommandType.COMMAND_QUICK_GOBACK, dist)


    def left_turn_quick(self, deg=90):
        """
        ! 이슈 : 각도 제어는 5도씩, 360도까지 도달하지 못함
        빠르게 각도 만큼 왼쪽으로 회전하기 명령을 전송합니다.

        Args:
            deg : 각도

        Returns:
            없음

        Examples:
            >>> zumi.left_turn_quick(90)
        """
        if(deg > 360) :deg = 360

        deg = int(deg / 5)
        # 우노보드의 타임아웃이 짧음
        # 각도를 1도씩 제어하고 싶음
        return self.sendCommand(CommandType.COMMAND_QUICK_LEFT, deg)

    def right_turn_quick(self, deg=90):
        """
        ! 이슈 : 각도 제어는 5도씩, 360도까지 도달하지 못함
        빠르게 각도 만큼 오른쪽으로 회전하기 명령을 전송합니다.

        Args:
            deg  : 각도

        Returns:
            없음

        Examples:
            >>> zumi.right_turn_quick(90)
        """

        if(deg > 360) :deg = 360

        deg = int(deg / 5)
        # 우노보드의 타임아웃이 짧음
        # 각도를 1도씩 제어하고 싶음
        return self.sendCommand(CommandType.COMMAND_QUICK_RIGHT, deg)


    def led_control(self, r=0, g=0, b=0):
        """
        led 색상을 변경

        Args:
            r  : 빨강 밝기 (0~10)
            g  : 초록 밝기 (0~10)
            b  : 파랑 밝기 (0~10)

        Returns:
            없음

        Examples:
            >>> zumi.led_control(10,10,10)
        """
        return self.sendCommand(CommandType.COMMAND_LED, r, g, b)



    #def led_pattern(self, pattern=LED_effectType.LED_BLINK, time=1):
    def led_pattern(self, pattern=1, time=1):

        """
        led 패턴을 변경

        Args:
            pattern  : - 0 : 켜있는 상태
                       - 1 : 깜박이기
                       - 2 : 두번 깜박이기
                       - 3 : 점점 밝아졌다가 어두워지기
                       - 4 : 점점 어두워지기
                       - 5 : 점점 밝아지기
                       - 6 : 무지개색상으로 변하기
            time     : 시간 (초)

        Returns:
            없음

        Examples:
            >>> zumi.led_pattern(1, 1)
        """
        if not isinstance(pattern, LED_effectType):
            try:
                pattern = LED_effectType(pattern)
            except ValueError:
                pattern = LED_effectType.LED_NORMAL  # 기본값

        time_high = 0
        time_low = 0
        time = int(time *1000)
        if(time < 255) : time_low = time

        else :
            time_high = time // 256  # 상위 바이트 (몫)
            time_low = time % 256   # 하위 바이트 (나머지)

        return self.sendCommand(CommandType.COMMAND_PATTERN_LED, pattern.value, time_high, time_low)




    def go_sensor(self, speed = 1, senL = 150, senR = 150):
        """
        !양쪽이 감지되어야 멈춘다.
        센서에 감지 될때까지 직진 (감지 기준 값 이하가 될 때까지)

         Args:
            - speed : 속도 (1, 2, 3)
            - senL  : 왼쪽 센서 감지 기준 값
            - senR  : 오른쪽 센서 감지 기준 값

        Returns:
            없음

        Examples:
            >>> zumi.go_sensor(3,150,150)
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(senL < 0) :senL = 0
        if(senL > 255) :senL = 255

        if(senR < 0) :senR = 0
        if(senR > 255) :senR = 255

        #senL = int(senL/4)
        #senR = int(senR/4)

        return self.sendCommand(CommandType.COMMAND_GOSENSOR, speed, senL, senR)


    def play_sound(self, sound = 1):
        """
        ! 와이파이 작동 불가 이슈 있음
        소리를 재생합니다.

         Args:
            sound : 사운드 번호

        Returns:
            없음

        Examples:
            >>> zumi.play_sound(1)
        """

        return self.sendCommand(CommandType.COMMAND_PLAY_SOUND, sound)


    def control_motor(self, dirL = 2, speedL = 50, dirR = 1, speedR = 50):
        """
        모터를 작동합니다.

        Args:
            dirL   : 왼쪽 모터 회전 방향 (0 정지, 1 정회전, 2 역회전)
            speedL : 왼쪽 모터 회전 속도 (0~250)
            dirR   : 오론쪽 모터 회전 방향 (0 정지, 1 정회전, 2 역회전)
            speedR : 오른쪽 모터 회전 속도 (0~250)

        Returns:
            없음

        Examples:
            >>> zumi.control_motor(2,50,1,50)
        """

        if(speedL < 0) : speedL = 0
        if(speedR > 250) : speedL = 250

        if(speedR < 0) : speedR = 0
        if(speedR > 250) : speedR = 250

        if(dirL < 0) : dirL = 0
        if(dirL > 2) : dirL = 2
        if(dirR < 0) : dirR = 0
        if(dirR > 2) : dirR = 2

        dir = 0b01000000 #RESOLUTION_1 고정 값 (0~250 단위를 쓰겠다는 설정)
        dir = dir | dirL
        dir = dir | (dirR<<4)

        return self.sendCommand(CommandType.COMMAND_MOTOR1_INFINITE, speedL, speedR, dir)


    def control_motor_time(self, dirL = 2, speedL = 50, dirR = 1, speedR = 50, time = 1):
        """
        일정한 시간동안 모터를 제어합니다.

        Args:
            dirL   : 왼쪽 모터 회전 방향 (0 정지, 1 정회전, 2 역회전)
            speedL : 왼쪽 모터 회전 속도 (0~250)
            dirR   : 오론쪽 모터 회전 방향 (0 정지, 1 정회전, 2 역회전)
            speedR : 오른쪽 모터 회전 속도 (0~250)
            time   : 작동시킬 시간 (초: 0.1~25)

        Returns:
            없음

        Examples:
            >>> zumi.control_motor_time(2,50,1,50,1)
        """

        time = int(time * 10)
        if(time < 0):time = 0
        if(time > 250):time = 250

        if(speedL < 0) : speedL = 0
        if(speedR > 250) : speedL = 250

        if(speedR < 0) : speedR = 0
        if(speedR > 250) : speedR = 250

        if(dirL < 0) : dirL = 0
        if(dirL > 2) : dirL = 2
        if(dirR < 0) : dirR = 0
        if(dirR > 2) : dirR = 2

        dir = 0b01000000 #RESOLUTION_1 고정 값 (0~250 단위를 쓰겠다는 설정)
        dir = dir | dirL
        dir = dir | (dirR<<4)

        return self.sendCommand(CommandType.COMMAND_MOTOR_TIME, speedL, speedR, dir, time)


    def linefollower(self, speed = 1,  senBL = 100, senBR = 100, senBC = 100, time = 0):
        """
        !! 라인이 시작되면 멈출수 있어야 함.
        일정한 거리만큼 라인을 따라 이동합니다.

        Args:
            speed : 속도 (1, 2, 3)
            senBL : 아래 왼쪽 센서 감지 기준 값
            senBR : 아래 오른쪽 센서 감지 기준 값
            senBC : 아래 가운데 센서 감지 기준 값
            time  : 시간 (초: 0.1~25) (0: 경우 교차로 감지떄까지 계속 작동)

        Returns:
            없음

        Examples:
            >>> zumi.linefollower(1,10)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        if(senBL < 0) :senBL = 0
        if(senBL > 255) :senBL = 255

        if(senBR < 0) :senBR = 0
        if(senBR > 255) :senBR = 255

        if(senBC < 0) :senBC = 0
        if(senBC > 255) :senBC = 255

        #senBL = int(senBL/4)
        #senBR = int(senBR/4)
        #senBC = int(senBC/4)

        time = int(time * 10)
        if(time < 0):time = 0
        if(time > 250):time = 250

        return self.sendCommand(CommandType.COMMAND_LINE_TRACING, speed, senBL, senBR, senBC, time)


    def linefollower_distance(self, speed = 1, dist = 10):
        """
        !! 부정확 함 : 테스트 및 수정 필요
        일정한 거리만큼 라인을 따라 이동합니다.

        Args:
            speed : 속도 (1, 2, 3)
            dist  : 거리 (cm)

        Returns:
            없음

        Examples:
            >>> zumi.linefollower_distance(1,10)
        """
        if isinstance(speed, float):
            speed = int(speed)
        elif not isinstance(speed, int):
            raise TypeError("speed는 숫자여야 합니다.")

        if isinstance(dist, float):
            dist = int(dist)
        elif not isinstance(dist, int):
            raise TypeError("dist는 숫자여야 합니다.")

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        if(dist < 0) : dist = 0
        if(dist > 255) : dist = 255

        return self.sendCommand(CommandType.COMMAND_LINE_TRACE_DIST, speed, dist)


    def stop(self):
        """
        움직임을 멈춥니다.

        Args:
            없음

        Returns:
            없음

        Examples:
            >>> zumi.stop()
        """

        return self.sendCommand(CommandType.COMMAND_MOTION_STOP)


    def move_infinite(self, speed=1, dir=0):
        """
        선택한 방향으로 계속 이동합니다.

        Args:
            speed : 속도 (1, 2, 3)
            dir   : 방향 (0:전진, 1:후진)

        Returns:
            없음

        Examples:
            >>> zumi.move_infinite(1,0)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        if(dir < 0) : dir = 0
        if(dir > 1) : dir = 1

        temp = 0

        return self.sendCommand(CommandType.COMMAND_GO_INFINITE,speed,temp,dir)

    def forward_infinite(self, speed=1):
        """
        계속 전진합니다.

        Args:
            speed : 속도 (1, 2, 3)

        Returns:
            없음

        Examples:
            >>> zumi.forward_infinite(1)
        """

        dir = 0

        return self.move_infinite(speed,dir)

    def reverse_infinite(self, speed=1):
        """
        계속 후진합니다.

        Args:
            speed : 속도 (1, 2, 3)

        Returns:
            없음

        Examples:
            >>> zumi.reverse_infinite(1)
        """

        dir = 1

        return self.move_infinite(speed,dir)


    def linefollower_infinite(self, speed = 1):
        """
        계속 라인을 따라 이동합니다.

        Args:
            speed : 속도 (1, 2, 3)

        Returns:
            없음

        Examples:
            >>> zumi.linefollower_infinite(1,10)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        return self.sendCommand(CommandType.COMMAND_TRACE_INFINITE, speed)


    def get_IR_sensor_all(self):
        """
        전체 센서 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 전방 왼쪽 센서 값
            - 전방 오른쪽 센서 값
            - 하단 왼쪽 센서 값
            - 하단 중앙 센서 값
            - 오른쪽 센서 값

        Examples:
            >>> ir = zumi.get_IR_sensor_all()
                print(ir)
        """

        return self._connection_handler.get_ir_all_readings()

    def get_IR_sensor_bottom(self):
        """
        하단 센서 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 하단 왼쪽 센서 값
            - 하단 중앙 센서 값
            - 하단 오른쪽 센서 값

        Examples:
            >>> ir = zumi.get_IR_sensor_bottom()
                print(ir)
        """

        return self._connection_handler.get_ir_bottom_readings()

    def get_IR_sensor_front(self):
        """
        전방 센서 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 전방 왼쪽 센서 값
            - 전방 오른쪽 센서 값

        Examples:
            >>> ir = zumi.get_IR_sensor_front()
                print(ir)
        """

        return self._connection_handler.get_ir_front_readings()

    def set_detect_color(self, set = 0):
        """
        색상 감지 기능을 설정합니다.

        Args:
            set : (0 끄기, 1 켜기)

        Returns:
            없음

        Examples:
            >>> zumi.set_detect_color(1)
        """

        if(set == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)

    def set_detect_face(self, set = 0):
        """
        얼굴 감지 기능을 설정합니다.

        Args:
            set : (0 끄기, 1 켜기)

        Returns:
            없음

        Examples:
            >>> zumi.set_detect_face(1)
        """

        if(set == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_FACE_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_FACE_DETECT)

    def set_detect_cat(self, set = 0):
        """
        고양이 감지 기능을 설정합니다.

        Args:
            set : (0 끄기, 1 켜기)

        Returns:
            없음

        Examples:
            >>> zumi.set_detect_cat(1)
        """

        if(set == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_CAT_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_CAT_DETECT)

    def set_detect_marker(self, set = 0):
        """
        마커 감지 기능을 설정합니다.

        Args:
            set : (0 끄기, 1 켜기)

        Returns:
            없음

        Examples:
            >>> zumi.set_detect_marker(1)
        """

        if(set == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_APRIL_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_APRIL_DETECT)

    def change_screen(self, set = 1):
        """
        화면을 전환합니다.

        Args:
            set : (1 카메라, 2 표정)

        Returns:
            없음

        Examples:
            >>> zumi.change_screen(2)
        """

        if(set < 0) : set = 0
        if(set > 2) : set = 2

        return self.sendCommand(CommandType.COMMAND_SCREEN_TOGGLE, set)

    def change_emotion(self, set = 1):
        """
        표정을 바꿉니다.

        Args:
            set : 표정 리스트

        Returns:
            없음

        Examples:
            >>> zumi.change_emotion(2)
        """

        if(set < 0) : set = 0
        #if(set > 2) : set = 2

        return self.sendCommand(CommandType.COMMAND_EMOTION_CHANGE, set)


    def sendText(self, CommandType, text, newline = 0):
        """
        문자를 출력합니다.

        Args:
            CommandType : CommandType
            text    : 문자열
            newline : 줄바꿈 선택 (0: 사용안함, 1: 사용)

        Returns:
            없음

        Examples:
            >>> zumi.sendText(CommandType.COMMAND_TEXT_INPUT.value,"Hello, world!")
        """

        encoded_bytes = text.encode('utf-8')
        if(len(encoded_bytes) > 27):
            #print("too long")
            encoded_bytes = encoded_bytes[:27]  # 처음부터 27바이트까지만 슬라이싱


        print(len(encoded_bytes))

        # 첫 번째 바이트로 CommandType을 갖는 bytearray 생성
        preCommandType = bytearray([CommandType])

        # 종료 바이트 추가
        null_terminator = b'\x00'
        # 기존 encoded_bytes를 뒤에 추가

        # 줄바꿈
        if(newline == 1) :
            line_terminator = b'\n'
            final_bytes = preCommandType + encoded_bytes + line_terminator +null_terminator
        else:
            final_bytes = preCommandType + encoded_bytes + null_terminator

        print(len(final_bytes))
        return self.transfer(final_bytes)

    def display_text(self, text, newline = 0):
        """
        문자를 출력합니다.

        Args:
            text    : 문자열
            newline : 줄바꿈 선택 (0: 사용안함, 1: 사용)

        Returns:
            없음

        Examples:
            >>> zumi.display_text("Hello, world!")
        """

        return self.sendText(CommandType.COMMAND_TEXT_INPUT.value,text,newline)


    def display_text_add(self, text, newline = 0):
        """
        기존 문자에 추가로 문자를 출력합니다.

        Args:
            text : 문자열
            newline : 줄바꿈 선택 (0: 사용안함, 1: 사용)

        Returns:
            없음

        Examples:
            >>> zumi.display_text_add("Hello, world!")
        """

        return self.sendText(CommandType.COMMAND_TEXT_ADD.value,text,newline)

        return self.transfer(final_bytes)

    def display_text_clear(self):
        """
        문자열을 지웁니다.

        Args:
            text : 문자열

        Returns:
            없음

        Examples:
            >>> zumi.display_text_clear()
        """
        self.display_text("")

    def display_text_set(self, color = 0, size = 0):
        """
        문자의 색상과 크기를 설정합니다.

        Args:
            색상 : 0~22 (0의 경우 현재 상태 유지, 1은 흰색)
            크기 : 0~5 (0의 경우 현재 상태 유지)

        Returns:
            없음

        Examples:
            >>> zumi.display_text_set(1,5)

        """
        usePos = 0

        self.sendCommand(CommandType.COMMAND_TEXT_SET, color ,size, usePos, 0, 0)

    # x,y 좌표를 절대 좌표로 변경해야 함 음수를 양수로 변환하고, 다시 음수로 변환
    def display_text_pos(self, pos_x = 0, pos_y = 0):
            """
            문자의 위치를 지정합니다.

            Args:
                pos_x (int, optional): 텍스트의 가로 위치를 설정합니다.
                                   기본값은 0입니다.
                                   - 값이 양수이면 기준점에서 오른쪽으로 이동합니다. (예: pos_x=10은 오른쪽으로 10만큼 이동)
                                   - 값이 음수이면 기준점에서 왼쪽으로 이동합니다. (예: pos_x=-10은 왼쪽으로 10만큼 이동)
                pos_y (int, optional): 텍스트의 세로 위치를 설정합니다.
                                   기본값은 0입니다.
                                   - 값이 양수이면 기준점에서 아래쪽으로 이동합니다. (예: pos_y=10은 아래쪽으로 10만큼 이동)
                                   - 값이 음수이면 기준점에서 위쪽으로 이동합니다. (예: pos_y=-10은 위쪽으로 10만큼 이동)
            Returns:
                없음

            Examples:
                >>> zumi.display_text_pos(10,10)

            """
            usePos = 1
            # 음수를 전송하기위한 오프셋 설정
            pos_x = pos_x + 500
            pos_y = pos_y + 500

            if not (0 <= pos_x <= 2047 and 0 <= pos_y <= 2047):
                print("Error: pos_x and pos_y must be between 0 and 2047", file=sys.stderr)
                return None
            if not (usePos == 0 or usePos == 1):
                print("Error: usePos must be 0 or 1", file=sys.stderr)
                return None

            # pos_x의 하위 8비트 추출
            # 0xFF는 이진수로 11111111입니다.
            buf2 = pos_x & 0xFF

            # pos_y의 하위 8비트 추출
            buf3 = pos_y & 0xFF

            # buf1에 저장할 비트들 조합
            buf1 = 0

            # pos_x의 상위 3비트 추출 (오른쪽 시프트 8, 하위 3비트 마스크)
            # 0x07은 이진수로 00000111입니다.
            upper_bits_pos_x = (pos_x >> 8) & 0x07
            # 추출한 상위 3비트를 buf1의 비트 6, 5, 4 위치로 이동 (왼쪽 시프트 4)
            buf1 |= upper_bits_pos_x << 4

            # pos_y의 상위 3비트 추출 (오른쪽 시프트 8, 하위 3비트 마스크)
            upper_bits_pos_y = (pos_y >> 8) & 0x07
            # 추출한 상위 3비트를 buf1의 비트 3, 2, 1 위치로 이동 (왼쪽 시프트 1)
            buf1 |= upper_bits_pos_y << 1

            # 플래그 비트 추출 (하위 1비트 마스크)
            usePos_bit = usePos & 0x01
            # 추출한 플래그 비트를 buf1의 비트 7 위치로 이동 (왼쪽 시프트 7)
            buf1 |= usePos_bit << 7

            # buf1의 비트 0은 사용하지 않으므로 0으로 유지됩니다.

            #print(buf1, buf2, buf3)

            self.sendCommand(CommandType.COMMAND_TEXT_SET, 0 ,0, buf1 ,buf2, buf3)



    def _get_req_datas(self):
        """
        get_req_datas
        """
        return self._connection_handler.get_req_datas()

    def get_detect_face(self):
        """
        얼굴 감지 값을 가져옵니다.

        Args:
            없음

        Returns:
            - (0 미감지, 1 감지)
            - 감지된 얼굴의 x축 값
            - 감지된 얼굴의 y축 값

        Examples:
            >>> detect_face = zumi.get_detect_face()
                print(detect_face)
        """

        return self._connection_handler.get_detect_face_data()

    def get_detect_color(self):
        """
        색상 감지 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 감지된 색상 값(0~7), 미감지(254)
            - 감지된 색상의 x축 값
            - 감지된 색상의 y축 값

        Examples:
            >>> detect_color = zumi.get_detect_color()
                print(detect_color)
        """
        return self._connection_handler.get_detect_color_data()

    def get_detect_marker(self):
        """
        마커 감지 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 감지된 마커 값, 미감지(254)
            - 감지된 마커의 x축 값
            - 감지된 마커의 y축 값

        Examples:
            >>> detect_marker = zumi.get_detect_marker()
                print(detect_marker)
        """
        return self._connection_handler.get_detect_marker_data()

    def get_detect_cat(self):
        """
        고양이 감지 값을 가져옵니다.

        Args:
            없음

        Returns:
            - (0 미감지, 1 감지)
            - 감지된 고양이의 x축 값
            - 감지된 고양이의 y축 값

        Examples:
            >>> detect_cat = zumi.get_detect_cat()
                print(detect_cat)
        """
        return self._connection_handler.get_detect_cat_data()

    def get_button(self):
        """
        버튼 값을 가져옵니다.

        Args:
            없음

        Returns:
            - 0 누른 버튼 없음
            - 1 빨강 버튼 눌림
            - 2 파란 버튼 눌림
            - 4 초록 버튼 눌림
            - 8 노란 버튼 눌림

        Examples:
            >>> detect_btn = zumi.get_button()
                print(detect_btn)
        """

        return self._connection_handler.get_btn_data()

    def get_battery(self):
        """
        배터리 잔량 값을 가져옵니다.

        Args:
            없음

        Returns:
           배터리 퍼센트(0~100)

        Examples:
            >>> battery = zumi.get_battery()
                print(detect_battery)
        """
        return self._connection_handler.get_battery_data()

    def set_calibration_motors(self):
        """
        모터를 보정합니다.

        1) 주미 미니를 눕혀주세요.
        2) 명령을 실행합니다.
        3) 완료가 될때까지 기다려주세요.
           약간의 시간이 걸립니다.

        Args:
            없음

        Returns:
           없음

        Examples:
            >>> zumi.set_calibration_motors()
        """
        self.sendCommand(CommandType.COMMAND_MOTOR_CALIBRATION_START)

        print("Start Motor calibration")

        self.display_text_set(15,5)
        self.display_text("Motor",1)
        self.display_text_add("calibration",1)
        self.display_text_add("Start",1)

        time.sleep(1)

        try:
            while True:
                datas = self._get_req_datas()
                p_exe = datas[3]
                print(p_exe)

                if(p_exe == 0):
                    print("Done")
                    self.display_text("Done",1)
                    break
                self.display_text_add(".")
                time.sleep(3)

        except KeyboardInterrupt:
            print("Done")
        finally:
            print("Program finished.")

        time.sleep(2)
        self.display_text_clear()


    # def sendForward(self):
    #     data = Command()
    #     data.commandType = CommandType.COMMAND_GOGO
    #     data.option = 0
    #     return self.transfer(data)

    ##--------------------------------------------------------------------#
    # 소켓 영상 제어 명령어
    def start_video_viewer(self):
        """
        영상출력을 시작합니다.
        """
        self._connection_handler.ws_start_display()



    # --- vision ---
    def LeftRightFlipMode(self, flag:bool):
        self._connection_handler.LeftRightFlipMode(flag)


    ##--------------------------------------------------------------------#]
    # sensor
    def sensorInit(self):
        """
        센서 값을 가져오기를 준비합니다.
        """
        self._connection_handler.sensorInit()

    def sensorStart(self):
        """
        센서 값을 가져오기를 시작합니다.
        """
        self._connection_handler.sensorStart()

    def sensorStop(self):
        """
        센서 값을 가져오기를 중지합니다.
        """
        self._connection_handler.sensorStop()


    ##--------------------------------------------------------------------#

    # face
    def FacedetectorInit(self):
        self._connection_handler.FacedetectorInit()

    def FacedetectorStart(self):
        self._connection_handler.FacedetectorStart()

    def FacedetectorStop(self):
        self._connection_handler.FacedetectorStop()


    def FaceCapture(self,name:str, captureCount:int=5, path:str=pkg_resources.resource_filename(__package__,"res/face/")):
        self._connection_handler.FaceCapture(name,captureCount,path)

    def TrainFaceData(self,facePath:str =pkg_resources.resource_filename(__package__,"res/face/")):
        self._connection_handler.TrainFaceData(facePath)

    def DeleteFaceData(self, name:str, facePath:str=pkg_resources.resource_filename(__package__,"res/face/")):
        self._connection_handler.DeleteFaceData(name,facePath)

    def DeleteAllFaceData(self, facePath:str=pkg_resources.resource_filename(__package__,"res/face/")):
        self._connection_handler.DeleteAllFaceData(facePath)


    def GetFaceCount(self):
        return self._connection_handler.GetFaceCount()

    def GetFaceExist(self,name:str="Human0"):
        return self._connection_handler.GetFaceExist(name)

    def GetFaceNames(self):
        return self._connection_handler.GetFaceNames()


    def GetFaceSize(self,name:str="Human0"):
        return self._connection_handler.GetFaceSize(name)

    def GetFaceCenterPoint(self,name:str="Human0"):
        return self._connection_handler.GetFaceCenterPoint(name)

    def GetFaceLandmarkPoint(self, landmark=1, name: str = "Human0"):
        if not isinstance(landmark, face_landmark):
            try:
                landmark = face_landmark(landmark)
            except ValueError:
                landmark = face_landmark.NOSE
        return self._connection_handler.GetFaceLandmarkPoint(landmark,name)


    ##--------------------------------------------------------------------#
    # april
    def AprilDetectorInit(self):
        self._connection_handler.AprilDetectorInit()

    def AprilDetectorStart(self):
        self._connection_handler.AprilDetectorStart()

    def AprildetectorStop(self):
        self._connection_handler.AprildetectorStop()

    def GetAprilId(self):
        return self._connection_handler.GetAprilId()

    def GetAprilCenterPoint(self):
        return self._connection_handler.GetAprilCenterPoint()

    def GetAprilExist(self,id:int):
        return self._connection_handler.GetAprilExist(id)


    ##--------------------------------------------------------------------#
    # number
    def NumberRecognizerInit(self):
        self._connection_handler.NumberRecognizerInit()

    def NumberRecognizerStart(self):
        self._connection_handler.NumberRecognizerStart()

    def NumberRecognizerStop(self):
        self._connection_handler.NumberRecognizerStop()

    ##--------------------------------------------------------------------#]
    # scketch
    def SketchDetectorInit(self):
        self._connection_handler.SketchDetectorInit()

    def SketchDetectorStart(self):
        self._connection_handler.SketchDetectorStart()

    def SketchDetectorStop(self):
        self._connection_handler.SketchDetectorStop()

    def SketchCapture(self, name:str, captureCount:int=5, path:str=pkg_resources.resource_filename(__package__,"res/sketch/")):
        self._connection_handler.SketchCapture(name,captureCount,path)

    def TrainSketchData(self, sketchPath:str = pkg_resources.resource_filename(__package__,"res/sketch/")):
        self._connection_handler.TrainSketchData(sketchPath)

    def GetSketchExist(self,name:str="Sketch"):
        return self._connection_handler.GetSketchExist(name)

    def GetSketchCenterPoint(self,name:str="Sketch"):
        return self._connection_handler.GetSketchCenterPoint(name)


    ##--------------------------------------------------------------------#]
    # gesture

    def GestureDetectorInit(self):
        self._connection_handler.GestureDetectorInit()

    def GestureDetectorStart(self):
        self._connection_handler.GestureDetectorStart()

    def GestureDetectorStop(self):
        self._connection_handler.GestureDetectorStop()

    # def GetGesturePoint(self,name:str="Sketch"):
    #     return self._connection_handler.GetSketchCenterPoint(name)
