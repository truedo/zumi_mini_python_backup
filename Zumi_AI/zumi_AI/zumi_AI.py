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


from protocol import * # make html 사용시 적용
from receiver import * # make html 사용시 적용

#from .protocol import *
#from .receiver import *


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

try:
    import websocket # websocket-client 라이브러리
    import threading
    import time
    import queue
    import cv2
    import numpy as np
    import ssl # WSS (WebSocket Secure) 사용 시 필요

    WEBSOCKET_LIB_IS_AVAILABLE = True

except ImportError:
    WEBSOCKET_LIB_IS_AVAILABLE = False
    print("Warning: 웹소켓을 위한 라이브러리가 없습니다.")


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


        #print(self.detectFace)
        #print(self.detectColor)
        #print(self.detectMarker)
        #print(self.detectCat)

        #print(self.btn)
        #print(self.battery)

        # print(str(self.senFL)+" "+
        #       str(self.senFR)+" "+
        #       str(self.senBL)+" "+
        #       str(self.senBR)+" "+
        #       str(self.senBC))

        # # Save incoming data
        # self._runHandler(header, dataArray)

        # # Run a callback event
        # self._runEventHandler(header.dataType)

        # # Monitor data processing
        # self._runHandlerForMonitor(header, dataArray)

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
    def __init__(self, usePosInterruptKey=True, usePosCheckBackground=True, usePosShowErrorMessage=True, usePosShowLogMessage=False,
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
        self._connection_handler = SerialConnectionHandler(self._usePosCheckBackground, debugger=self._debugger)
        self._connection_handler.connect(portname)

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
            if pattern == 1:
                pattern=LED_effectType.LED_BLINK
            elif pattern == 2:
                pattern=LED_effectType.LED_FLICKER
            elif pattern == 3:
                pattern=LED_effectType.LED_DIMMING
            elif pattern == 4:
                pattern=LED_effectType.LED_SUNRIZE
            elif pattern == 5:
                pattern=LED_effectType.LED_SUNSET
            elif pattern == 6:
                pattern=LED_effectType.LED_RAINBOW
            else:
                pattern=LED_effectType.LED_NORMAL


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

    def get_req_datas(self):
        """
        get_req_datas
        """
        return self._connection_handler.get_req_datas()

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
                datas = self.get_req_datas()
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

