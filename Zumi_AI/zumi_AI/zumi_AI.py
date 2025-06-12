#serial
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


# #websocket
# import cv2
# import numpy as np
# import websocket
# import argparse
# import time
# import threading
# import queue

# import logging
# import re # 정규 표현식 모듈 임포트


# from protocol import * # make html 사용시 적용
# from receiver import * # make html 사용시 적용
# from serial_class import * # make html 사용시 적용
# from socket_class import * # make html 사용시 적용


from .protocol import *
from .receiver import *

from .serial_class import *
from .socket_class import *



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

    def _is_valid_ip(self, address):
        """주어진 문자열이 유효한 IPv4 주소 형식인지 확인합니다."""
        # 간단한 IPv4 정규 표현식 (더 엄격하게 만들 수 있음)
        # 0-255.0-255.0-255.0-255 형식 확인
        pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        if re.match(pattern, address):
            # 각 옥텟이 0-255 범위에 있는지 추가 검사
            parts = address.split('.')
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        return False


    def connect(self, connection_info=None):
        """
        주미 AI를 연결합니다.

        동글 연결과 IP 연결 방식을 지원합니다. 연결 방식에 따라 사용 방법이 다릅니다.

        Args:
            connection_info (str or None):

                         * **동글 연결**:

                           ``zumiAI.connect()`` 와 같이 입력을 하지 않으면 자동으로 연결된 동글을 검색해서 연결을 시도합니다.

                           ``zumiAI.connect("COM84")`` 와 같이 동글의 포트명을 직접 입력해서 연결을 시도할 수도 있습니다.

                         * **IP 연결**:

                           ``zumiAI.connect("192.168.0.100")`` 와 같이 주미 AI의 IP를 직접 입력하여 연결을 시도합니다.
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.connect() # 동글 연결 : 자동으로 동글이 연결된 포트를 검색해서 연결
            >>> zumiAI.connect("COM84") # 동글 연결 : 동글이 연결된 포트명을 직접 입력
            >>> zumiAI.connect("192.168.0.100") # IP 연결: 주미 AI의 IP를 입력
        """
        # Handling
        if connection_info is None:
            # 1. portname이 None이면 시리얼 포트 자동 검색
            self._debugger._printLog("입력값이 없습니다. 시리얼 포트 자동 검색을 시도합니다.")
            #return self._connect_serial(None)
            self._connection_handler = SerialConnectionHandler(self._usePosCheckBackground, debugger=self._debugger)
            self._connection_handler.connect(connection_info)

        elif self._is_valid_ip(connection_info):
            # 2. portname이 IP 주소 형식인 경우 웹소켓 연결
            self._debugger._printLog(f"'{connection_info}'이(가) IP 주소 형식입니다. 웹소켓 연결을 시도합니다.")
            #return self._connect_websocket(connection_info)
            #connection_info = '192.168.0.59'
            websocket_url = f'ws://{connection_info}/ws'
            self._connection_handler = WebSocketConnectionHandler(
                websocket_url,
                self._usePosCheckBackground,
                debugger=self._debugger
            )
            self._connection_handler.connect()



        else:
            # 3. 그 외의 경우 (예: "COM84", "/dev/ttyUSB0") 시리얼 포트 연결
            self._debugger._printLog(f"'{connection_info}'이(가) 시리얼 포트 이름 형식입니다. 시리얼 연결을 시도합니다.")
            #return self._connect_serial(connection_info)
            self._connection_handler = SerialConnectionHandler(self._usePosCheckBackground, debugger=self._debugger)
            self._connection_handler.connect(connection_info)



    def disconnect(self):
        """
        주미 AI의 연결을 종료합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.disconnect()
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


    def key_press_set(self, key_str:str, callback_func:callable):
        """
        사용자 키보드의 특정 키가 눌렸을 때 실행될 콜백 함수를 등록합니다.

        이 함수를 통해 사용자는 키보드 입력에 따라 주미 AI의 동작을 제어하는
        맞춤형 기능을 구현할 수 있습니다.

        Args:
            key_str (str): 등록할 키의 이름 문자열입니다. (예: "a", "esc", "space", "enter", "up", "down", "left", "right")
                        대소문자를 구분하며, 특수 키는 특정 문자열로 지정됩니다.
            callback_func (callable): 지정된 키가 눌렸을 때 호출될 함수입니다.
                                    이 함수는 인자를 받지 않는 형태여야 합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Raises:
            ValueError: 'callback_func'가 호출 가능한 함수가 아닐 경우 오류 메시지를 출력합니다.
            Warning: 'key_str'이 유효하지 않은 키 이름일 경우 경고 메시지를 출력합니다.

        Examples:
            >>> def my_forward_function():
            >>>     print("앞으로 이동!")
            >>>     zumiAI.forward(1)
            >>>
            >>> def my_stop_function():
            >>>     print("정지!")
            >>>     zumiAI.stop()
            >>>
            >>> zumiAI.key_press_set("w", my_forward_function) # 'w' 키를 누르면 my_forward_function 호출
            >>> zumiAI.key_press_set("s", my_stop_function)    # 's' 키를 누르면 my_stop_function 호출
            >>> # 이제 키보드 'w'를 누르면 앞으로 이동하고 's'를 누르면 정지합니다.
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

        이 함수는 주미 AI 프로그램이 시작될 때 한 번만 호출하여
        사용자가 이전에 `key_press_set()` 함수로 등록한 키보드 콜백 함수들이
        정상적으로 작동하도록 합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Raises:
            RuntimeWarning: 키보드 인터럽트 리스너가 이미 실행 중일 경우 경고 메시지를 출력하고 함수를 종료합니다.
            UserWarning: 등록된 키보드 콜백 함수가 없을 경우 경고 메시지를 출력하고 리스너를 시작하지 않습니다.

        Examples:
            >>> # 먼저 키보드 콜백 함수를 등록합니다.
            >>> def go_forward():
            >>>     print("앞으로 이동!")
            >>>     zumiAI.forward(1)
            >>>
            >>> zumiAI.key_press_set("w", go_forward)
            >>>
            >>> # 키보드 리스너를 시작합니다.
            >>> zumiAI.key_press_start()
            >>> # 이제 'w' 키를 누르면 go_forward 함수가 실행됩니다.
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

        이 함수는 key_press_start()로 시작된 키보드 리스너를 안전하게 종료합니다.

        프로그램이 완전히 종료되기 전에 명시적으로 호출하여 리소스 누수를 방지하는 것이 좋습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 키보드 리스너를 시작한 후 작업을 수행합니다.
            >>> # ...
            >>> # 작업이 끝나면 리스너를 중지합니다.
            >>> zumiAI.key_press_stop()
            외부 키보드 인터럽트 리스너 중지 요청.
            외부 키보드 인터럽트 리스너 스레드 종료됨. # 또는 '실행 중인 외부 키보드 인터럽트 리스너가 없습니다.'
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


    def send_move_dist(self, speed:int=0, dist:int=0, dir:int=0):
        """
        지정된 거리만큼 주미에게 이동하도록 명령을 전송합니다.

        이 함수는 ``forward_dist()``, ``reverse_dist()`` 대신에 방향을 변수로 입력받아야 하는 경우에 사용됩니다.

        Args:
            speed (int): 이동 속도 (가능한 값: 1, 2, 3)
            dist (int): 이동할 거리 (단위: cm, 0 ~ 300)
            dir (int): 이동 방향 (0: 전진, 1: 후진)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.send_move_dist(1, 20, 0)
            주미에게 속도 1로 20cm 전진하라는 명령을 전송합니다.
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(dist < 0) :dist = 0
        if(dist > 300) :dist = 300

        if(dir < 0) :dir = 0
        if(dir > 1) :dir = 1

        return self.sendCommand(CommandType.COMMAND_GO_UNTIL_DIST, speed, dist, dir)


    def forward_dist(self, speed:int=1, dist:int=10):
        """
        지정된 거리만큼 주미를 전진시킵니다.

        Args:
            speed (int): 전진 속도 (가능한 값: 1, 2, 3)
            dist (int): 전진할 거리 (단위: cm, 0 ~ 300)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.forward_dist(1, 20)
            주미를 속도 1로 20cm 전진시킵니다.
        """

        return self.send_move_dist(speed, dist, 0)

    def reverse_dist(self, speed:int=1, dist:int=10):
        """
        지정된 거리만큼 주미를 후진시킵니다.

        Args:
            speed (int): 후진 속도 (가능한 값: 1, 2, 3)
            dist (int): 후진할 거리 (단위: cm, 0 ~ 300)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.reverse_dist(1, 20)
            주미를 속도 1로 20cm 후진시킵니다.
        """

        return self.send_move_dist(speed, dist, 1)


    def send_turn(self, speed:int=0, deg:int=0, dir:int=0):
        """
        지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        이 함수는 ``left_turn()``, ``right_turn()`` 대신에 방향을 변수로 입력받아야 하는 경우에 사용됩니다.

        Args:
            speed (int): 회전 속도 (가능한 값: 1, 2, 3)
            deg (int): 회전할 각도 (단위: 각도)
            dir (int): 회전 방향 (0: 좌회전, 1: 우회전)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.send_turn(1, 90, 0)
            주미를 속도 1로 90도 왼쪽으로 회전시킵니다.
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(dir < 0) :dir = 0
        if(dir > 1) :dir = 1

        deg_high = 0
        deg_low = 0

        if(deg < 255) : deg_low = deg

        else :
            deg_high = deg // 256  # 상위 바이트 (몫)
            deg_low = deg % 256   # 하위 바이트 (나머지)

        return self.sendCommand(CommandType.COMMAND_FREE_TURN_PYTHON, speed, deg_low, deg_high, dir)


    def left_turn(self, speed:int=1, deg:int=90):
        """
        왼쪽으로 지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        Args:
            speed (int): 회전 속도 (가능한 값: 1, 2, 3)
            deg (int): 회전할 각도 (단위: 각도, 예: 90)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.left_turn(1, 90)
            주미를 속도 1로 90도 왼쪽으로 회전시킵니다.
        """

        return self.send_turn(speed, deg, 0)

    def right_turn(self, speed:int=1, deg:int=90):
        """
        오른쪽으로 지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        Args:
            speed (int): 회전 속도 (가능한 값: 1, 2, 3)
            deg (int): 회전할 각도 (단위: 각도, 예: 90)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.right_turn(1, 90)
            주미를 속도 1로 90도 오른쪽으로 회전시킵니다.
        """

        return self.send_turn(speed, deg, 1)


    def send_move_dist_quick(self, dist:int=0, dir:int=0):
        """
        빠르게 주미에게 지정된 거리만큼 이동하도록 명령을 전송합니다.

        이 함수는 ``forward_dist_quick()``, ``reverse_dist_quick()`` 대신에 방향을 변수로 입력받아야 하는 경우에 사용됩니다.


        Args:
            dist (int): 이동할 거리 (단위: cm, 0 ~ 300)
            dir (int): 이동 방향 (0: 전진, 1: 후진)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.send_move_dist_quick(20, 0)
            주미에게 20cm를 빠르게 전진하라는 명령을 전송합니다.
        """

        if(dist < 0) :dist = 0
        if(dist > 300) :dist = 300

        if(dir < 0) :dir = 0
        if(dir > 1) :dir = 1

        if dir == 0:
            return self.sendCommand(CommandType.COMMAND_QUICK_GOGO, dist)
        else:
            return self.sendCommand(CommandType.COMMAND_QUICK_GOBACK, dist)



    def forward_dist_quick(self, dist:int=20):
        """
        빠르게 지정된 거리만큼 주미를 전진시킵니다.

        Args:
            dist (int): 전진할 거리 (단위: cm, 0 ~ 300)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.forward_dist_quick(20)
            주미를 빠르게 20cm 전진시킵니다.
        """

        return self.send_move_dist_quick(dist, 0)



    def reverse_dist_quick(self, dist:int=20):
        """
        빠르게 지정된 거리만큼 주미를 후진시킵니다.

        Args:
            dist (int): 후진할 거리 (단위: cm, 0 ~ 300)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.reverse_dist_quick(20)
            주미를 빠르게 20cm 후진시킵니다.
        """

        return self.send_move_dist_quick(dist, 1)


    def send_turn_quick(self,deg:int=0, dir:int=0):
        """
        빠르게 지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        이 함수는 ``left_turn_quick()``, ``right_turn_quick()`` 대신에 방향을 변수로 입력받아야 하는 경우에 사용됩니다.

        Args:
            deg (int): 회전할 각도 (단위: 도)
            dir (int): 회전 방향 (0: 좌회전, 1: 우회전)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.send_turn_quick(90, 0)
            주미를 90도 빠르게 왼쪽으로 회전시킵니다.

        Note:
            각도 제어는 5도씩만 가능하며, 360도까지 정확하게 도달하지 못할 수 있습니다.
        """

        if(deg > 360) :deg = 360

        deg = int(deg / 5)
        # 우노보드의 타임아웃이 짧음
        # 각도를 1도씩 제어하고 싶음

        #return self.sendCommand(CommandType.COMMAND_FREE_TURN_PYTHON, speed, deg_low, deg_high, dir)
        if dir == 0:
            return self.sendCommand(CommandType.COMMAND_QUICK_LEFT, deg)
        else:
            return self.sendCommand(CommandType.COMMAND_QUICK_RIGHT, deg)


    def left_turn_quick(self, deg:int=90):
        """
        빠르게 왼쪽으로 지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        Args:
            deg (int): 회전할 각도 (단위: 각도, 예: 90)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.left_turn_quick(90)
            주미를 90도 빠르게 왼쪽으로 회전시킵니다.
        """

        return self.send_turn_quick(deg, 0)

    def right_turn_quick(self, deg:int=90):
        """
        빠르게 오른쪽으로 지정된 각도만큼 주미를 회전시키는 명령을 전송합니다.

        Args:
            deg (int): 회전할 각도 (단위: 각도, 예: 90)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.right_turn_quick(90)
            주미를 90도 빠르게 오른쪽으로 회전시킵니다.
        """

        return self.send_turn_quick(deg, 1)


    def led_control(self, r:int=0, g:int=0, b:int=0):
        """
        주미의 LED 색상을 변경합니다. 각 색상 채널의 밝기를 조절하여 원하는 색상을 만들 수 있습니다.

        Args:
            r (int): 빨강 채널의 밝기 (0~10)
            g (int): 초록 채널의 밝기 (0~10)
            b (int): 파랑 채널의 밝기 (0~10)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.led_control(10, 10, 10)
            주미의 LED를 가장 밝은 흰색으로 변경합니다.
            >>> zumiAI.led_control(10, 0, 0)
            주미의 LED를 가장 밝은 빨간색으로 변경합니다.
            >>> zumiAI.led_control(0, 0, 0)
            주미의 LED를 끕니다.
        """
        return self.sendCommand(CommandType.COMMAND_LED, r, g, b)


    def led_pattern(self, pattern:int=1, time:int=1):
        """
        주미의 LED에 다양한 패턴 효과를 적용합니다.

        Args:
            pattern (int): 적용할 LED 패턴의 종류를 선택합니다.

                * 0: LED가 켜진 상태를 유지합니다.

                * 1: LED가 깜박입니다.

                * 2: LED가 두 번 깜박입니다.

                * 3: LED가 점점 밝아졌다가 어두워집니다.

                * 4: LED가 점점 어두워집니다.

                * 5: LED가 점점 밝아집니다.

                * 6: LED 색상이 무지개색으로 변합니다.

            time (int): 패턴이 지속될 시간 (단위: 초)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.led_pattern(1, 1)
            주미의 LED를 1초 동안 깜박이게 합니다.
            >>> zumiAI.led_pattern(6, 5)
            주미의 LED 색상을 5초 동안 무지개색으로 변화시킵니다.
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




    def go_sensor(self, speed:int = 1, senL:int = 150, senR:int = 150):
        """
        전방 센서에 무언가가 감지될 때까지 주미가 직진합니다. (감지 기준값 이하가 될 때까지).

        Args:
            speed (int): 직진 속도 (가능한 값: 1, 2, 3)
            senL (int): 왼쪽 전방 센서 감지 기준값 (0 ~ 255)
            senR (int): 오른쪽 전방 센서 감지 기준값 (0 ~ 255)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.go_sensor(3, 150, 150)
            주미가 속도 3으로 직진하다가, 양쪽 전방 센서 값이 150 이하로 감지되면 멈춥니다.

        Note:
            Warning: 주미는 양쪽 전방 센서(왼쪽, 오른쪽)가 모두 설정된 기준값 이하로 감지되어야 멈춥니다.
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


    def play_sound(self, sound:int = 1):
        """
        주미에서 지정된 사운드를 재생합니다.

        Args:
            sound (int): 재생할 사운드의 ID (사운드 번호)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.play_sound(1)
            주미에서 ID 1번에 해당하는 사운드를 재생합니다.

        Note:
            와이파이 연결 환경에서는 사운드 재생이 정상적으로 작동하지 않을 수 있습니다.
        """

        return self.sendCommand(CommandType.COMMAND_PLAY_SOUND, sound)


    def control_motor(self, dirL:int=2, speedL:int=50, dirR:int=1, speedR:int=50):
        """
        모터를 작동합니다.

        Args:
            dirL (int): 왼쪽 모터 회전 방향 (0: 정지, 1: 정회전, 2: 역회전)
            speedL (int): 왼쪽 모터 회전 속도 (0~250)
            dirR (int): 오른쪽 모터 회전 방향 (0: 정지, 1: 정회전, 2: 역회전)
            speedR (int): 오른쪽 모터 회전 속도 (0~250)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Example:
            >>> zumiAI.control_motor(2, 50, 1, 50)
            왼쪽 모터를 역회전 속도 50으로, 오른쪽 모터를 정회전 속도 50으로 작동합니다.
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


    def control_motor_time(self, dirL:int = 2, speedL:int = 50, dirR:int = 1, speedR:int = 50, time:float = 1):
        """
        일정한 시간 동안 모터를 제어합니다.

        Args:
            dirL (int): 왼쪽 모터 회전 방향 (0: 정지, 1: 정회전, 2: 역회전)
            speedL (int): 왼쪽 모터 회전 속도 (0~250)
            dirR (int): 오른쪽 모터 회전 방향 (0: 정지, 1: 정회전, 2: 역회전)
            speedR (int): 오른쪽 모터 회전 속도 (0~250)
            time (float): 모터 작동 시간 (초 단위, 0.1 ~ 25)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.control_motor_time(2, 50, 1, 50, 1)
            왼쪽 모터를 역회전(속도 50), 오른쪽 모터를 정회전(속도 50)으로 1초 동안 작동시킵니다.
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
        라인 감지 센서를 이용하여 라인을 따라 주미가 이동하도록 명령합니다.
        지정된 시간 동안 또는 교차로를 감지할 때까지 작동합니다.

        Args:
            speed (int): 라인 따라 이동 속도 (가능한 값: 1, 2, 3)
            senBL (int): 아래 왼쪽 센서 감지 기준 값 (0 ~ 255)
            senBR (int): 아래 오른쪽 센서 감지 기준 값 (0 ~ 255)
            senBC (int): 아래 가운데 센서 감지 기준 값 (0 ~ 255)
            time (float): 라인을 따라 이동할 시간 (초 단위: 0.1 ~ 25). 0을 입력하면 교차로를 감지할 때까지 계속 작동합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.linefollower(1, 100, 100, 100, 5)
            주미가 센서 감지 기준값 100으로 속도 1로 5초 동안 라인을 따라 이동합니다.
            >>> zumiAI.linefollower(2, 120, 120, 120, 0)
            주미가 센서 감지 기준값 120으로 속도 2로 교차로를 감지할 때까지 라인을 따라 이동합니다.

        Note:
            이 함수는 라인 시작 시 멈출 수 있는 기능이 필요할 수 있습니다.
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        if(senBL < 0) :senBL = 0
        if(senBL > 255) :senBL = 255

        if(senBR < 0) :senBR = 0
        if(senBR > 255) :senBR = 255

        if(senBC < 0) :senBC = 0
        if(senBC > 255) :senBC = 255

        time = int(time * 10)
        if(time < 0):time = 0
        if(time > 250):time = 250

        return self.sendCommand(CommandType.COMMAND_LINE_TRACING, speed, senBL, senBR, senBC, time)


    def linefollower_distance(self, speed:int = 1, dist:int = 10):

        """
        라인을 따라 지정된 거리만큼 주미가 이동하도록 명령합니다.

        Args:
            speed (int): 라인 따라 이동 속도 (가능한 값: 1, 2, 3)
            dist (int): 라인을 따라 이동할 거리 (단위: cm, 0 ~ 255)
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.linefollower_distance(1, 10)
            주미를 속도 1로 10cm만큼 라인을 따라 이동시킵니다.

        Note:
            이 함수는 부정확할 수 있으므로 테스트가 필요합니다.
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
        주미의 모든 움직임을 즉시 멈춥니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.stop()
            현재 진행 중인 주미의 움직임을 멈춥니다.
        """

        return self.sendCommand(CommandType.COMMAND_MOTION_STOP)


    def move_infinite(self, speed:int=1, dir:int=0):
        """
        지정된 속도와 방향으로 주미가 계속 이동하도록 명령합니다.

        이 함수는 ``forward_infinite()``, ``reverse_infinite()`` 대신에 방향을 변수로 입력받아야 하는 경우에 사용됩니다.

        Args:
            speed (int): 이동 속도 (가능한 값: 1, 2, 3)
            dir (int): 이동 방향 (0: 전진, 1: 후진)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.move_infinite(1, 0)
            주미를 속도 1로 계속 전진시킵니다. (정지하려면 다른 이동 함수를 호출하거나 stop() 함수를 사용하세요.)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        if(dir < 0) : dir = 0
        if(dir > 1) : dir = 1

        temp = 0

        return self.sendCommand(CommandType.COMMAND_GO_INFINITE,speed,temp,dir)

    def forward_infinite(self, speed:int=1):
        """
        지정된 속도로 주미가 계속 전진하도록 명령합니다.

        Args:
            speed (int): 전진 속도 (가능한 값: 1, 2, 3)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.forward_infinite(1)
            주미를 속도 1로 계속 전진시킵니다.
            (정지하려면 stop() 함수를 호출하거나 control_motor(0,0,0,0)을 사용하세요.)
        """

        dir = 0

        return self.move_infinite(speed,dir)

    def reverse_infinite(self, speed:int=1):
        """
        지정된 속도로 주미가 계속 후진하도록 명령합니다.

        Args:
            speed (int): 후진 속도 (가능한 값: 1, 2, 3)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.reverse_infinite(1)
            주미를 속도 1로 계속 후진시킵니다.
            (정지하려면 stop() 함수를 호출하거나 control_motor(0,0,0,0)을 사용하세요.)
        """
        dir = 1

        return self.move_infinite(speed,dir)


    def linefollower_infinite(self, speed:int = 1):
        """
        라인을 따라 지정된 속도로 계속 주미가 이동하도록 명령합니다.

        Args:
            speed (int): 라인 따라 이동 속도 (가능한 값: 1, 2, 3)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.linefollower_infinite(1)
            주미를 속도 1로 라인을 계속 따라 이동시킵니다. (정지하려면 stop() 함수를 사용하세요.)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        return self.sendCommand(CommandType.COMMAND_TRACE_INFINITE, speed)


    def get_IR_sensor_all(self) -> list:
        """
        주미의 모든 적외선(IR) 센서 값을 가져옵니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 정수형 센서 값들을 포함하는 리스트를 반환합니다:
                - 전방 왼쪽 센서 값
                - 전방 오른쪽 센서 값
                - 하단 왼쪽 센서 값
                - 하단 중앙 센서 값
                - 하단 오른쪽 센서 값

        Examples:
            >>> ir_values = zumiAI.get_IR_sensor_all()
            >>> print(ir_values)
            [120, 130, 80, 90, 75] # 예시 출력: [전방 왼쪽, 전방 오른쪽, 하단 왼쪽, 하단 중앙, 하단 오른쪽 센서 값]
        """

        return self._connection_handler._get_ir_all_readings()

    def get_IR_sensor_front(self) -> list:
        """
        주미의 전방 적외선(IR) 센서 값들을 가져옵니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 정수형 센서 값들을 포함하는 리스트를 반환합니다:
                - 전방 왼쪽 센서 값
                - 전방 오른쪽 센서 값

        Examples:
            >>> ir_front_values = zumiAI.get_IR_sensor_front()
            >>> print(ir_front_values)
            [120, 130] # 예시 출력: [전방 왼쪽, 전방 오른쪽 센서 값]
        """

        all_readings = self._connection_handler._get_ir_all_readings()
        # 튜플 슬라이싱을 사용하여 앞쪽 2개의 값만 선택
        return all_readings[0:2] # 또는 all_readings[:2]


    def get_IR_sensor_bottom(self) -> list:
        """
        주미의 하단 적외선(IR) 센서 값들을 가져옵니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 정수형 센서 값들을 포함하는 리스트를 반환합니다:
                - 하단 왼쪽 센서 값
                - 하단 중앙 센서 값
                - 하단 오른쪽 센서 값

        Examples:
            >>> ir_bottom_values = zumiAI.get_IR_sensor_bottom()
            >>> print(ir_bottom_values)
            [80, 90, 75] # 예시 출력: [하단 왼쪽, 하단 중앙, 하단 오른쪽 센서 값]
        """

        all_readings = self._connection_handler._get_ir_all_readings()
        # 튜플 슬라이싱을 사용하여 앞쪽 2개의 값만 선택
        return all_readings[2:5] # 또는 all_readings[2:]

    def set_zumi_color_detection(self, enable:int = 0):
        """
        주미의 자체 색상 감지 기능을 켜거나 끕니다.

        이 함수는 주미가 카메라를 통해 특정 색상을 인식하는
        기능을 활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (int, optional): 색상 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 0 (비활성화)입니다.

                                    - **0**: 색상 감지 기능을 비활성화합니다.

                                    - **1**: 색상 감지 기능을 활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_color_detection(1) # 색상 감지 기능 켜기
            >>> zumiAI.set_zumi_color_detection(0) # 색상 감지 기능 끄기
            >>> zumiAI.set_zumi_color_detection()  # 기본값인 끄기(비활성화)로 설정
        """

        if(enable == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)

    def set_zumi_face_detection (self, enable:int = 0):
        """
        주미의 자체 얼굴 감지 기능을 켜거나 끕니다.

        이 함수는 주미가 카메라를 통해 사람의 얼굴을 인식하는
        기능을 활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (int, optional): 얼굴 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 0 (비활성화)입니다.

                                    - **0**: 얼굴 감지 기능을 비활성화합니다.

                                    - **1**: 얼굴 감지 기능을 활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_face_detection (1) # 얼굴 감지 기능 켜기
            >>> zumiAI.set_zumi_face_detection (0) # 얼굴 감지 기능 끄기
            >>> zumiAI.set_zumi_face_detection ()  # 기본값인 끄기(비활성화)로 설정
        """

        if(enable == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_FACE_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_FACE_DETECT)

    def set_zumi_cat_detection(self, enable:int = 0):
        """
        주미의 자체 고양이 감지 기능을 켜거나 끕니다.

        이 함수는 주미가 카메라를 통해 고양이를 인식하는 기능을
        활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (int, optional): 고양이 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 0 (비활성화)입니다.

                                    - **0**: 고양이 감지 기능을 비활성화합니다.

                                    - **1**: 고양이 감지 기능을 활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_cat_detection(1) # 고양이 감지 기능 켜기
            >>> zumiAI.set_zumi_cat_detection(0) # 고양이 감지 기능 끄기
            >>> zumiAI.set_zumi_cat_detection()  # 기본값인 끄기(비활성화)로 설정
        """

        if(enable == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_CAT_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_CAT_DETECT)

    def set_zumi_marker_detection(self, enable:int = 0):
        """
        주미의 자체 마커 감지 기능을 켜거나 끕니다.

        이 함수를 사용하여 주미가 마커를 인식하는
        기능을 활성화하거나 비활성화할 수 있습니다.

        Args:
            enable (int, optional): 마커 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 0 (비활성화)입니다.

                                    - **0**: 마커 감지 기능을 비활성화합니다.

                                    - **1**: 마커 감지 기능을 활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_marker_detection(1) # 마커 감지 기능 켜기
            >>> zumiAI.set_zumi_marker_detection(0) # 마커 감지 기능 끄기
            >>> zumiAI.set_zumi_marker_detection()  # 기본값인 끄기(비활성화)로 설정
        """

        if(enable == 1) :
            self.set_request(RequestType.REQUEST_ENTRY_APRIL_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_APRIL_DETECT)

    def change_screen(self, screen_type:int = 1):
        """
        주미의 디스플레이 화면을 전환합니다.

        이 함수는 주미가 디스플레이에 표시될 콘텐츠를 변경합니다.

        Args:
            screen_type (int, optional): 전환할 화면의 타입을 지정합니다.
                                         기본값은 1입니다.

                                         - **1**: 카메라를 화면에 표시합니다.

                                         - **2**: 주미의 표정(감정) 디스플레이를 화면에 표시합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.change_screen(1) # 화면을 카메라 피드로 전환
            >>> zumiAI.change_screen(2) # 화면을 주미의 표정 디스플레이로 전환
            >>> zumiAI.change_screen()  # 기본값인 카메라 피드로 화면 전환
        """


        if(screen_type < 0) : screen_type = 0
        if(screen_type > 2) : screen_type = 2

        return self.sendCommand(CommandType.COMMAND_SCREEN_TOGGLE, screen_type)

    def change_emotion(self, set:int = 1):
        """
        주미의 표정을 변경합니다.

        이 함수는 사전에 정의된 표정 중 하나를 선택하여 주미의 얼굴 표정을 업데이트합니다.

        Args:
            set (int): 변경할 표정의 ID입니다. 각 ID는 특정 표정에 매핑됩니다.
                    (예: 0은 기본 표정, 1은 행복한 표정 등, 자세한 표정 리스트는 문서를 참조하세요.)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.change_emotion(0) # 주미의 표정을 기본 표정으로 변경
            >>> zumiAI.change_emotion(2) # 주미의 표정을 웃는 표정으로 변경 (예시)
            >>> zumiAI.change_emotion(5) # 주미의 표정을 놀란 표정으로 변경 (예시)

        Note:
            표정 리스트 (추가 예정)
        """

        if(set < 0) : set = 0
        #if(set > 2) : set = 2

        return self.sendCommand(CommandType.COMMAND_EMOTION_CHANGE, set)

    def sendText(self, CommandType, text:str, newline:int = 0):
        """
        주어진 명령 타입에 따라 텍스트를 디스플레이에 전송하고 출력합니다.

        이 함수는 특정 명령과 함께 문자열을 디스플레이로 보내며,
        텍스트 출력 후 줄바꿈 여부를 제어할 수 있습니다.

        Args:
            CommandType: 텍스트를 전송할 명령의 타입을 지정합니다.
                         CommandType, Enum 또는 해당 Enum의 값을 사용해야 합니다.
                         (예: CommandType.COMMAND_TEXT_INPUT.value 는 텍스트 입력을 위한 명령입니다.)
            text (str): 디스플레이에 출력할 문자열입니다.
            newline (int, optional): 텍스트 출력 후 줄바꿈 여부를 설정합니다.
                                     기본값은 0입니다.
                                     - **0**: 텍스트 출력 후 줄바꿈을 하지 않습니다 (다음 텍스트는 같은 줄에 이어서 출력됩니다).
                                     - **1**: 텍스트 출력 후 자동으로 줄바꿈을 수행합니다 (다음 텍스트는 새로운 줄에서 시작합니다).

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.sendText(CommandType.COMMAND_TEXT_INPUT.value, "Hello, Zumi!")
            >>> zumiAI.sendText(CommandType.COMMAND_TEXT_INPUT.value, "Next line.", newline=1)
            >>> zumiAI.sendText(CommandType.COMMAND_MESSAGE_DISPLAY.value, "Important message.")
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

    def display_text(self, text:str, newline:int = 0):
        """
        주어진 문자열을 디스플레이에 출력합니다.

        이 함수는 새로운 텍스트를 디스플레이에 표시하며,
        필요에 따라 텍스트 출력 후 줄바꿈을 처리할 수 있습니다.

        Args:
            text (str): 디스플레이에 출력할 문자열입니다.
            newline (int, optional): 텍스트 출력 후 줄바꿈 여부를 설정합니다.
                                     기본값은 0입니다.

                                     - 0: 텍스트 출력 후 줄바꿈을 하지 않습니다 (다음 텍스트는 같은 줄에 이어서 출력됨).

                                     - 1: 텍스트 출력 후 자동으로 줄바꿈을 수행합니다 (다음 텍스트는 새로운 줄에서 시작).

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.display_text("Hello, Zumi!") # "Hello, Zumi!"를 출력하고 줄바꿈하지 않음
            >>> zumiAI.display_text("Next line.", newline=1) # "Next line."을 출력하고 다음 줄로 이동
            >>> zumiAI.display_text("This is on a new line.") # 새로운 줄에 텍스트 출력
        """

        return self.sendText(CommandType.COMMAND_TEXT_INPUT.value,text,newline)

    def display_text_add(self, text:str, newline:int = 0):
        """
        현재 디스플레이에 기존 텍스트에 이어서 새로운 텍스트를 출력합니다.

        이 함수는 화면에 표시된 텍스트 뒤에 주어진 문자열을 추가하고,
        필요에 따라 자동으로 줄바꿈을 처리할 수 있습니다.

        Args:
            text (str): 디스플레이에 추가할 문자열입니다.
            newline (int, optional): 텍스트 출력 후 줄바꿈 여부를 설정합니다.
                                     기본값은 0입니다.

                                     - 0: 줄바꿈을 사용하지 않습니다 (텍스트가 현재 줄에 이어져 출력됨).

                                     - 1: 텍스트 출력 후 자동으로 줄바꿈을 수행합니다 (다음 텍스트는 새 줄에서 시작).

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.display_text_add("Hello")  # "Hello"를 출력하고 같은 줄에 유지
            >>> zumiAI.display_text_add(", world!", newline=1) # " world!"를 이어 출력하고 다음 줄로 이동
            >>> zumiAI.display_text_add("New line of text.") # 새로운 줄에 텍스트 출력
        """

        return self.sendText(CommandType.COMMAND_TEXT_ADD.value,text,newline)

        return self.transfer(final_bytes)

    def display_text_clear(self):
        """
        디스플레이에 표시된 모든 텍스트를 지웁니다.

        이 함수는 화면의 모든 텍스트 내용을 초기화합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.display_text_clear() # 화면의 모든 텍스트를 지웁니다.
        """
        self.display_text("")

    def display_text_set(self, color:int = 0, size:int = 0):
        """
        텍스트의 색상과 크기를 설정합니다.

        Args:
            color (int): 텍스트의 색상 코드를 지정합니다 (0-22).

                         - 0은 현재 색상을 유지합니다.

                         - 1은 흰색을 나타냅니다.
            size (int): 텍스트의 크기를 지정합니다 (0-5).

                        - 0은 현재 크기를 유지합니다.

                        - 숫자가 클수록 텍스트가 커집니다.

        Returns:
            None: 이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.display_text_set(1, 5) # 흰색 텍스트, 가장 큰 크기

        Note:
            색상 리스트 (추가 예정)
        """
        usePos = 0

        self.sendCommand(CommandType.COMMAND_TEXT_SET, color ,size, usePos, 0, 0)

    # x,y 좌표를 절대 좌표로 변경해야 함 음수를 양수로 변환하고, 다시 음수로 변환
    def display_text_pos(self, pos_x:int = 0, pos_y:int = 0):
        """
        텍스트의 위치를 지정합니다.

        이 함수는 디스플레이의 왼쪽 상단 (0,0)을 기준으로 텍스트를 배치합니다.

        Args:
            pos_x (int, optional): 텍스트의 가로 위치를 **픽셀(px) 단위로** 설정합니다.
                                기본값은 0입니다.

                                - 값이 양수이면 기준점에서 오른쪽으로 이동합니다. (예: pos_x=10은 오른쪽으로 10픽셀 이동)

                                - 값이 음수이면 기준점에서 왼쪽으로 이동합니다. (예: pos_x=-10은 왼쪽으로 10픽셀 이동)

            pos_y (int, optional): 텍스트의 세로 위치를 **픽셀(px) 단위로** 설정합니다.
                                기본값은 0입니다.

                                - 값이 양수이면 기준점에서 아래쪽으로 이동합니다. (예: pos_y=10은 아래쪽으로 10픽셀 이동)

                                - 값이 음수이면 기준점에서 위쪽으로 이동합니다. (예: pos_y=-10은 위쪽으로 10픽셀 이동)
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.display_text_pos(10, 10) # 텍스트를 왼쪽 상단에서 오른쪽으로 10픽셀, 아래로 10픽셀 이동
            >>> zumiAI.display_text_pos(-5, 20) # 텍스트를 왼쪽으로 5픽셀, 아래로 20픽셀 이동
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



    # def _get_req_datas(self):
    #     """
    #     _get_req_datas
    #     """
    #     return self._connection_handler._get_req_datas()

    def get_zumi_face_detection(self) -> list:
        """
        주미가 자체 얼굴 감지 기능을 통해 감지된 얼굴 정보를 가져옵니다.

        이 함수는 set_zumi_face_detection() 함수로 얼굴 감지 기능을 활성화했을 때
        사용할 수 있습니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 얼굴 정보를 포함하는 리스트를 반환합니다:
                - **감지 여부 (int)**: 얼굴 감지 여부 (0: 미감지, 1: 감지됨)
                - **x축 위치 (int)**: 감지된 얼굴의 중심 x 좌표 (감지된 경우에만 유효)
                - **y축 위치 (int)**: 감지된 얼굴의 중심 y 좌표 (감지된 경우에만 유효)

        Examples:
            >>> face_info = zumiAI.get_zumi_face_detection()
            >>> print(face_info)
            [1, 60, 80] # 예시 출력: 얼굴이 감지되었고, 중심 x=60, y=80 위치
            >>> print(face_info)
            [0, 0, 0]   # 예시 출력: 얼굴이 감지되지 않음
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_FACE)

    def get_zumi_color_detection(self) -> list:
        """
        주미의 자체 색상 감지 기능을 통해 감지된 색상 정보를 가져옵니다.

        이 함수는 set_zumi_color_detection() 함수로 색상 감지 기능을 활성화했을 때
        사용할 수 있습니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 색상 정보를 포함하는 리스트를 반환합니다:
                - **감지된 색상 ID (int)**: 감지된 색상의 고유 ID (0~7).
                                        색상이 감지되지 않은 경우 254를 반환합니다.
                                        (각 ID에 해당하는 색상 정보는 관련 문서를 참조하십시오.)
                - **x축 위치 (int)**: 감지된 색상 영역의 중심 x 좌표 (감지된 경우에만 유효)
                - **y축 위치 (int)**: 감지된 색상 영역의 중심 y 좌표 (감지된 경우에만 유효)

        Examples:
            >>> color_info = zumiAI.get_zumi_color_detection()
            >>> print(color_info)
            [1, 80, 100] # 예시 출력: ID 1번 색상(예: 빨강)이 감지되었고, 중심 x=80, y=100 위치
            >>> print(color_info)
            [254, 0, 0] # 예시 출력: 색상이 감지되지 않음

        Note:
            색상 ID 리스트 (추가 예정)
        """
        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_COLOR)

    def get_zumi_marker_detection(self) -> list:
        """
        주미의 자체 마커 감지 기능을 통해 감지된 마커 정보를 가져옵니다.

        이 함수는 set_zumi_marker_detection() 함수로 마커 감지 기능을 활성화했을 때
        사용할 수 있습니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 마커 정보를 포함하는 리스트를 반환합니다:
                - **감지된 마커 ID (int)**: 감지된 마커의 고유 ID. 마커가 감지되지 않은 경우 254를 반환합니다.
                - **x축 위치 (int)**: 감지된 마커의 중심 x 좌표 (감지된 경우에만 유효)
                - **y축 위치 (int)**: 감지된 마커의 중심 y 좌표 (감지된 경우에만 유효)

        Examples:
            >>> marker_info = zumiAI.get_zumi_marker_detection()
            >>> print(marker_info)
            [5, 90, 110] # 예시 출력: ID 5번 마커가 감지되었고, 중심 x=90, y=110 위치
            >>> print(marker_info)
            [254, 0, 0] # 예시 출력: 마커가 감지되지 않음

        Note:
            마커 ID 리스트 (추가 예정)
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_MARKER)

    def get_zumi_cat_detection(self) -> list:
        """
        주미가 자체 고양이 감지 기능을 통해 감지된 고양이 정보를 가져옵니다.

        이 함수는 set_zumi_cat_detection() 함수로 고양이 감지 기능을 활성화했을 때
        사용할 수 있습니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 고양이 정보를 포함하는 리스트를 반환합니다:
                - **감지 여부 (int)**: 고양이 감지 여부 (0: 미감지, 1: 감지됨)
                - **x축 위치 (int)**: 감지된 고양이의 중심 x 좌표 (감지된 경우에만 유효)
                - **y축 위치 (int)**: 감지된 고양이의 중심 y 좌표 (감지된 경우에만 유효)

        Examples:
            >>> cat_info = zumiAI.get_zumi_cat_detection()
            >>> print(cat_info)
            [1, 70, 90] # 예시 출력: 고양이가 감지되었고, 중심 x=70, y=90 위치
            >>> print(cat_info)
            [0, 0, 0]   # 예시 출력: 고양이가 감지되지 않음
        """
        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_CAT)

    def get_button(self) -> int:
        """
        주미에 있는 4개의 버튼 중 현재 눌린 버튼의 값을 가져옵니다.

        Args:
            없음

        Returns:
            int: 눌린 버튼에 해당하는 정수 값.
                - 0: 누른 버튼 없음
                - 1: 빨간 버튼 눌림
                - 2: 파란 버튼 눌림
                - 4: 초록 버튼 눌림
                - 8: 노란 버튼 눌림

        Examples:
            >>> pressed_button = zumiAI.get_button()
            >>> print(pressed_button)
            1 # 예시 출력: 빨간 버튼이 눌렸을 경우
        """

        return self._connection_handler._get_btn_data()

    def get_battery(self) -> int:
        """
        주미의 현재 배터리 잔량을 퍼센트(%) 값으로 가져옵니다.

        Args:
            없음

        Returns:
            int: 배터리 잔량을 나타내는 정수 값 (0~100%).

        Examples:
            >>> battery = zumiAI.get_battery()
            >>> print(battery)
            75 # 예시 출력: 75%
        """

        return self._connection_handler._get_battery_data()

    def set_calibration_motors(self):
        """
        주미의 모터를 보정하여 정확한 움직임을 수행할 수 있도록 합니다.

        모터의 움직임을 사용하는 명령에 영향을 줍니다.
        (한번만 실행하면 설정 값이 계속 저장됩니다.)

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.


        Examples:
            >>> zumiAI.set_calibration_motors()
            주미의 모터 보정을 시작합니다.

        Note:
            모터 보정 절차:

            1. 주미를 평평한 곳에 눕혀주세요.

            2. 이 명령을 실행합니다.

            3. 보정이 완료될 때까지 잠시 기다려주세요. (약간의 시간이 소요될 수 있습니다.)

            작동 영상 참고 <https://www.naver.com/>

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
                p_exe = self._connection_handler._get_PSTAT_data()
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
    def camera_stream_start(self):
        """
        주미가 카메라 영상 스트리밍을 시작합니다.

        이 함수는 주미가 카메라 영상을 컴퓨터로 실시간 전송하여,
        사용자가 PC 화면에서 주미의 시야를 확인하거나 영상 처리를 할 수 있도록 합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Note:
            이 기능은 주미에서 직접 실행되는 얼굴/색상/마커 감지 기능과 다릅니다.
            전송된 영상은 PC에서 별도의 이미지 처리 라이브러리(예: OpenCV)를 사용하여 분석할 수 있습니다.

        Examples:
            >>> zumiAI.camera_stream_start()
            # 이제 주미의 카메라 영상이 PC로 스트리밍되기 시작합니다.
            # (별도의 뷰어 프로그램이나 코드를 통해 영상을 볼 수 있습니다.)
        """

        self._connection_handler._cameraStream()

    # --- vision ---
    def camera_LR_Flip(self, flag: bool):
        """
        주미의 카메라 영상 스트리밍 화면을 좌우로 뒤집습니다.

        이 함수는 주미의 카메라 영상이 컴퓨터로 스트리밍될 때,
        화면을 거울처럼 좌우 반전시키거나 특정 시각적 효과를 위해 사용됩니다.

        Args:
            flag (bool): 화면의 좌우 반전 활성화 여부를 설정합니다.

                        - True: 카메라 영상을 좌우로 뒤집습니다.

                        - False: 카메라 영상을 원래대로 되돌립니다 (좌우 반전 해제).

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_LR_Flip(True)  # 카메라 영상을 좌우로 뒤집습니다.
            >>> zumiAI.camera_LR_Flip(False) # 좌우 반전 기능을 해제하고 원래대로 되돌립니다.
        """

        self._connection_handler._cameraLeftRightFlip(flag)

    ##--------------------------------------------------------------------#]
    # sensor
    # def sensor_init(self):
    #     """
    #     센서 값을 가져옵니다.
    #     """
    #     self._connection_handler._sensorInit()

    def sensor_start(self):
        """
        주미의 다양한 내장 센서에서 데이터를 읽는 기능을 시작합니다.

        이 함수는 주미의 IR 센서, 버튼, 배터리 등 여러 센서의 데이터를
        주기적으로 가져올 수 있도록 시스템을 활성화합니다. 센서 값을 사용하기 전에
        이 함수를 반드시 한 번 호출해야 합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Note:
            이 함수를 호출한 후, ``get_IR_sensor_all()``, ``get_battery()``, ``get_button()``
            등과 같은 관련 함수를 사용하여 현재 센서 값들을 가져올 수 있습니다.
            또한, ``sensor_visible()`` 함수를 사용해 스트리밍 카메라 영상에서 센서 값들을 직접 확인할 수도 있습니다.

        Examples:
            >>> zumiAI.sensor_start()
            # 이제 주미의 센서 데이터가 내부적으로 업데이트되기 시작합니다.
            >>> ir_values = zumiAI.get_IR_sensor_all()
            >>> print("현재 IR 센서 값:", ir_values)
        """

        self._connection_handler._sensorStart()

    def sensor_visible(self, flag:bool):
        """
        스트리밍 카메라 영상에서 주미의 센서 값들을 실시간으로 표시합니다.

        이 함수는 주미의 IR 센서, 버튼, 배터리 등 여러 센서의 현재 값들을
        스트리밍 카메라 영상에 출력하여 사용자가 쉽게 확인할 수 있도록 돕습니다.
        주로 센서 데이터 디버깅이나 시각적 확인이 필요할 때 유용합니다.

        Args:
            flag (bool): 센서 값 화면 표시 활성화 여부를 설정합니다.

                        - **True**: 센서 값들을 스트리밍화면에 표시하기 시작합니다.

                        - **False**: 센서 값 표시를 중지하고 화면을 원래대로 되돌립니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.sensor_start()        # 센서 데이터 읽기 시작 (필수)
            >>> zumiAI.sensor_visible(True)  # 주미 화면에 센서 값 표시 시작
            # 이제 주미의 디스플레이에 센서 값들이 실시간으로 나타납니다.
            >>> # 원하는 작업을 수행한 후
            >>> zumiAI.sensor_visible(False) # 센서 값 표시 중지
        """

        self._connection_handler._sensorVisible(flag)


    # fps
    def frame_rate_visible(self, flag:bool):
        """
        주미의 PC 스트리밍 카메라 영상의 프레임 속도(FPS) 정보를 표시합니다.

        이 함수는 주미의 카메라 영상이 컴퓨터로 실시간 스트리밍될 때,
        PC 화면에 표시되는 영상의 현재 프레임 속도를 시각적으로 보여줍니다.
        주로 스트리밍 성능을 확인하거나 영상 처리 속도를 디버깅할 때 유용합니다.

        Args:
            flag (bool): 스트리밍 영상의 프레임 속도 정보 화면 표시 활성화 여부를 설정합니다.

                        - **True**: PC 화면에 프레임 속도 정보(FPS)를 표시하기 시작합니다.

                        - **False**: 프레임 속도 정보 표시를 중지합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작 (필수)
            >>> zumiAI.frame_rate_visible(True) # PC 화면에 스트리밍 영상의 프레임 속도 표시 시작
            # 이제 PC 화면의 스트리밍 영상 위에 현재 FPS가 실시간으로 나타납니다.
            >>> # 원하는 작업을 수행한 후
            >>> zumiAI.frame_rate_visible(False) # 프레임 속도 표시 중지
        """
        self._connection_handler._frameRateVisible(flag)

    ##--------------------------------------------------------------------#

    # face
    def face_detector_init(self, face_recognize_threshold = 0.8):
        """
        얼굴 인식 기능을 초기화
        """
        self._connection_handler._faceDetectorInit(face_recognize_threshold)

    def face_detector_start(self):
        """
        얼굴 인식 기능을 시작
        """
        self._connection_handler._faceDetectorStart()

    def face_detector_stop(self):
        """
        얼굴 인식 기능을 종료
        """
        self._connection_handler._faceDetectorStop()

    def is_face_detected(self,name:str="Unknown"):
        """
        카메라에 입력한 이름을 가진 얼굴이 있는지 반환
        name : 검출할 얼굴의 이름
        """
        return self._connection_handler._isFaceDetected(name)

    def get_detected_face_result(self):
        """
        티처블 모델의 예측 결과 (클래스 이름과 신뢰도 점수)를 반환
        """
        return self._connection_handler._getDetectedFaceResult()

    def get_detected_face_name(self):
        """
        카메라에 확인된 얼굴의 이름을 반환
        현재 인식된 얼굴이 없다면 Unknown를 반환
        """
        return self._connection_handler._getDetectedFaceName()

    def get_detected_face_confidence_score(self):
        """
        카메라에 인식된 얼굴의 신뢰도 점수를 반환
        """
        return self._connection_handler._getDetectedFaceConfidenceScore()

    def get_face_center(self):
        """
        카메라에 인식된 얼굴의 중심 좌표를 반환
        """
        return self._connection_handler._getFaceCenter()

    def get_face_size(self):
        """
        카메라에 인식된 얼굴의 크기를 반환
        """
        return self._connection_handler._getFaceSize()

    def face_landmark_visible(self, flag):
        self._connection_handler._faceLandmarkVisible(flag)

    def face_contours_visible(self, flag):
        self._connection_handler._faceContoursVisible(flag)


    def get_face_landmark(self, landmark=1):
        """
        얼굴의 특정 부위의 좌표를 반환
        LEFT_EYE = 1
        RIGHT_EYE = 2
        LEFT_EYEBROW = 3
        RIGHT_EYEBROW = 4
        NOSE = 5
        MOUTH = 6
        JAW = 7
        """
        if not isinstance(landmark, face_landmark):
            try:
                landmark = face_landmark(landmark)
            except ValueError:
                landmark = face_landmark.NOSE
        return self._connection_handler._getFaceLandmark(landmark)

    def face_train(self,name:str):
        """
        얼굴 학습 모드
        키보드의 z키를 누르면 얼굴을 학습합니다.
        키도드의 e키를 누르면 종료합니다.
        name : 등록할 얼굴의 이름
        """
        self._connection_handler._faceTrain(name)

    def delete_face_data(self, name:str):
        """
        등록된 얼굴중 입력한 이름의 데이터 삭제
        name : 삭제할 얼굴의 이름
        """
        self._connection_handler._deleteFaceData(name)

    def delete_all_Face_data(self):
        """
        등록된 모든 얼굴의 데이터 삭제
        """
        self._connection_handler._deleteAllFaceData()

    ##--------------------------------------------------------------------#
    # april
    def marker_detector_init(self):
        """
        마커 인식 기능을 초기화
        """
        self._connection_handler._aprilDetectorInit()

    def marker_detector_start(self):
        """
        마커 인식 기능을 시작
        """
        self._connection_handler._aprilDetectorStart()

    def marker_detector_stop(self):
        """
        마커 인식 기능을 종료
        """
        self._connection_handler._aprildetectorStop()

    def is_marker_detected(self,id:int):
        """
        카메라에 입력한 ID의 마커가 있는지 반환
        nId : 검출할 마커 아이디
        """
        return self._connection_handler._isMarkerDetected(id)

# 마커의 동시 인식에 따른 가져오는 값을 수정해야 함
    def get_marker_id(self):
        """
        카메라에 확인된 마커의 ID를 반환
        """
        return self._connection_handler._getAprilId()

    def get_marker_center(self):
        """
        카메라에 인식된 마커의 중심 좌표를 반환
        """
        return self._connection_handler._getAprilCenter()

    def get_marker_size(self):
        """
        카메라에 인식된 마커의 중심 좌표를 반환
        """
        return self._connection_handler._getAprilSize()

    ##--------------------------------------------------------------------#]
    # gesture

    def gesture_detector_init(self):
        """
        제스처 인식 기능을 초기화
        """
        self._connection_handler._gestureDetectorInit()

    def gesture_detector_start(self):
        """
        제스처 인식 기능을 시작
        """
        self._connection_handler._gestureDetectorStart()

    def gesture_detector_stop(self):
        """
        제스처 인식 기능을 종료
        """
        self._connection_handler._gestureDetectorStop()

    def is_gesture_detected(self):
        """
        카메라에 손이 감지되었는지 확인
        """
        return self._connection_handler._isGestureDetected()

    def get_gesture_finger(self):
        """
        손가락이 펴져 있는지 접혀 있는지 확인
        Args:
            hand_landmarks: MediaPipe에서 감지된 손 랜드마크 객체 (예: results.multi_hand_landmarks[0])
            hand_type_label (str): 'Left' 또는 'Right' 문자열 (MediaPipe에서 감지된 손의 타입)
        Returns:
            list[int]: [엄지, 검지, 중지, 약지, 새끼] 각 손가락의 상태 (1: 펴짐, 0: 쥐어짐)
        """
        return self._connection_handler._getGestureFinger()

    def get_gesture_recognize(self):
        """
        손가락의 특정 상태에 따른 모션 값 반환
        Returns:
            'fist', 'point', 'open', 'peace', 'standby', 'thumbs_up','None'
        """
        return self._connection_handler._getGestureRecognize()

    def get_gesture_center(self):
        """
        카메라에 인식된 손의 중심 좌표를 반환
        """
        return self._connection_handler._getGestureCenter()

    def get_gesture_size(self):
        """
        카메라에 인식된 손의 크기를 반환
        """
        return self._connection_handler._getGestureSize()

    ##--------------------------------------------------------------------#
    # yolo
    def object_detector_init(self):
        """
        object 인식 기능을 초기화
        """
        self._connection_handler._yoloDetectorInit()

    def object_detector_start(self):
        """
        object 인식 기능을 시작
        """
        self._connection_handler._yoloDetectorStart()

    def object_detector_stop(self):
        """
        object 인식 기능을 종료
        """
        self._connection_handler._yoloDetectorStop()


    def object_check_add_obj(self, obj_name=""):
        """
        object 검출 오브젝트를 추가
        """
        self._connection_handler._yoloCheckAddObj(obj_name)


    def object_check_all_add_obj(self):
        """
        object 모든 검출 오브젝트를 추가
        """
        self._connection_handler._yoloCheckAllAddObj()



    def is_stop_sign_detected(self):
        """
        카메라에 stop sign 이 감지되었는지 확인
        """
        #return self._connection_handler._isStopSignDetected()
        return self._connection_handler._isObjDetected("stop sign")

    def get_stop_sign_center(self):
        """
        카메라에 감지된 stop sign의 중심 좌표
        """
        return self._connection_handler._getObjCenter("stop sign")

    def get_stop_sign_size(self):
        """
        카메라에 감지된 stop sign의 크기
        """
        return self._connection_handler._getObjSize("stop sign")

    def get_stop_sign_confidence(self):
        """
        카메라에 감지된 stop sign의 신뢰도 점수
        """
        return self._connection_handler._getObjConfidence("stop sign")

    def is_traffic_light_detected(self):
        """
        카메라에 신호등이 감지되었는지 확인
        """
       # return self._connection_handler._isTrafficLightDetected()
        return self._connection_handler._isObjDetected("traffic light")

    def get_traffic_light_center(self):
        """
        카메라에 감지된 신호등의 중심 좌표
        """
        return self._connection_handler._getObjCenter("traffic light")

    def get_traffic_light_size(self):
        """
        카메라에 감지된 신호등의 크기
        """
        return self._connection_handler._getObjSize("traffic light")

    def get_traffic_light_color(self):
        """
        카메라에 감지된 신호등의 감지 색상
        return : "RED","GREEN","YELLOW","UNKNOW"
        """
        return self._connection_handler._getTrafficLightColor()

    def get_traffic_light_confidence(self):
        """
        카메라에 감지된 신호등의 신뢰도 점수
        """
        return self._connection_handler._getObjConfidence("traffic light")

    def is_obj_detected(self, name:str):
        """
        카메라에 오브젝트가 감지되었는지 확인
        """
        return self._connection_handler._isObjDetected(name)

    def get_obj_size(self, name:str):
        """
        카메라에 감지된 오브젝트의 크기
        """
        return self._connection_handler._getObjSize(name)

    def get_obj_center(self, name:str):
        """
        카메라에 감지된 오브젝트의 중심 좌표
        """
        return self._connection_handler._getObjCenter(name)

    def get_obj_confidence(self, name:str):
        """
        카메라에 감지된 오브젝트의 신뢰도 점수
        """
        return self._connection_handler._getObjConfidence(name)


    ##--------------------------------------------------------------------#]
    # scketch
    def sketch_detector_init(self):
        """
        스케치 인식 기능을 초기화
        """
        self._connection_handler._sketchDetectorInit()

    def sketch_detector_start(self):
        """
        스케치 인식 기능을 시작
        """
        self._connection_handler._sketchDetectorStart()

    def sketch_detector_stop(self):
        """
        스케치 인식 기능을 종료
        """
        self._connection_handler._sketchDetectorStop()

    def is_sketch_detected(self,name:str="Sketch"):
        """
        카메라에 입력한 스케치가 있는지 반환
        """
        return self._connection_handler._isSketchDetected(name)

    def sketch_train(self,name:str=""):
        """
        스케치 인식 기능을 학습
        """
        self._connection_handler._sketchTrain(name)

    def delete_sketch_data(self,name:str=""):
        """
        학습된 스케치 데이터를 제거
        """
        self._connection_handler._deleteSketchData(name)

    def delete_all_sketch_data(self):
        """
        학습된 모든 스케치 데이터를 제거
        """
        self._connection_handler._deleteAllSketchData()

    def get_sketch_center(self,name:str="Sketch"):
        """
        카메라에 인식된 스케치의 중심 좌표를 반환
        """
        return self._connection_handler._getSketchCenter(name)

    def get_sketch_size(self,name:str="Sketch"):
        """
        카메라에 인식된 스케치의 중심 좌표를 반환
        """
        return self._connection_handler._getSketchSize(name)

    def get_sketch_result(self,name:str="Sketch"):
        """
        카메라에 인식된 스케치의 결과(스케치 이름과 신뢰도 점수)를 반환
        """
        return self._connection_handler._getSketchResult(name)

    def get_sketch_confidence(self,name:str="Sketch"):
        """
        카메라에 인식된 스케치의 신뢰도 점수를 반환
        """
        return self._connection_handler._getSketchConfidence(name)


    ##--------------------------------------------------------------------#]
    # teachablemachine
    # https://teachablemachine.withgoogle.com/

    def teachable_detector_init(self, model_path = 'model_unquant.tflite', lable_path = 'labels.txt'):
        """
        티처블 머신 인식 기능을 초기화
        """
        self._connection_handler._teachableInit(model_path, lable_path)

    def teachable_detector_start(self):
        """
        티처블 머신 인식 기능을 시작
        """
        self._connection_handler._teachableStart()

    def teachable_detector_stop(self):
        """
        티처블 머신 인식 기능을 종료
        """
        self._connection_handler._teachableStop()

    def get_teachable_result(self):
        """
        티처블 모델의 예측 결과 (클래스 이름과 신뢰도 점수)를 반환
        """
        return self._connection_handler._getTeachableResult()