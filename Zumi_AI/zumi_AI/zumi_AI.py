#serial
import sys
#import serial
import time
#import queue
#from queue import Queue
#from time import sleep
import threading
from threading import Thread
from colorama import Fore, Back, Style
#from serial.tools.list_ports import comports
from pynput import keyboard

import re # 정규 표현식 모듈 임포트

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
#from .socket_class import *



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


class ZumiAI:
    def __init__(self, usePosInterruptKey=False, usePosCheckBackground=True, usePosShowErrorMessage=True, usePosShowLogMessage=False,
                 usePosShowTransferData=False, usePosShowReceiveData=False):
        """
        usePosInterruptKey (bool): 키 인터럽트
        usePosCheckBackground (bool): 시리얼 통신시 수신 데이터 처리
        usePosShowErrorMessage (bool): # 일반 로그
        usePosShowLogMessage (bool):  # 에러 로그
        usePosShowTransferData (bool): # 송신 데이터 로그
        usePosShowReceiveData (bool): # 수신 데이터 로그
        """

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

            #from .socket_class import *
            from .socket_class import WebSocketConnectionHandler

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


        time.sleep(0.5)

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


    def _sendCommand_test(self):
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
        # print(f"받은 인자의 개수: {len(args)}")
        # for arg in args:
        #     print(arg)

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

        print(dir)

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

                * 2: LED가 두 번 깜박입니다. (0.1 ~ 0.3초의 값을 사용)

                * 3: LED가 점점 밝아졌다가 어두워집니다.

                * 4: LED가 점점 어두워집니다.

                * 5: LED가 점점 밝아집니다.

                * 6: LED 색상이 무지개색으로 변합니다.

            time (int): 패턴의 간격 시간 (단위: 초)

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.led_pattern(1, 1)
            주미의 LED를 1초 마다 깜박이게 합니다.
            >>> zumiAI.led_pattern(6, 0.5)
            주미의 LED 색상을 0.5초 마다 무지개색으로 변화시킵니다.
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

        print(pattern)

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
            #사운드 목록
                0 : 고양이 울음소리

                1 : 카메라 셔터

                2 : 실패음1

                3 : 실패음2

                4 : 경적1

                5 : 경적2

                6 : 사이렌

                7 : 성공

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

    def set_zumi_color_detection(self, enable: bool = False): # int를 bool로 변경, 기본값도 False로 변경
        """
        주미의 내장 색상 감지 기능을 켜거나 끕니다.

        이 함수는 주미 AI 하드웨어 자체에서 색상을 인식하는 기능을
        활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (bool, optional): 색상 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 **False** (비활성화)입니다.
                                    - **True**: 내장 색상 감지 기능을 활성화합니다.
                                    - **False**: 내장 색상 감지 기능을 비활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_color_detection(True)  # 주미의 내장 색상 감지 기능 켜기
            >>> zumiAI.set_zumi_color_detection(False) # 주미의 내장 색상 감지 기능 끄기
            >>> zumiAI.set_zumi_color_detection()   # 기본값인 끄기(비활성화)로 설정
        """
        if enable:
            self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)


    def set_zumi_face_detection(self, enable: bool = False): # int를 bool로 변경, 기본값도 False로 변경
        """
        주미의 내장 얼굴 감지 기능을 켜거나 끕니다.

        이 함수는 주미 AI 하드웨어 자체에서 사람의 얼굴을 인식하는 기능을
        활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (bool, optional): 얼굴 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 **False** (비활성화)입니다.
                                    - **True**: 온보드 얼굴 감지 기능을 활성화합니다.
                                    - **False**: 온보드 얼굴 감지 기능을 비활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_face_detection(True) # 주미의 내장 얼굴 감지 기능 켜기
            >>> zumiAI.set_zumi_face_detection(False) # 주미의 내장 얼굴 감지 기능 끄기
            >>> zumiAI.set_zumi_face_detection()  # 기본값인 끄기(비활성화)로 설정
        """

        if enable:
            self.set_request(RequestType.REQUEST_ENTRY_FACE_DETECT)
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_FACE_DETECT)

    def set_zumi_cat_detection(self, enable: bool = False): # int를 bool로 변경, 기본값도 False로 변경
        """
        주미의 내장 고양이 감지 기능을 켜거나 끕니다.

        이 함수는 주미 AI 하드웨어 자체에서 고양이를 인식하는 기능을
        활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (bool, optional): 고양이 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 **False** (비활성화)입니다.
                                    - **True**: 온보드 고양이 감지 기능을 활성화합니다.
                                    - **False**: 온보드 고양이 감지 기능을 비활성화합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_cat_detection(True)  # 주미의 내장 고양이 감지 기능 켜기
            >>> zumiAI.set_zumi_cat_detection(False) # 주미의 내장 고양이 감지 기능 끄기
            >>> zumiAI.set_zumi_cat_detection()   # 기본값인 끄기(비활성화)로 설정
        """
        if enable: # bool 타입이므로 바로 조건으로 사용 가능
            self.set_request(RequestType.REQUEST_ENTRY_CAT_DETECT) # 실제 로직에 맞게 수정
        else:
            self.clear_request(RequestType.REQUEST_ENTRY_CAT_DETECT) # 실제 로직에 맞게 수정

    def set_zumi_marker_detection(self, enable: bool = False): # int를 bool로 변경, 기본값도 False로 변경
        """
        주미의 내장 마커 감지 기능을 켜거나 끕니다.

        이 함수는 주미 AI 하드웨어 자체에서 마커를 인식하는 기능을
        활성화하거나 비활성화하는 데 사용됩니다.

        Args:
            enable (bool, optional): 마커 감지 기능의 활성화 여부를 설정합니다.
                                    기본값은 **False** (비활성화)입니다.
                                    - **True**: 내장 마커 감지 기능을 활성화합니다.
                                    - **False**: 내장 마커 감지 기능을 비활성화합니다.
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.set_zumi_marker_detection(True)  # 주미의 내장 마커 감지 기능 켜기
            >>> zumiAI.set_zumi_marker_detection(False) # 주미의 내장 마커 감지 기능 끄기
            >>> zumiAI.set_zumi_marker_detection()   # 기본값인 끄기(비활성화)로 설정
        """
        if enable:
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


    def show_camera(self):
        """
        주미의 디스플레이에 카메라 피드를 표시합니다.
        """
        return self.sendCommand(CommandType.COMMAND_SCREEN_TOGGLE, 1)


    def show_emotions(self):
        """
        주미의 디스플레이에 표정을 표시합니다.
        """
        return self.sendCommand(CommandType.COMMAND_SCREEN_TOGGLE, 2)


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



    def is_zumi_face_detected(self) -> bool:
        """
        주미의 내장 얼굴 감지 기능을 통해 얼굴이 감지되었는지 확인합니다.

        이 함수는 `set_zumi_face_detection()` 함수로 얼굴 감지 기능을 활성화했을 때
        사용할 수 있습니다. 얼굴이 감지되면 True를, 감지되지 않으면 False를 반환합니다.

        Args:
            없음

        Returns:
            bool: 얼굴이 감지되었는지 여부를 나타내는 불리언(True/False) 값.
                - **True**: 주미의 시야에서 얼굴이 감지됨
                - **False**: 주미의 시야에서 얼굴이 감지되지 않음

        Examples:
            >>> zumiAI.set_zumi_face_detection(True) # 얼굴 감지 기능 활성화
            >>> face_detected = zumiAI.is_zumi_face_detected()
            >>> print(f"얼굴 감지 여부: {face_detected}")
            얼굴 감지 여부: True # 예시 출력: 얼굴이 감지된 경우
            >>> print(f"얼굴 감지 여부: {face_detected}")
            얼굴 감지 여부: False # 예시 출력: 얼굴이 감지되지 않은 경우
        """
        return bool(self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_FACE))


    def get_zumi_face_center(self) -> list:
        """
        주미의 내장 얼굴 감지 기능을 통해 감지된 얼굴의 중심 좌표를 가져옵니다.

        이 함수는 `set_zumi_face_detection()` 함수로 얼굴 감지 기능을 활성화했을 때
        사용할 수 있습니다. 얼굴이 감지되면 해당 얼굴의 중심 x, y 좌표를 반환합니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 얼굴의 중심 좌표를 포함하는 리스트를 반환합니다:
                - **x축 위치 (int)**: 감지된 얼굴의 중심 x 좌표. (얼굴이 감지되지 않았다면 0)
                - **y축 위치 (int)**: 감지된 얼굴의 중심 y 좌표. (얼굴이 감지되지 않았다면 0)

        Examples:
            >>> zumiAI.set_zumi_face_detection(True) # 얼굴 감지 기능 활성화
            >>> face_center = zumiAI.get_zumi_face_center()
            >>> print(f"감지된 얼굴 중심 좌표: {face_center}")
            감지된 얼굴 중심 좌표: [60, 80] # 예시 출력: x=60, y=80 위치에서 얼굴 감지됨
            >>> print(f"감지된 얼굴 중심 좌표: {face_center}")
            감지된 얼굴 중심 좌표: [0, 0] # 예시 출력: 얼굴이 감지되지 않음
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_FACE_X)



    def is_zumi_cat_detected(self) -> bool:
        """
        주미의 내장 고양이 감지 기능을 통해 고양이가 감지되었는지 확인합니다.

        이 함수는 `set_zumi_cat_detection()` 함수로 고양이 감지 기능을 활성화했을 때
        사용할 수 있습니다. 고양이가 감지되면 True를, 감지되지 않으면 False를 반환합니다.

        Args:
            없음

        Returns:
            bool: 고양이가 감지되었는지 여부를 나타내는 불리언(True/False) 값.
                - **True**: 주미의 시야에서 고양이가 감지됨
                - **False**: 주미의 시야에서 고양이가 감지되지 않음

        Examples:
            >>> zumiAI.set_zumi_cat_detection(True) # 고양이 감지 기능 활성화
            >>> cat_detected = zumiAI.is_zumi_cat_detected()
            >>> print(f"고양이 감지 여부: {cat_detected}")
            고양이 감지 여부: True # 예시 출력: 고양이가 감지된 경우
            >>> print(f"고양이 감지 여부: {cat_detected}")
            고양이 감지 여부: False # 예시 출력: 고양이가 감지되지 않은 경우
        """
        return bool(self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_CAT))


    def get_zumi_cat_center(self) -> list:
        """
        주미의 내장 고양이 감지 기능을 통해 감지된 고양이의 중심 좌표를 가져옵니다.

        이 함수는 `set_zumi_cat_detection()` 함수로 고양이 감지 기능을 활성화했을 때
        사용할 수 있습니다. 고양이가 감지되면 해당 고양이의 중심 x, y 좌표를 반환합니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 고양이의 중심 좌표를 포함하는 리스트를 반환합니다:
                - **x축 위치 (int)**: 감지된 고양이의 중심 x 좌표. (고양이가 감지되지 않았다면 0)
                - **y축 위치 (int)**: 감지된 고양이의 중심 y 좌표. (고양이가 감지되지 않았다면 0)

        Examples:
            >>> zumiAI.set_zumi_cat_detection(True) # 고양이 감지 기능 활성화
            >>> cat_center = zumiAI.get_zumi_cat_center()
            >>> print(f"감지된 고양이 중심 좌표: {cat_center}")
            감지된 고양이 중심 좌표: [70, 90] # 예시 출력: x=70, y=90 위치에서 고양이 감지됨
            >>> print(f"감지된 고양이 중심 좌표: {cat_center}")
            감지된 고양이 중심 좌표: [0, 0] # 예시 출력: 고양이가 감지되지 않음
        """
        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_CAT_X)


    def get_zumi_color_id(self) -> int:
        """
        주미의 내장 색상 감지 기능을 통해 현재 감지된 색상의 ID를 가져옵니다.

        이 함수는 `set_zumi_color_detection()` 함수로 색상 감지 기능을 활성화했을 때
        사용할 수 있습니다. 주미의 카메라 시야에 특정 색상이 감지되면 해당 색상의 고유 ID를 반환하며,
        감지된 색상이 없으면 특정 값을 반환합니다.

        Args:
            없음

        Returns:
            int: 감지된 색상의 고유 ID를 나타내는 정수.
                - **0~7**: 감지된 색상의 ID.
                - **254**: 감지된 색상이 없는 경우.

        Examples:
            >>> zumiAI.set_zumi_color_detection(True) # 색상 감지 기능 활성화
            >>> detected_id = zumiAI.get_zumi_color_id()
            >>> print(f"감지된 색상 ID: {detected_id}")
            감지된 색상 ID: 3 # 예시 출력: ID 3번 색상 감지됨
            >>> print(f"감지된 색상 ID: {detected_id}")
            감지된 색상 ID: 254 # 예시 출력: 감지된 색상 없음

        Note:
            #색상 ID 리스트
                1 : 빨강
                2 : 주황
                3 : 노랑
                4: 녹색
                5: 하늘색
                6: 파랑색
                7 : 보라색
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_COLOR)


    def get_zumi_color_center(self) -> list:
        """
        주미의 내장 색상 감지 기능을 통해 감지된 색상 영역의 중심 좌표를 가져옵니다.

        이 함수는 `set_zumi_color_detection()` 함수로 색상 감지 기능을 활성화했을 때
        사용할 수 있습니다. 색상이 감지되면 해당 색상 영역의 중심 x, y 좌표를 반환합니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 색상 영역의 중심 좌표를 포함하는 리스트를 반환합니다:
                - **x축 위치 (int)**: 감지된 색상 영역의 중심 x 좌표. (색상이 감지되지 않았다면 0)
                - **y축 위치 (int)**: 감지된 색상 영역의 중심 y 좌표. (색상이 감지되지 않았다면 0)

        Examples:
            >>> zumiAI.set_zumi_color_detection(True) # 색상 감지 기능 활성화
            >>> color_center = zumiAI.get_zumi_color_center()
            >>> print(f"감지된 색상 중심 좌표: {color_center}")
            감지된 색상 중심 좌표: [80, 100] # 예시 출력: x=80, y=100 위치에서 색상 감지됨
            >>> print(f"감지된 색상 중심 좌표: {color_center}")
            감지된 색상 중심 좌표: [0, 0] # 예시 출력: 색상이 감지되지 않음
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_COLOR_X)



    def get_zumi_marker_id(self) -> int:
        """
        주미의 내장 마커 감지 기능을 통해 현재 감지된 마커의 ID를 가져옵니다.

        이 함수는 `set_zumi_marker_detection()` 함수로 마커 감지 기능을 활성화했을 때
        사용할 수 있습니다. 주미의 카메라 시야에 특정 마커가 감지되면 해당 마커의 고유 ID를 반환하며,
        감지된 마커가 없으면 특정 값을 반환합니다.

        Args:
            없음

        Returns:
            int: 감지된 마커의 고유 ID를 나타내는 정수.
                - **0~253**: 감지된 마커의 ID.
                - **254**: 감지된 마커가 없는 경우.

        Examples:
            >>> zumiAI.set_zumi_marker_detection(True) # 마커 감지 기능 활성화
            >>> detected_id = zumiAI.get_zumi_marker_id()
            >>> print(f"감지된 마커 ID: {detected_id}")
            감지된 마커 ID: 5 # 예시 출력: ID 5번 마커 감지됨
            >>> print(f"감지된 마커 ID: {detected_id}")
            감지된 마커 ID: 254 # 예시 출력: 감지된 마커 없음

        Note:
            마커 ID 리스트 (추가 예정)
        """
        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_MARKER)


    def get_zumi_marker_center(self) -> list:
        """
        주미의 내장 마커 감지 기능을 통해 감지된 마커의 중심 좌표를 가져옵니다.

        이 함수는 `set_zumi_marker_detection()` 함수로 마커 감지 기능을 활성화했을 때
        사용할 수 있습니다. 마커가 감지되면 해당 마커의 중심 x, y 좌표를 반환합니다.

        Args:
            없음

        Returns:
            list: 다음 순서로 감지된 마커의 중심 좌표를 포함하는 리스트를 반환합니다:
                - **x축 위치 (int)**: 감지된 마커의 중심 x 좌표. (마커가 감지되지 않았다면 0)
                - **y축 위치 (int)**: 감지된 마커의 중심 y 좌표. (마커가 감지되지 않았다면 0)

        Examples:
            >>> zumiAI.set_zumi_marker_detection(True) # 마커 감지 기능 활성화
            >>> marker_center = zumiAI.get_zumi_marker_center()
            >>> print(f"감지된 마커 중심 좌표: {marker_center}")
            감지된 마커 중심 좌표: [90, 110] # 예시 출력: x=90, y=110 위치에서 마커 감지됨
            >>> print(f"감지된 마커 중심 좌표: {marker_center}")
            감지된 마커 중심 좌표: [0, 0] # 예시 출력: 마커가 감지되지 않음
        """

        return self._connection_handler._get_detect_data(PacketDataIndex.DATA_DETECT_MARKER_X)







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

        self.display_text_set(1,5)
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


    ##--------------------------------------------------------------------#
    ##--------------------------------------------------------------------#
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

        Examples:
            >>> zumiAI.camera_stream_start()
            # 이제 주미의 카메라 영상이 PC로 스트리밍되기 시작합니다.
            # (별도의 뷰어 프로그램이나 코드를 통해 영상을 볼 수 있습니다.)

        Note:
            이 기능은 주미에서 직접 실행되는 얼굴/색상/마커 감지 기능과 다릅니다.
            전송된 영상은 PC에서 별도의 이미지 처리 라이브러리(예: OpenCV)를 사용하여 분석할 수 있습니다.
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
        주미의 다양한 센서에서 데이터를 읽는 기능을 시작합니다.

        IP 연결 모드에서는 센서 값을 기본적으로 가져오지 않으므로, 센서 값을 사용하기 전에
        이 함수를 반드시 한 번 호출해야 합니다.

        이 함수는 주미의 IR 센서, 버튼, 배터리 등의 데이터를
        주기적으로 가져올 수 있도록 시스템을 활성화합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.sensor_start()
            # 이제 주미의 센서 데이터가 내부적으로 업데이트되기 시작합니다.
            >>> ir_values = zumiAI.get_IR_sensor_all()
            >>> print("현재 IR 센서 값:", ir_values)

        Note:
            이 함수를 호출한 후, ``get_IR_sensor_all()``, ``get_battery()``, ``get_button()``
            등과 같은 관련 함수를 사용하여 현재 센서 값들을 가져올 수 있습니다.
            또한, ``sensor_visible()`` 함수를 사용해 스트리밍 카메라 영상에서 센서 값들을 직접 확인할 수도 있습니다.
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

                        - **True**: 센서 값들을 스트리밍 화면에 표시하기 시작합니다.

                        - **False**: 센서 값 표시를 중지합니다.

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
        스트리밍 카메라 영상의 프레임 속도(FPS) 정보를 표시합니다.

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
        스트리밍되는 카메라 영상에서 얼굴 인식 기능을 초기화합니다.

        이 함수는 주미에서 PC로 전송되는 실시간 영상 스트림을 사용하여
        컴퓨터에서 사람의 얼굴을 인식할 수 있도록 필요한 설정과 리소스(예: 얼굴 인식 모델)를 준비합니다.
        얼굴 인식은 단순히 얼굴이 감지되는 것을 넘어, 학습된 특정 얼굴을 구별하는 기능입니다.

        Args:
            face_recognize_threshold (float, optional): 얼굴 인식의 정확도 임계값을 설정합니다.
                                                        기본값은 0.8이며, 0.0부터 1.0 사이의 값을 가집니다.

                                                        - **값이 높을수록**: 더 엄격한 기준으로 얼굴을 비교하여 오인식률은 낮아지지만, 인식 성공률이 떨어질 수 있습니다.

                                                        - **값이 낮을수록**: 좀 더 관대한 기준으로 얼굴을 비교하여 인식 성공률은 높아지지만, 오인식률이 증가할 수 있습니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 먼저 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init() # 기본 임계값 0.8로 PC 기반 얼굴 인식 기능 초기화
            >>> zumiAI.face_detector_init(face_recognize_threshold=0.7) # 임계값을 0.7로 설정하여 초기화
            >>> zumiAI.face_detector_start() # 얼굴 인식 시작
            # ... 얼굴 인식 로직 ...
            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 얼굴 인식을 사용하기 전에 ``camera_stream_start()`` 함수를 호출하여 영상 스트리밍을 시작해야 합니다.
            - 이 함수로 초기화한 후, ``face_detector_start()`` 함수를 호출해야 실제로 얼굴 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 얼굴 감지/인식 기능과는 다릅니다.
        """

        self._connection_handler._faceDetectorInit(face_recognize_threshold)


    def face_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 얼굴 인식 기능을 시작합니다.

        이 함수를 호출하면 주미의 카메라 영상이 PC로 스트리밍될 때,
        영상 내에서 인식된 얼굴이 자동으로 감지되고 다음과 같이 화면에 표시됩니다:

        - **사각형 테두리**: 감지된 얼굴 주변에 사각형 테두리가 그려집니다.

        - **등록된 이름**: 만약 등록된 얼굴이라면 해당 이름이 표시됩니다.

        - **신뢰도**: 얼굴 인식의 신뢰도(정확도)가 숫자로 표시됩니다.

        - **중심 좌표 및 크기**: 인식된 얼굴의 중앙 x, y 좌표 및 크기 정보가 함께 표시될 수 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 기능 초기화 (선택 사항, 임계값 설정 가능)
            >>> zumiAI.face_detector_start()  # PC 화면에서 얼굴 인식 및 시각화 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 얼굴 정보가 표시됩니다.
            >>> # ... 얼굴 인식을 사용하는 로직 ...
            >>> zumiAI.face_detector_stop()   # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``face_detector_init()`` 로 얼굴 인식 기능을 초기화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 얼굴 감지/인식 기능과는 다릅니다.
        """

        self._connection_handler._faceDetectorStart()


    def face_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 얼굴 인식 기능을 중지합니다.

        이 함수는 ``face_detector_start()`` 함수로 시작된 얼굴 인식 프로세스와
        관련된 시각화(사각형 테두리, 이름, 신뢰도 등) 및 데이터 처리를 모두 종료합니다.
        더 이상 얼굴 인식이 필요하지 않을 때 호출하여 시스템 자원을 해제합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 기능 초기화
            >>> zumiAI.face_detector_start()  # PC 화면에서 얼굴 인식 시작
            # ... 얼굴 인식을 사용하는 로직 ...
            >>> zumiAI.face_detector_stop()   # 얼굴 인식 중지
            # 이제 PC 화면에서 얼굴 인식 관련 표시가 사라지고, 자원이 해제됩니다.

        Note:
            - 얼굴 인식 기능을 다시 사용하려면 ``face_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 얼굴 감지/인식 기능과는 다릅니다.
        """

        self._connection_handler._faceDetectorStop()


    def is_face_detected(self,name:str="Unknown") -> bool:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 얼굴이 감지되었는지 확인합니다.

        이 함수는 ``face_detector_start()`` 로 시작된 얼굴 인식 기능이 활성화된 상태에서,
        PC 화면에 스트리밍되는 영상에 지정된 name을 가진 얼굴이 있는지 여부를 반환합니다.

        Args:
            name (str, optional): 감지 여부를 확인할 등록된 얼굴의 이름.
                                기본값은 "Unknown"이며, 이 경우 '알 수 없는' 또는
                                '등록되지 않은' 얼굴의 감지 여부를 확인합니다.

        Returns:
            bool: 지정된 name을 가진 얼굴이 영상에서 감지되었는지 여부.
                - **True**: 해당 이름의 얼굴이 현재 영상에서 감지되었습니다.
                - **False**: 해당 이름의 얼굴이 현재 영상에서 감지되지 않았습니다.

        Examples:
            >>> zumiAI.camera_stream_start()
            >>> zumiAI.face_detector_init()
            >>> zumiAI.face_detector_start()
            >>>
            >>> # '학생1'이라는 이름의 얼굴이 감지되었는지 확인
            >>> detected_student = zumiAI.is_face_detected(name="학생1")
            >>> print(f"'학생1' 감지 여부: {detected_student}")
            '학생1' 감지 여부: True # 예시 출력: '학생1' 얼굴이 감지됨

            >>> # 'Unknown'(알 수 없는) 얼굴이 감지되었는지 확인
            >>> detected_unknown = zumiAI.is_face_detected() # 또는 is_face_detected("Unknown")
            >>> print(f"알 수 없는 얼굴 감지 여부: {detected_unknown}")
            알 수 없는 얼굴 감지 여부: False # 예시 출력: 알 수 없는 얼굴이 감지되지 않음

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._isFaceDetected(name)


    def get_detected_face_result(self) -> tuple:
        """
            스트리밍되는 카메라 영상에서 인식된 얼굴의 이름과 신뢰도 점수를 가져옵니다.

            이 함수는 ``face_detector_start()`` 함수로 얼굴 인식이 활성화된 상태에서
            현재 스트리밍 영상에 인식된 얼굴이 있다면, 가장 크게 감지된 얼굴이름과
            해당 이름에 대한 신뢰도 점수를 튜플 형태로 반환합니다.

            Args:
                없음

            Returns:
                tuple: 얼굴의 이름과 신뢰도 점수를 담은 튜플.

                    - **[0] 이름 (str)**: 인식된 얼굴의 이름 (예: "학생1"). 얼굴이 인식되지 않았다면 "Unknown" 또는 마지막으로 인식된 이름이 반환될 수 있습니다.

                    - **[1] 신뢰도 점수 (float)**: 해당 이름에 대한 신뢰도 점수 (0.00 ~ 1.00). 얼굴이 인식되지 않았다면 0.00이 반환될 수 있습니다.

                    예시: `("학생1", 0.95)`

            Examples:
                >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
                >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
                >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

                >>> while True:
                >>>     name, score = zumiAI.get_detected_face_result()
                >>>     if name != "Unknown" and score > 0.5: # Unknown이 아니며 신뢰도가 0.5보다 높을 때
                >>>         print(f"인식된 얼굴: {name}, 신뢰도: {score:.2f}")
                >>>     else:
                >>>         print("얼굴 인식 대기 중...")
                >>>     time.sleep(1) # 1초 대기

                >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

            Note:
                - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
                - face_recognize_threshold 값에 따라 신뢰도 점수가 달라질 수 있습니다.
                - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
            """

        return self._connection_handler._getDetectedFaceResult()


    def get_detected_face_name(self) -> str:
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 얼굴의 이름을 가져옵니다.

        이 함수는 ``face_detector_start()`` 함수로 얼굴 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 인식된 얼굴이 있다면 해당 얼굴의 등록된 이름을 반환합니다.
        만약 인식된 얼굴이 없거나 등록되지 않은 얼굴이라면 "Unknown"을 반환합니다.

        Args:
            없음

        Returns:
            str: 인식된 얼굴의 이름.
                - **등록된 이름 (str)**: 얼굴이 성공적으로 인식된 경우.
                - **"Unknown" (str)**: 얼굴이 인식되지 않았거나, 등록되지 않은 얼굴인 경우.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> while True:
            >>>     face_name = zumiAI.get_detected_face_name()
            >>>     if face_name != "Unknown":
            >>>         print(f"인식된 얼굴: {face_name}")
            >>>     else:
            >>>         print("얼굴 인식 대기 중... (알 수 없는 얼굴)")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getDetectedFaceName()


    def get_detected_face_confidence_score(self) -> float:
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 얼굴의 신뢰도 점수를 가져옵니다.

        이 함수는 ``face_detector_start()`` 함수로 얼굴 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 인식된 얼굴이 있다면 해당 얼굴이 얼마나 정확하게 인식되었는지 나타내는
        신뢰도 점수(0.00 ~ 1.00 사이의 값)를 반환합니다. 점수가 높을수록 더욱 확실하게 인식되었다는 의미입니다.

        Args:
            없음

        Returns:
            float: 인식된 얼굴의 신뢰도 점수 (0.00 ~ 1.00).
                얼굴이 인식되지 않았거나 등록되지 않은 얼굴인 경우 0.00이 반환될 수 있습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> while True:
            >>>     score = zumiAI.get_detected_face_confidence_score()
            >>>     if score > 0.7: # 신뢰도 점수가 0.7보다 높을 때
            >>>         print(f"얼굴 인식 신뢰도: {score:.2f} (높음)")
            >>>     elif score > 0.4:
            >>>         print(f"얼굴 인식 신뢰도: {score:.2f} (보통)")
            >>>     else:
            >>>         print(f"얼굴 인식 신뢰도: {score:.2f} (낮거나 인식 안 됨)")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - ``face_detector_init()`` 함수에서 설정한 ``face_recognize_threshold`` 값에 따라 인식 결과와 신뢰도 점수의 해석이 달라질 수 있습니다.
            - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getDetectedFaceConfidenceScore()


    def get_face_center(self) -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 얼굴의 중심 좌표를 가져옵니다.

        이 함수는 ``face_detector_start()`` 함수로 얼굴 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 얼굴이 인식되었다면, 가장 크게 감지된 얼굴의 중심이 되는
        x, y 좌표를 리스트 형태로 반환합니다.

        Args:
            없음

        Returns:
            list: 인식된 얼굴의 중심 x, y 좌표를 담은 리스트.
                - **[0] x축 위치 (int)**: 인식된 얼굴의 중심 x 좌표.
                - **[1] y축 위치 (int)**: 인식된 얼굴의 중심 y 좌표.

                얼굴이 인식되지 않았다면 `[0, 0]`을 반환할 수 있습니다. 예시: `[0, 0]` (스트리밍 화면의 중앙)


        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> while True:
            >>>     center_x, center_y = zumiAI.get_face_center()
            >>>     if center_x != 0 or center_y != 0: # 얼굴이 감지되어 유효한 좌표가 반환된 경우
            >>>         print(f"얼굴 중심 좌표: X={center_x}, Y={center_y}")
            >>>     else:
            >>>         print("얼굴 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 반환되는 좌표는 스트리밍 영상 화면의 크기(해상도)에 따라 달라질 수 있습니다.
            - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getFaceCenter()


    def get_face_size(self) -> int:
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 얼굴의 크기를 가져옵니다.

        이 함수는 ``face_detector_start()`` 함수로 얼굴 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 얼굴이 인식되었다면, 가장 크게 감지된 얼굴의 크기를
        숫자(픽셀 또는 상대적인 값)로 반환합니다. 이 값으로 얼굴이 화면에서 얼마나
        크게 보이는지 알 수 있습니다.

        Args:
            없음

        Returns:
            int: 인식된 얼굴의 크기.
                얼굴이 인식되지 않았다면 0을 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> while True:
            >>>     face_size = zumiAI.get_face_size()
            >>>     if face_size > 0: # 얼굴이 감지되어 유효한 크기 값이 반환된 경우
            >>>         print(f"인식된 얼굴 크기: {face_size}")
            >>>         if face_size > 100:
            >>>             print("얼굴이 가까이 있네요!")
            >>>         else:
            >>>             print("얼굴이 조금 멀리 있거나 작게 보이네요.")
            >>>     else:
            >>>         print("얼굴 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 반환되는 크기 값은 스트리밍 영상 화면의 해상도나 얼굴의 거리에 따라 달라질 수 있습니다.
            - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getFaceSize()



    def face_landmark_visible(self, flag:bool):
        """
        스트리밍되는 카메라 영상에 인식된 얼굴의 주요 랜드마크(특징점)를 표시합니다.

        이 함수를 호출하면 ``face_detector_start()`` 로 얼굴 인식이 활성화된 상태에서,
        스트리밍 영상에 인식된 얼굴 위에 다음과 같은 7가지 주요 특징점들이 표시됩니다:

        왼쪽 눈, 오른쪽 눈, 왼쪽 눈썹, 오른쪽 눈썹, 코, 입, 턱

        이 기능은 얼굴의 세부적인 움직임이나 특징을 시각적으로 확인하는 데 유용합니다.

        Args:
            flag (bool): 얼굴 랜드마크 표시 활성화 여부를 설정합니다.

                        - **True**: 스트리밍 영상에 얼굴 랜드마크를 표시하기 시작합니다.

                        - **False**: 얼굴 랜드마크 표시를 중지합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> zumiAI.face_landmark_visible(True) # 스트리밍 영상에 얼굴 랜드마크 표시 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 얼굴 위에 랜드마크가 나타납니다.
            >>> # ... 얼굴 랜드마크를 관찰하는 로직 ...
            >>> zumiAI.face_landmark_visible(False) # 얼굴 랜드마크 표시 중지

            >>> zumiAI.face_detector_stop() # 얼굴 인식 종료 (필요 시)

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
            - ``face_landmark_visible()`` 함수와 함께 사용하면 얼굴 특징점과 윤곽선을 동시에 볼 수 있습니다.
        """

        self._connection_handler._faceLandmarkVisible(flag)

    def face_contours_visible(self, flag:bool):
        """
        스트리밍되는 카메라 영상에 인식된 얼굴의 윤곽선을 표시합니다.

        이 함수를 호출하면 ``face_detector_start()`` 로 얼굴 인식이 활성화된 상태에서,
        스트리밍 영상에 인식된 얼굴 위에 얼굴의 주요 특징점을 연결한 파란색 윤곽선이 그려집니다.
        이는 얼굴의 형태와 움직임을 시각적으로 파악하는 데 유용합니다.

        Args:
            flag (bool): 얼굴 윤곽선 표시 활성화 여부를 설정합니다.

                        - **True**: 스트리밍 영상에 얼굴 윤곽선을 표시하기 시작합니다.

                        - **False**: 얼굴 윤곽선 표시를 중지합니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> zumiAI.face_contours_visible(True) # 스트리밍 영상에 얼굴 윤곽선 표시 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 얼굴 위에 파란색 윤곽선이 나타납니다.
            >>> # ... 얼굴 윤곽선을 관찰하는 로직 ...
            >>> zumiAI.face_contours_visible(False) # 얼굴 윤곽선 표시 중지

            >>> zumiAI.face_detector_stop() # 얼굴 인식 종료 (필요 시)

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
            - ``face_landmark_visible()`` 함수와 함께 사용하면 얼굴 특징점과 윤곽선을 동시에 볼 수 있습니다.
        """

        self._connection_handler._faceContoursVisible(flag)


    def get_face_landmark(self, landmark=1) -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 얼굴의 특정 랜드마크(특징점) 중심 좌표를 가져옵니다.

        이 함수는 `face_detector_start()`` 로 얼굴 인식이 활성화된 상태에서,
        스트리밍 영상에 인식된 얼굴의 지정된 랜드마크(예: 왼쪽 눈, 코)의 x, y 좌표를 리스트 형태로 반환합니다.
        이를 통해 얼굴 각 부분의 위치를 프로그램에서 활용할 수 있습니다.

        Args:
            landmark (int or face_landmark, optional): 좌표를 가져올 얼굴 랜드마크의 ID 또는 이름.
                                                    기본값은 `1` (왼쪽 눈)입니다.
                                                    다음 값들을 사용할 수 있습니다:

                                                    - **1 (face_landmark.LEFT_EYE)**: 왼쪽 눈

                                                    - **2 (face_landmark.RIGHT_EYE)**: 오른쪽 눈

                                                    - **3 (face_landmark.LEFT_EYEBROW)**: 왼쪽 눈썹

                                                    - **4 (face_landmark.RIGHT_EYEBROW)**: 오른쪽 눈썹

                                                    - **5 (face_landmark.NOSE)**: 코

                                                    - **6 (face_landmark.MOUTH)**: 입

                                                    - **7 (face_landmark.JAW)**: 턱

                                                    잘못된 값이 입력되면 자동으로 코(`face_landmark.NOSE`)의 좌표를 반환합니다.

        Returns:
            list: 선택된 얼굴 랜드마크의 중심 x, y 좌표를 담은 리스트.
                - **[0] x축 위치 (int)**: 랜드마크의 중심 x 좌표.
                - **[1] y축 위치 (int)**: 랜드마크의 중심 y 좌표.

                얼굴이 인식되지 않았다면 `[0, 0]`을 반환할 수 있습니다. 예시: `[150, 110]` (선택된 랜드마크의 화면 상 위치)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.face_detector_init()   # 얼굴 인식 초기화
            >>> zumiAI.face_detector_start()  # 얼굴 인식 시작

            >>> # 코의 중심 좌표 가져오기
            >>> nose_x, nose_y = zumiAI.get_face_landmark(landmark=5) # 또는 zumiAI.get_face_landmark(face_landmark.NOSE)
            >>> print(f"코의 중심 좌표: X={nose_x}, Y={nose_y}")

            >>> # 왼쪽 눈의 중심 좌표 가져오기
            >>> left_eye_x, left_eye_y = zumiAI.get_face_landmark(landmark=face_landmark.LEFT_EYE)
            >>> print(f"왼쪽 눈의 중심 좌표: X={left_eye_x}, Y={left_eye_y}")

            >>> zumiAI.face_detector_stop() # 얼굴 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()``, ``face_detector_init()``, 그리고 ``face_detector_start()`` 함수를 순서대로 호출하여 스트리밍 및 얼굴 인식 기능을 활성화해야 합니다.
            - 반환되는 좌표는 스트리밍 영상 화면의 크기(해상도)에 따라 달라질 수 있습니다.
            - 이 함수는 한 번에 하나의 얼굴(가장 크게 감지된 얼굴)에 대한 정보만 반환합니다.
        """
        if not isinstance(landmark, face_landmark):
            try:
                landmark = face_landmark(landmark)
            except ValueError:
                landmark = face_landmark.NOSE
        return self._connection_handler._getFaceLandmark(landmark)


    def face_train(self,name:str):
        """
        스트리밍되는 카메라 영상에서 새로운 얼굴을 학습시키고 등록합니다.

        이 함수를 호출하면 주미의 카메라 영상이 PC로 스트리밍되는 화면에서
        얼굴 학습 모드가 활성화됩니다. 이 모드에서는 키보드 입력을 통해
        얼굴을 학습시키고 저장할 수 있습니다.

        Args:
            name (str): 등록할 얼굴의 이름. 학습된 얼굴은 이 이름으로 저장됩니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 카메라 스트리밍 시작 (필수)
            >>> print("학습할 이름을 입력하세요 (예: '철수', '영희'):")
            >>> user_name = input()
            >>> zumiAI.face_train(name=user_name) # 입력된 이름으로 얼굴 학습 모드 시작
            # 이제 PC 화면을 보면서 'r'키를 눌러 얼굴을 학습하고 'e'키로 종료하세요.
            >>> print(f"'{user_name}' 얼굴 학습 모드가 종료되었습니다.")
            # 학습된 얼굴은 이제 'face_detector_start()'로 인식될 수 있습니다.

        Note:
            - **학습 과정**:
                1. ``face_train()`` 함수를 실행하면 얼굴 학습 모드가 시작됩니다.
                2. 화면에 얼굴이 인식된 상태에서 `r` 키를 누르면 현재 화면에 있는 얼굴이 한 장씩 캡처되어 학습됩니다.
                3. 얼굴이 인식되지 않은 상태에서 `r` 키를 누르면 학습되지 않으므로, 얼굴이 화면에 잘 보이도록 한 후 여러 번 `r` 키를 눌러 다양한 각도와 표정으로 학습시키는 것이 좋습니다.
                4. 충분히 학습되었다고 판단되면 `e` 키를 눌러 학습 모드를 종료합니다.

            - 학습된 얼굴 정보는 자동으로 저장되어 다음에 주미를 시작할 때 자동으로 불러와져 인식에 사용됩니다.
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._faceTrain(name)


    def delete_face_data(self, name:str):
        """
        스트리밍되는 카메라 영상에서 학습된 특정 이름의 얼굴 데이터를 삭제합니다.

        이 함수는 ``face_train()`` 함수를 통해 이전에 학습하고 저장했던 얼굴 데이터 중에서,
        지정된 name과 일치하는 얼굴 정보를 인식 시스템에서 완전히 지웁니다.
        더 이상 특정 얼굴을 인식하고 싶지 않을 때 사용합니다.

        Args:
            name (str): 삭제할 얼굴 데이터의 이름. 정확한 이름을 입력해야 해당 데이터가 삭제됩니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 'jay'라는 이름의 얼굴 데이터 삭제
            >>> zumiAI.delete_face_data(name="jay")
            >>> print("'jay' 얼굴 데이터가 삭제되었습니다.")

            >>> # 'may'라는 이름의 얼굴 데이터 삭제
            >>> zumiAI.delete_face_data(name="may")
            >>> print("'may' 얼굴 데이터 삭제를 시도했습니다.")

        Note:
            - 이 함수는 영구적으로 얼굴 데이터를 삭제합니다. 삭제된 데이터는 복구할 수 없습니다.
            - 삭제하려는 이름이 시스템에 등록되어 있지 않으면 아무런 작업도 수행되지 않습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.

        """
        self._connection_handler._deleteFaceData(name)


    def delete_all_Face_data(self):
        """
        스트리밍되는 카메라 영상에서 학습된 모든 얼굴 데이터를 삭제합니다.

        이 함수는 ``face_train()`` 함수를 통해 이전에 학습하고 저장했던
        모든 얼굴 인식 데이터를 인식 시스템에서 완전히 지웁니다.
        주미의 얼굴 인식 기록을 초기화하고 싶을 때 사용합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 저장된 모든 얼굴 데이터 삭제
            >>> zumiAI.delete_all_Face_data()
            >>> print("모든 얼굴 데이터가 삭제되었습니다.")
            # 이제 주미는 학습된 어떤 얼굴도 인식하지 못하게 됩니다.

        Note:
            - **이 작업은 되돌릴 수 없습니다!** 모든 학습된 얼굴 데이터가 영구적으로 삭제되니 신중하게 사용해 주세요.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._deleteAllFaceData()


    ##--------------------------------------------------------------------#
    # april
    def marker_detector_init(self):
        """
        스트리밍되는 카메라 영상에서 마커 인식 기능을 초기화합니다.

        이 함수는 주미에서 PC로 전송되는 실시간 영상 스트림을 사용하여
        컴퓨터에서 특수 제작된 마커(apriltag)를 인식할 수 있도록
        필요한 설정과 리소스(예: 인식 모델)를 준비합니다.
        마커 인식은 주미의 위치나 주변 환경을 파악하는 데 유용하게 활용될 수 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 먼저 카메라 스트리밍 시작
            >>> zumiAI.marker_detector_init() # PC 기반 마커 인식 기능 초기화
            >>> zumiAI.marker_detector_start() # 마커 인식 시작
            # ... 마커 인식 로직 ...
            >>> zumiAI.marker_detector_stop() # 마커 인식 중지

        Note:
            - 마커 인식을 사용하기 전에 ``camera_stream_start()`` 함수를 호출하여 영상 스트리밍을 시작해야 합니다.
            - 이 함수로 초기화한 후, ``marker_detector_start()`` 함수를 호출해야 실제로 마커 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 마커 감지 기능과는 다릅니다.
        """

        self._connection_handler._aprilDetectorInit()


    def marker_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 마커 인식 기능을 시작합니다.

        이 함수를 호출하면 주미의 카메라 영상이 PC로 스트리밍될 때,
        영상 내에서 특수 제작된 마커(apriltag)가 자동으로 감지되고
        다음과 같이 화면에 표시됩니다:

        - **윤곽선 표시**: 감지된 마커 주변에 윤곽선이 그려집니다.

        - **ID 표시**: 각 마커의 고유 ID가 표시됩니다.

        - **중심점**: 마커의 중심 좌표가 표시됩니다.

        - **크기**: 마커의 크기 정보가 표시됩니다.

        이후 ``is_marker_detected()``, ``get_marker_id()``, ``get_marker_center()``, ``get_marker_size()`` 와 같은 관련 함수를 사용하여 인식된 마커의 다양한 정보를 프로그램 내에서 가져올 수도 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.marker_detector_init() # 마커 인식 기능 초기화
            >>> zumiAI.marker_detector_start() # PC 화면에서 마커 인식 및 시각화 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 마커 정보가 표시됩니다.
            >>> # ... 마커 인식을 사용하는 로직 ...
            >>> zumiAI.marker_detector_stop() # 마커 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``marker_detector_init()`` 로 마커 인식 기능을 초기화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 마커 감지 기능과는 다릅니다.
        """

        self._connection_handler._aprilDetectorStart()

    def marker_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 마커 인식 기능을 중지합니다.

        이 함수는 ``marker_detector_start()`` 함수로 시작된 마커 인식 프로세스와
        관련된 시각화(윤곽선, ID, 중심점, 크기 등) 및 데이터 처리를 모두 종료합니다.
        더 이상 마커 인식이 필요하지 않을 때 호출하여 시스템 자원을 해제합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.marker_detector_init() # 마커 인식 기능 초기화
            >>> zumiAI.marker_detector_start() # PC 화면에서 마커 인식 시작
            # ... 마커 인식을 사용하는 로직 ...
            >>> zumiAI.marker_detector_stop() # 마커 인식 중지
            # 이제 PC 화면에서 마커 인식 관련 표시가 사라지고, 자원이 해제됩니다.

        Note:
            - 마커 인식 기능을 다시 사용하려면 ``marker_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 마커 감지 기능과는 다릅니다.
        """

        self._connection_handler._aprildetectorStop()

    def is_marker_detected(self,id:int) -> bool:
        """
        스트리밍되는 카메라 영상에서 특정 ID의 마커가 감지되었는지 확인합니다.

        이 함수는 ``marker_detector_start()`` 로 마커 인식이 활성화된 상태에서,
        PC 화면에 스트리밍되는 영상에 지정된 id를 가진 마커가 있는지 여부를 불리언(True/False) 값으로 반환합니다.

        Args:
            id (int): 감지 여부를 확인할 마커의 고유 ID.

        Returns:
            bool: 지정된 id를 가진 마커가 현재 영상에서 감지되었는지 여부.

                - **True**: 해당 ID의 마커가 현재 영상에서 감지되었습니다.

                - **False**: 해당 ID의 마커가 현재 영상에서 감지되지 않았습니다.

        Examples:
            >>> zumiAI.camera_stream_start()
            >>> zumiAI.marker_detector_init()
            >>> zumiAI.marker_detector_start()
            >>>
            >>> # ID가 100인 마커가 감지되었는지 확인
            >>> detected_marker_100 = zumiAI.is_marker_detected(id=100)
            >>> print(f"ID 100 마커 감지 여부: {detected_marker_100}")
            ID 100 마커 감지 여부: True # 예시 출력: ID 100 마커가 감지됨

            >>> # ID가 200인 마커가 감지되었는지 확인
            >>> detected_marker_200 = zumiAI.is_marker_detected(id=200)
            >>> print(f"ID 200 마커 감지 여부: {detected_marker_200}")
            ID 200 마커 감지 여부: False # 예시 출력: ID 200 마커가 감지되지 않음

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``marker_detector_init()`` 로 마커 인식 기능을 초기화한 후, ``marker_detector_start()`` 를 호출하여 마커 인식을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 마커 감지 기능과는 다릅니다.
        """
        return self._connection_handler._isMarkerDetected(id)





# 마커의 동시 인식에 따른 가져오는 값을 수정해야 함

    def get_marker_id(self):
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 마커의 ID를 가져옵니다.

        이 함수는 ``marker_detector_start()`` 함수로 마커 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 마커가 인식되었다면 마커의 고유 ID를 정수 형태로 반환합니다.
        이를 통해 주미가 어떤 마커를 보고 있는지 확인할 수 있습니다.

        Args:
            없음

        Returns:
            int: 인식된 마커의 고유 ID.
                마커가 인식되지 않았다면 -1 을 반환합니다.
                예시: 1 (ID가 1인 마커가 감지됨)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.marker_detector_init() # 마커 인식 초기화
            >>> zumiAI.marker_detector_start() # 마커 인식 시작

            >>> while True:
            >>>     marker_id = zumiAI.get_marker_id()
            >>>     if marker_id != -1: # 마커가 감지된 경우
            >>>         print(f"감지된 마커 ID: {marker_id}")
            >>>         if marker_id == 1:
            >>>             print("목표 마커를 찾았습니다!")
            >>>     else:
            >>>         print("마커 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.marker_detector_stop() # 마커 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``marker_detector_init()`` 로 마커 인식 기능을 초기화한 후, ``marker_detector_start()`` 를 호출하여 마커 인식을 활성화해야 합니다.
            - 이 함수는 한 번에 하나의 마커에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getAprilId()


    def get_marker_center(self) -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 첫 번째 마커의 중심 좌표를 가져옵니다.

        이 함수는 ``marker_detector_start()`` 함수로 마커 인식이 활성화된 상태에서,
        현재 스트리밍 영상에 마커가 인식되었다면 마커의 중심이 되는
        x, y 좌표를 리스트 형태로 반환합니다. 이를 통해 주미가 마커를 화면의 어느 위치에서 보고 있는지 알 수 있습니다.

        Args:
            없음

        Returns:
            list: 인식된 마커의 중심 x, y 좌표를 담은 리스트.

                - **[0] x축 위치 (int)**: 마커의 중심 x 좌표.

                - **[1] y축 위치 (int)**: 마커의 중심 y 좌표.

                마커가 인식되지 않았다면 `[0, 0]`을 반환합니다. 예시: `[0, 0]` (스트리밍 화면의 중앙)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.marker_detector_init() # 마커 인식 초기화
            >>> zumiAI.marker_detector_start() # 마커 인식 시작

            >>> while True:
            >>>     center_x, center_y = zumiAI.get_marker_center()
            >>>     if center_x != -1 or center_y != -1: # 마커가 감지되어 유효한 좌표가 반환된 경우
            >>>         print(f"마커 중심 좌표: X={center_x}, Y={center_y}")
            >>>     else:
            >>>         print("마커 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.marker_detector_stop() # 마커 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``marker_detector_init()`` 로 마커 인식 기능을 초기화한 후, ``marker_detector_start()`` 를 호출하여 마커 인식을 활성화해야 합니다.
            - 반환되는 좌표는 스트리밍 영상 화면의 크기(해상도)에 따라 달라질 수 있습니다.
            - 이 함수는 한 번에 하나의 마커에 대한 정보만 반환합니다.
        """

        return self._connection_handler._getAprilCenter()


    def get_marker_size(self) -> int:
        """
            스트리밍되는 카메라 영상에서 인식된 첫 번째 마커의 크기를 가져옵니다.

            이 함수는 ``marker_detector_start()`` 함수로 마커 인식이 활성화된 상태에서,
            현재 스트리밍 영상에 마커가 인식되었다면 가장 크게 감지된 마커의 크기를
            숫자(픽셀 또는 상대적인 값)로 반환합니다. 이 값을 통해 마커가 화면에서 얼마나
            크게 보이는지, 즉 주미와의 거리가 어느 정도인지 예측하는 데 사용할 수 있습니다.

            Args:
                없음

            Returns:
                int: 인식된 마커의 크기.
                    마커가 인식되지 않았다면 0을 반환합니다.

            Examples:
                >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
                >>> zumiAI.marker_detector_init() # 마커 인식 초기화
                >>> zumiAI.marker_detector_start() # 마커 인식 시작

                >>> while True:
                >>>     marker_size = zumiAI.get_marker_size()
                >>>     if marker_size != -1: # 마커가 감지되어 유효한 크기 값이 반환된 경우
                >>>         print(f"인식된 마커 크기: {marker_size}")
                >>>         if marker_size > 150:
                >>>             print("마커가 가까이 있네요!")
                >>>         else:
                >>>             print("마커가 조금 멀리 있거나 작게 보이네요.")
                >>>     else:
                >>>         print("마커 감지 대기 중...")
                >>>     time.sleep(1) # 1초 대기

                >>> zumiAI.marker_detector_stop() # 마커 인식 중지

            Note:
                - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``marker_detector_init()`` 로 마커 인식 기능을 초기화한 후, ``marker_detector_start()`` 를 호출하여 마커 인식을 활성화해야 합니다.
                - 반환되는 크기 값은 스트리밍 영상 화면의 해상도나 마커의 실제 크기, 주미와의 거리에 따라 달라질 수 있습니다.
                - 이 함수는 한 번에 하나의 마커에 대한 정보만 반환합니다.
            """
        return self._connection_handler._getAprilSize()

    ##--------------------------------------------------------------------#]
    # gesture

    def gesture_detector_init(self):
        """
        스트리밍되는 카메라 영상에서 손 제스처 인식 기능을 초기화합니다.

        이 함수는 주미에서 PC로 전송되는 실시간 영상 스트림을 사용하여
        컴퓨터에서 사용자의 손 제스처를 인식할 수 있도록 필요한 설정과 리소스를 준비합니다.
        이 초기화 과정을 통해 주미는 한 손의 움직임이나 형태를 분석하여 특정 제스처로 판단할 수 있게 됩니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 먼저 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # PC 기반 손 제스처 인식 기능 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작
            # ... 손 제스처 인식 로직 ...
            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수는 내부적으로 손 인식 모델을 설정합니다.
            - 손 감지 및 추적의 최소 신뢰도(min_detection_confidence, min_tracking_confidence)는 0.5로 설정됩니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.
            - 이 함수로 초기화한 후, ``gesture_detector_start()`` 함수를 호출해야 실제로 제스처 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._gestureDetectorInit()


    def gesture_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 손 제스처 인식 기능을 시작합니다.

        이 함수를 호출하면 주미의 카메라 영상이 PC로 스트리밍될 때,
        영상 내에서 인식된 손과 제스처 정보가 자동으로 감지되고 다음과 같이 화면에 표시됩니다:

        - **손 랜드마크**: 인식된 손 위에 여러 특징점(관절, 손가락 끝 등)이 표시됩니다.

        - **손 중심점**: 손의 중심 x, y 좌표가 표시됩니다.

        - **손 크기**: 손의 크기 정보가 표시됩니다.

        - **손가락 상태**: 각 손가락(엄지부터 새끼손가락까지)이 굽혀졌는지(0) 펴졌는지(1)를 나타내는 5개의 숫자로 된 리스트(예: `[0, 1, 0, 0, 0]`)가 표시됩니다.

        - **인식된 제스처**: 인식된 손 모션에 따라 다음과 같은 제스처 이름이 화면에 표시됩니다:
            - `fist` (주먹): 모든 손가락이 굽혀진 상태 (`[0, 0, 0, 0, 0]`)

            - `point` (가리키기): 검지 손가락만 펴진 상태 (`[0, 1, 0, 0, 0]`)

            - `open` (손바닥 펴기): 모든 손가락이 펴진 상태 (`[1, 1, 1, 1, 1]`)

            - `peace` (브이): 검지와 중지 손가락이 펴진 상태 (`[0, 1, 1, 0, 0]`)

            - `standby` (엄지 제외 펴기): 엄지손가락만 굽혀진 상태 (`[1, 1, 0, 0, 0]`)

            - `thumbs_up` (엄지척): 엄지손가락만 펴진 상태 (`[1, 0, 0, 0, 0]`)

            - `None` (인식 불가): 위에 해당하지 않는 모든 제스처

        이후 ``is_gesture_detected()`` , ``get_gesture_center()`` , ``get_gesture_size()`` , ``get_gesture_finger()`` , ``get_gesture_recognize()`` 와 같은 관련 함수를 사용하여
        인식된 손 제스처의 다양한 정보를 프로그램 내에서 가져올 수도 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 기능 초기화
            >>> zumiAI.gesture_detector_start() # PC 화면에서 손 제스처 인식 및 시각화 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 손과 제스처 정보가 표시됩니다.
            >>> # ... 손 제스처 인식을 사용하는 로직 ...
            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 기능과는 다릅니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.
        """

        self._connection_handler._gestureDetectorStart()


    def gesture_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 손 제스처 인식 기능을 중지합니다.

        이 함수는 ``gesture_detector_start()`` 함수로 시작된 손 제스처 인식 프로세스와
        관련된 시각화(손 랜드마크, 중심점, 크기, 손가락 상태 등) 및 데이터 처리를 모두 종료합니다.
        더 이상 손 제스처 인식이 필요하지 않을 때 호출하여 시스템 자원을 해제합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 기능 초기화
            >>> zumiAI.gesture_detector_start() # PC 화면에서 손 제스처 인식 시작
            # ... 손 제스처 인식을 사용하는 로직 ...
            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지
            # 이제 PC 화면에서 손 제스처 인식 관련 표시가 사라지고, 자원이 해제됩니다.

        Note:
            - 손 제스처 인식 기능을 다시 사용하려면 ``gesture_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어에서 처리되는 기능과는 다릅니다.
        """

        self._connection_handler._gestureDetectorStop()

    def is_gesture_detected(self) -> bool:
        """
        스트리밍되는 카메라 영상에 손이 감지되었는지 확인합니다.

        이 함수는 ``gesture_detector_start()`` 함수로 손 제스처 인식이 활성화된 상태에서,
        현재 주미의 카메라 영상에 사람의 손이 화면에 나타났는지 여부를 True 또는 False로 반환합니다.

        Args:
            없음

        Returns:
            bool: 손이 영상에서 감지되었는지 여부.

                - **True**: 손이 현재 영상에 감지되었습니다.

                - **False**: 손이 현재 영상에 감지되지 않았습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작

            >>> while True:
            >>>     if zumiAI.is_gesture_detected():
            >>>         print("손이 감지되었습니다!")
            >>>     else:
            >>>         print("손 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화한 후, ``gesture_detector_start()`` 를 호출하여 손 제스처 인식을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.

        """
        return self._connection_handler._isGestureDetected()

    def get_gesture_finger(self) -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 손의 각 손가락이 펴져 있는지 접혀 있는지 확인합니다.

        이 함수는 ``gesture_detector_start()`` 로 손 제스처 인식이 활성화된 상태에서,
        현재 영상에 감지된 손의 엄지, 검지, 중지, 약지, 새끼손가락의 상태를 리스트 형태로 반환합니다.
        각 손가락은 펴져 있으면 1, 굽혀져(쥐어져) 있으면 0으로 표시됩니다.

        Args:
            없음

        Returns:
            list[int]: [엄지, 검지, 중지, 약지, 새끼] 순서로 각 손가락의 상태를 나타내는 리스트.

                    - **1**: 해당 손가락이 펴진 상태

                    - **0**: 해당 손가락이 굽혀진(쥐어진) 상태

                    손이 감지되지 않았다면 모든 값이 0인 리스트 `[0, 0, 0, 0, 0]`을 반환할 수 있습니다. 예시: `[0, 1, 0, 0, 0]` (검지 손가락만 펴진 상태, 즉 '가리키기')

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작

            >>> while True:
            >>>     finger_status = zumiAI.get_gesture_finger()
            >>>     print(f"손가락 상태 (엄지-새끼): {finger_status}")
            >>>     if finger_status[1] == 1 and finger_status[2] == 1: # 검지와 중지가 펴진 경우 (브이)
            >>>         print("브이(V) 제스처입니다!")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화한 후, ``gesture_detector_start()`` 를 호출하여 손 제스처 인식을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.

        """

        return self._connection_handler._getGestureFinger()

    def get_gesture_recognize(self) -> str:
        """
        스트리밍되는 카메라 영상에서 인식된 손의 제스처 이름을 가져옵니다.

        이 함수는 ``gesture_detector_start()`` 로 손 제스처 인식이 활성화된 상태에서,
        현재 영상에 감지된 손의 모양을 분석하여 다음 중 하나의 제스처 이름을 문자열로 반환합니다:

        - **'fist'**: 주먹을 쥐었을 때

        - **'point'**: 검지 손가락만 펴서 무언가를 가리킬 때

        - **'open'**: 손바닥을 활짝 펴서 '하이 파이브'와 같은 자세를 취할 때

        - **'peace'**: 검지와 중지 손가락을 펴서 '브이(V)'자를 만들 때

        - **'standby'**: 엄지손가락만 굽히고 나머지 손가락을 폈을 때

        - **'thumbs_up'**: 엄지손가락만 펴서 '최고'를 나타낼 때

        - **'None'**: 위에 해당하지 않는 다른 모든 손 모양이나 손이 인식되지 않았을 때

        Args:
            없음

        Returns:
            str: 인식된 손 제스처의 이름. 위에 나열된 문자열 중 하나를 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작

            >>> while True:
            >>>     gesture = zumiAI.get_gesture_recognize()
            >>>     if gesture != 'None':
            >>>         print(f"인식된 제스처: {gesture}")
            >>>         if gesture == 'peace':
            >>>             print("평화! 브이(V) 제스처네요!")
            >>>     else:
            >>>         print("제스처 인식 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화한 후, ``gesture_detector_start()`` 를 호출하여 손 제스처 인식을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.
        """
        return self._connection_handler._getGestureRecognize()

    def get_gesture_center(self) -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 손의 중심 좌표를 가져옵니다.

        이 함수는 ``gesture_detector_start()`` 함수로 손 제스처 인식이 활성화된 상태에서,
        현재 영상에 손이 인식되었다면 해당 손의 중심이 되는 x, y 좌표를 리스트 형태로 반환합니다.
        이를 통해 주미가 화면의 어느 위치에서 손을 보고 있는지 알 수 있습니다.

        Args:
            없음

        Returns:
            list: 인식된 손의 중심 x, y 좌표를 담은 리스트.

                - **[0] x축 위치 (int)**: 손의 중심 x 좌표.

                - **[1] y축 위치 (int)**: 손의 중심 y 좌표.

                손이 인식되지 않았다면 `[0, 0]`을 반환할 수 있습니다. 예시: `[0, 0]` (스트리밍 화면의 중앙)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작

            >>> while True:
            >>>     center_x, center_y = zumiAI.get_gesture_center()
            >>>     if center_x != 0 or center_y != 0: # 손이 감지되어 유효한 좌표가 반환된 경우
            >>>         print(f"손 중심 좌표: X={center_x}, Y={center_y}")
            >>>     else:
            >>>         print("손 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화한 후, ``gesture_detector_start()`` 를 호출하여 손 제스처 인식을 활성화해야 합니다.
            - 반환되는 좌표는 스트리밍 영상 화면의 크기(해상도)에 따라 달라질 수 있습니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.

        """
        return self._connection_handler._getGestureCenter()

    def get_gesture_size(self) -> int:
        """
        스트리밍되는 카메라 영상에서 인식된 손의 크기를 가져옵니다.

        이 함수는 ``gesture_detector_start()`` 함수로 손 제스처 인식이 활성화된 상태에서,
        현재 영상에 손이 인식되었다면 해당 손의 크기를 숫자(픽셀 또는 상대적인 값)로 반환합니다.
        이 값을 통해 손이 화면에서 얼마나 크게 보이는지, 즉 주미와의 거리가 어느 정도인지
        예측하는 데 사용할 수 있습니다.

        Args:
            없음

        Returns:
            int: 인식된 손의 크기.
                손이 인식되지 않았다면 0을 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.gesture_detector_init() # 손 제스처 인식 초기화
            >>> zumiAI.gesture_detector_start() # 손 제스처 인식 시작

            >>> while True:
            >>>     hand_size = zumiAI.get_gesture_size()
            >>>     if hand_size > 0: # 손이 감지되어 유효한 크기 값이 반환된 경우
            >>>         print(f"인식된 손 크기: {hand_size}")
            >>>         if hand_size > 150:
            >>>             print("손이 가까이 있네요!")
            >>>         else:
            >>>             print("손이 조금 멀리 있거나 작게 보이네요.")
            >>>     else:
            >>>         print("손 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.gesture_detector_stop() # 손 제스처 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``gesture_detector_init()`` 로 손 제스처 인식 기능을 초기화한 후, ``gesture_detector_start()`` 를 호출하여 손 제스처 인식을 활성화해야 합니다.
            - 반환되는 크기 값은 스트리밍 영상 화면의 해상도나 손의 실제 크기, 주미와의 거리에 따라 달라질 수 있습니다.
            - 한 번에 하나의 손만 인식하도록 설정되어 있습니다.
        """
        return self._connection_handler._getGestureSize()

    ##--------------------------------------------------------------------#
    # yolo
    def object_detector_init(self, performance_mode = "speed"):
        """
        스트리밍되는 카메라 영상에서 물체 인식(Object Detection) 기능을 초기화합니다.

        이 함수는 주미에서 PC로 전송되는 실시간 영상 스트림을 사용하여 컴퓨터가 영상 속에 있는 다양한 물체(예: 사람, 자동차, 의자 등)를 인식할 수 있도록 모델을 준비합니다.
        사용자는 원하는 물체 인식 성능 모드를 선택하여 주미가 얼마나 빠르게 또는 얼마나 정확하게 물체를 인식할지 조절할 수 있습니다.

        Args:
            performance_mode (str, optional): 물체 인식 모델의 성능 모드를 선택합니다.
                                            다음 중 하나의 값을 입력할 수 있습니다:

                                            - **"speed"**: 가장 빠르지만 인식 정확도는 보통 (기본값)

                                            - **"balance"**: 속도와 정확도의 균형

                                            - **"power"**: 느리지만 가장 정확한 인식

                                            입력된 값이 유효하지 않으면 "speed"로 자동 설정됩니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 먼저 카메라 스트리밍 시작

            >>> # 기본값인 "speed" 성능으로 물체 인식 기능 초기화
            >>> zumiAI.object_detector_init()
            >>> print("물체 인식 기능이 'speed' 모드로 초기화되었습니다.")

            >>> # "balance" 성능으로 물체 인식 기능 초기화
            >>> zumiAI.object_detector_init(performance_mode="balance")
            >>> print("물체 인식 기능이 'balance' 모드로 초기화되었습니다.")

            >>> # "power" 성능으로 물체 인식 기능 초기화
            >>> zumiAI.object_detector_init(performance_mode="power")
            >>> print("물체 인식 기능이 'power' 모드로 초기화되었습니다.")

            >>> zumiAI.object_detector_start() # 물체 인식 시작
            # ... 물체 인식 로직 ...
            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 선택한 performance_mode에 따라 다른 모델 파일이 로드됩니다.
            - COCO 데이터셋을 기반으로 학습되었기 때문에, 일상생활에서 흔히 볼 수 있는 약 80가지 종류의 물체를 인식할 수 있습니다.
            - 이 함수로 초기화한 후, ``object_detector_start()`` 함수를 호출해야 실제로 물체 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._yoloDetectorInit(performance_mode)

    def object_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 물체 인식(Object Detection) 기능을 시작합니다.

        이 함수를 호출하면 ``object_detector_init()`` 으로 준비된 모델을 사용하여 주미의 실시간 카메라 영상 속에서 다양한 물체를 인식하기 시작합니다.
        인식된 물체는 화면에 테두리와 함께 이름, 신뢰도(정확도) 등이 표시될 수 있습니다.

        기본적으로 주미는 자율주행에 필요한 다음 물체들을 우선적으로 인식하도록 설정되어 있습니다:

        - **"person"** (사람)

        - **"car"** (자동차)

        - **"bus"** (버스)

        - **"truck"** (트럭)

        - **"traffic light"** (신호등)

        - **"stop sign"** (정지 표지판)

        - **"cat"** (고양이)

        - **"dog"** (개)

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init(performance_mode="balance") # 'balance' 모드로 물체 인식 모델 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작
            # 이제 PC 화면의 스트리밍 영상에서 설정된 물체들이 인식되기 시작합니다.
            >>> # ... 인식 결과를 사용하는 로직 ...
            >>> zumiAI.object_detector_stop() # 물체 인식 중지


        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 모델을 초기화해야 합니다.
            - 기본 인식 목록 외에, 다음 함수들을 사용하여 모델이 인식할 수 있는 다른 물체를 인식하도록 추가하거나, 현재 인식 목록에서 특정 물체를 제거할 수 있습니다:
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.

                - ``object_check_add_obj(obj_name)``: 특정 물체를 인식 목록에 추가합니다.
                - ``object_check_all_add_obj()``: 모든 물체(COCO 데이터셋 80종)를 인식 목록에 추가합니다.
                - ``object_check_del_obj(obj_name)``: 특정 물체를 인식 목록에서 제거합니다.
                - ``object_check_all_del_obj()``: 모든 물체를 인식 목록에서 제거합니다.


                - 사용가능한 리스트 목록은 다음과 같습니다.


                    # 사람 및 동물 (Person and Animals)
                        "사람": "person"

                        "자전거": "bicycle"

                        "오토바이": "motorcycle"

                        "새": "bird"

                        "고양이": "cat"

                        "개": "dog"

                        "말": "horse"

                        "양": "sheep"

                        "소": "cow"

                        "코끼리": "elephant"

                        "곰": "bear"

                        "얼룩말": "zebra"

                        "기린": "giraffe"

                    # 차량 (Vehicles)
                        "자동차": "car"

                        "비행기": "airplane"

                        "버스": "bus"

                        "기차": "train"

                        "트럭": "truck"

                        "보트": "boat"

                    # 야외 및 거리 (Outdoor and Street)
                        "신호등": "traffic light"

                        "소화전": "fire hydrant"

                        "정지 표지판": "stop sign"

                        "주차 미터기": "parking meter"

                        "벤치": "bench"

                    # 악세사리 (Accessories)
                        "배낭": "backpack"

                        "우산": "umbrella"

                        "핸드백": "handbag"

                        "넥타이": "tie"

                        "여행 가방": "suitcase"

                    # 스포츠 용품 (Sports Equipment)
                        "프리스비": "frisbee"

                        "스키": "skis"

                        "스노보드": "snowboard"

                        "스포츠 공": "sports ball"

                        "연": "kite"

                        "야구 배트": "baseball bat"

                        "야구 글러브": "baseball glove"

                        "스케이트보드": "skateboard"

                        "서핑보드": "surfboard"

                        "테니스 라켓": "tennis racket"

                    # 주방 및 식기 (Kitchen and Dining)
                        "병": "bottle"

                        "와인잔": "wine glass"

                        "컵": "cup"

                        "포크": "fork"

                        "칼": "knife"

                        "숟가락": "spoon"

                        "그릇": "bowl"

                    # 음식 (Food)
                        "바나나": "banana"

                        "사과": "apple"

                        "샌드위치": "sandwich"

                        "오렌지": "orange"

                        "브로콜리": "broccoli"

                        "당근": "carrot"

                        "핫도그": "hot dog"

                        "피자": "pizza"

                        "도넛": "donut"

                        "케이크": "cake"

                    # 가구 (Furniture)
                        "의자": "chair

                        "소파": "couch

                        "화분": "potted plant"

                        "침대": "bed"

                        "식탁": "dining table"

                        "변기": "toilet"

                    # 전자제품 및 실내 물품 (Electronics and Indoor Items)

                        "TV": "tv"

                        "노트북": "laptop"

                        "마우스": "mouse"

                        "리모컨": "remote"

                        "키보드": "keyboard"

                        "휴대폰": "cell phone"

                        "전자레인지": "microwave"

                        "오븐": "oven"

                        "토스터": "toaster"

                        "싱크대": "sink"

                        "냉장고": "refrigerator"

                        "책": "book"

                        "시계": "clock"

                        "꽃병": "vase"

                        "가위": "scissors"

                        "테디 베어": "teddy bear"

                        "헤어 드라이어": "hair drier"

                        "칫솔": "toothbrush"

        """

        self._connection_handler._yoloDetectorStart()

    def object_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 물체 인식(Object Detection) 기능을 중지합니다.

        이 함수는 ``object_detector_start()`` 로 시작된 모델 기반의 물체 인식 프로세스를
        종료하고 관련된 리소스(자원)를 해제합니다. 더 이상 주미가 영상 속 물체들을
        인식할 필요가 없을 때 이 함수를 사용합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 모델 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작
            >>> # ... 물체 인식 로직 ...
            >>> zumiAI.object_detector_stop() # 물체 인식 중지
            >>> print("물체 인식 기능이 종료되었습니다.")

        Note:
            - 물체 인식 기능을 다시 사용하려면 ``object_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._yoloDetectorStop()


    def is_obj_detected(self, name:str) -> bool:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 물체가 감지되었는지 확인합니다.

        이 함수는 ``object_detector_start()`` 로 물체 인식이 활성화된 상태에서, 주미의 카메라 영상 속에 지정된 name을 가진 물체(예: "person", "car")가
        화면에 나타났는지 여부를 True 또는 False로 반환합니다.

        Args:
            name (str): 감지 여부를 확인할 물체의 이름.
                        이 이름은 ``object_detector_start()`` 를 통해 인식하도록 설정된 물체 목록(기본 목록 또는 ``object_check_add_obj()``, ``object_check_all_add_obj()`` 로 추가된 물체)에 포함되어야 합니다.
                        (예: "person", "stop sign", "traffic light", "car"등)
                        만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환됩니다.
                        (예: "사람" 입력 시 "person"으로 변환)

        Returns:
            bool: 해당 물체가 영상에서 감지되었는지 여부.
                - **True**: 지정된 name의 물체가 현재 영상에 감지되었습니다.
                - **False**: 지정된 name의 물체가 현재 영상에 감지되지 않았습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작

            >>> print("--- 영어 이름으로 'person' 감지 예시 ---")
            >>> while True:
            >>>     if zumiAI.is_obj_detected(name="person"): # 영어 이름 사용
            >>>         print("사람(person)이 감지되었습니다!")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("사람(person) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> print("--- 한글 이름으로 'car' 감지 예시 ---")
            >>> # KOREAN_TO_ENGLISH_OBJ_MAP이 미리 정의되어 있다고 가정합니다.
            >>> while True:
            >>>     if zumiAI.is_obj_detected(name="자동차"): # 한글 이름 사용
            >>>         print("자동차(car)가 감지되었습니다!")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("자동차(car) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 기능을 초기화한 후, ``object_detector_start()`` 를 호출하여 물체 인식을 활성화해야 합니다.
            - name으로 지정하는 물체 이름은 COCO 데이터셋에 정의된 클래스 이름이어야 합니다. 한글 이름으로 변환해서 사용할 수도 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._isObjDetected(name)

    def get_obj_center(self, name:str) -> tuple:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 물체(객체) 중심 좌표를 가져옵니다.

        이 함수는 ``object_detector_start()`` 로 물체 인식이 활성화된 상태에서, 주미의 카메라 영상 속에서 지정된 name을 가진 물체가 감지되었다면, 해당 물체의 중심이 되는 x, y 좌표를 튜플 형태로 반환합니다.
        만약 같은 이름의 물체가 여러 개 감지되었다면, 가장 먼저 인식된(첫 번째) 물체의 좌표를 알려줍니다.

        Args:
            name (str): 중심 좌표를 조회할 물체의 이름.
                        이 이름은 ``object_detector_start()`` 를 통해 인식하도록 설정된 물체 목록(기본 목록 또는 ``object_check_add_obj()``, ``object_check_all_add_obj()`` 로 추가된 물체)에 포함되어야 합니다.
                        (예: "person", "stop sign", "traffic light", "car"등)
                        만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환됩니다.
                        (예: "사람" 입력 시 "person"으로 변환)

        Returns:
            tuple: 인식된 물체의 중심 좌표 (x, y).

                - **x (int)**: 물체의 중심 x 좌표.

                - **y (int)**: 물체의 중심 y 좌표.

                물체가 인식되지 않았다면 빈 튜플 `()`을 반환합니다. 예시: `(0, 0)` (스트리밍 화면의 중앙)

        Examples:
        >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
        >>> zumiAI.object_detector_init() # 물체 인식 초기화
        >>> zumiAI.object_detector_start() # 물체 인식 시작

        >>> print("--- 영어 이름으로 'person' 감지 예시 ---")
        >>> while True:
        >>>     person_center = zumiAI.get_obj_center(name="person") # 영어 이름 사용
        >>>     if person_center: # 사람이 감지되어 좌표가 반환된 경우
        >>>         center_x, center_y = person_center
        >>>         print(f"사람(person)의 중심 좌표: X={center_x}, Y={center_y}")
        >>>         break # 감지되면 반복 중단
        >>>     else:
        >>>         print("사람(person) 감지 대기 중...")
        >>>     time.sleep(1) # 1초 대기

        >>> print("--- 한글 이름으로 '자동차' 감지 예시 ---")
        >>> # KOREAN_TO_ENGLISH_OBJ_MAP이 미리 정의되어 있다고 가정합니다.
        >>> while True:
        >>>     car_center = zumiAI.get_obj_center(name="자동차") # 한글 이름 사용
        >>>     if car_center: # 자동차가 감지되어 좌표가 반환된 경우
        >>>         center_x, center_y = car_center
        >>>         print(f"자동차(car)의 중심 좌표: X={center_x}, Y={center_y}")
        >>>         break # 감지되면 반복 중단
        >>>     else:
        >>>         print("자동차(car) 감지 대기 중...")
        >>>     time.sleep(1) # 1초 대기

        >>> zumiAI.object_detector_stop() # 물체 인식 중지


        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 기능을 초기화한 후, ``object_detector_start()`` 를 호출하여 물체 인식을 활성화해야 합니다.
            - name으로 지정하는 물체 이름은 COCO 데이터셋에 정의된 클래스 이름이어야 합니다. 한글 이름으로 변환해서 사용할 수도 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getObjCenter(name)


    def get_obj_size(self, name:str) -> int:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 물체(객체) 크기를 가져옵니다.

        이 함수는 ``object_detector_start()`` 로 물체 인식이 활성화된 상태에서,
        주미의 카메라 영상 속에서 지정된 name을 가진 물체가 감지되었다면,
        해당 물체가 화면에서 차지하는 크기(면적)를 숫자로 반환합니다. 이 크기 값을 통해
        물체가 주미로부터 얼마나 멀리 떨어져 있는지 예측하는 데 사용할 수 있습니다.
        만약 같은 이름의 물체가 여러 개 감지되었다면, 가장 먼저 인식된(첫 번째) 물체의 크기를 알려줍니다.

        Args:
            name (str): 크기를 조회할 물체의 이름.
                        이 이름은 ``object_detector_start()`` 를 통해 인식하도록 설정된 물체 목록(기본 목록 또는 ``object_check_add_obj()``, ``object_check_all_add_obj()`` 로 추가된 물체)에 포함되어야 합니다.
                        (예: "person", "stop sign", "traffic light", "car"등)
                        만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환됩니다.
                        (예: "사람" 입력 시 "person"으로 변환)
        Returns:
            int: 인식된 물체의 크기(면적).
                물체가 인식되지 않았다면 0을 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작

            >>> print("--- 영어 이름으로 'car' 크기 감지 예시 ---")
            >>> while True:
            >>>     car_size = zumiAI.get_obj_size(name="car") # 영어 이름 사용
            >>>     if car_size > 0: # 자동차가 감지되어 크기 값이 반환된 경우
            >>>         print(f"자동차(car)의 크기: {car_size}")
            >>>         if car_size > 5000:
            >>>             print("자동차가 가까이 있네요!")
            >>>         else:
            >>>             print("자동차가 조금 멀리 있거나 작게 보이네요.")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("자동차(car) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> print("--- 한글 이름으로 '개' 크기 감지 예시 ---")
            >>> # KOREAN_TO_ENGLISH_OBJ_MAP이 미리 정의되어 있다고 가정합니다.
            >>> while True:
            >>>     dog_size = zumiAI.get_obj_size(name="개") # 한글 이름 사용
            >>>     if dog_size > 0: # 개가 감지되어 크기 값이 반환된 경우
            >>>         print(f"개(dog)의 크기: {dog_size}")
            >>>         if dog_size > 3000:
            >>>             print("개가 가까이 있네요!")
            >>>         else:
            >>>             print("개가 조금 멀리 있거나 작게 보이네요.")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("개(dog) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 기능을 초기화한 후, ``object_detector_start()`` 를 호출하여 물체 인식을 활성화해야 합니다.
            - 반환되는 크기 값은 스트리밍 영상 화면의 해상도나 물체의 실제 크기, 주미와의 거리에 따라 달라질 수 있습니다.
            - name으로 지정하는 물체 이름은 COCO 데이터셋에 정의된 클래스 이름이어야 합니다. 한글 이름으로 변환해서 사용할 수도 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._getObjSize(name)


    def get_obj_confidence(self, name:str)-> float:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 물체(객체)에 대한 신뢰도 점수를 가져옵니다.

        이 함수는 ``object_detector_start()`` 로 물체 인식이 활성화된 상태에서, 주미의 카메라 영상 속에서 지정된 name을 가진 물체가 감지되었다면,
        해당 물체 인식의 정확도(신뢰도)를 0.0(0%)부터 1.0(100%) 사이의 숫자로 반환합니다.
        이 점수를 통해 주미가 해당 물체를 얼마나 확실하게 인식했는지 알 수 있습니다.
        만약 같은 이름의 물체가 여러 개 감지되었다면, 가장 먼저 인식된(첫 번째) 물체의 신뢰도를 알려줍니다.

        Args:
            name (str): 신뢰도 점수를 조회할 물체의 이름.
                        이 이름은 ``object_detector_start()`` 를 통해 인식하도록 설정된 물체 목록(기본 목록 또는 ``object_check_add_obj()``, ``object_check_all_add_obj()`` 로 추가된 물체)에 포함되어야 합니다.
                        (예: "person", "stop sign", "traffic light", "car"등)
                        만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환됩니다.
                        (예: "사람" 입력 시 "person"으로 변환)
        Returns:
            float: 인식된 물체의 신뢰도 점수. 0.0부터 1.0 사이의 값입니다.
                물체가 인식되지 않았다면 0.0을 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작

            >>> print("--- 영어 이름으로 'person' 신뢰도 감지 예시 ---")
            >>> while True:
            >>>     person_confidence = zumiAI.get_obj_confidence(name="person") # 영어 이름 사용
            >>>     if person_confidence > 0.0: # 사람이 감지되어 유효한 신뢰도 값이 반환된 경우
            >>>         print(f"사람(person) 인식 신뢰도: {person_confidence:.2f}")
            >>>         if person_confidence > 0.9:
            >>>             print("사람을 아주 정확하게 인식했어요!")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("사람(person) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> print("--- 한글 이름으로 '고양이' 신뢰도 감지 예시 ---")
            >>> # KOREAN_TO_ENGLISH_OBJ_MAP이 미리 정의되어 있다고 가정합니다.
            >>> while True:
            >>>     cat_confidence = zumiAI.get_obj_confidence(name="고양이") # 한글 이름 사용
            >>>     if cat_confidence > 0.0: # 고양이가 감지되어 유효한 신뢰도 값이 반환된 경우
            >>>         print(f"고양이(cat) 인식 신뢰도: {cat_confidence:.2f}")
            >>>         if cat_confidence > 0.8:
            >>>             print("고양이를 꽤 정확하게 인식했어요!")
            >>>         break # 감지되면 반복 중단
            >>>     else:
            >>>         print("고양이(cat) 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 기능을 초기화한 후, ``object_detector_start()`` 를 호출하여 물체 인식을 활성화해야 합니다.
            - name으로 지정하는 물체 이름은 COCO 데이터셋에 정의된 클래스 이름이어야 합니다. 한글 이름으로 변환해서 사용할 수도 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._getObjConfidence(name)

    def get_traffic_light_color(self) -> str:
        """
        스트리밍되는 카메라 영상에서 신호등의 현재 색상을 판별하여 반환합니다.

        이 함수는 ``object_detector_start()`` 로 물체 인식이 활성화된 상태에서,
        주미의 카메라 영상 속에 신호등이 감지되면 해당 신호등의 불빛이 어떤 색인지 분석하여
        그 결과를 문자열로 알려줍니다.

        Args:
            없음

        Returns:
            str: 인식된 신호등의 색상. 다음 중 하나의 값을 반환합니다:

                - **"RED"**: 빨간색 신호등이 감지된 경우

                - **"YELLOW"**: 노란색 신호등이 감지된 경우

                - **"GREEN"**: 초록색 신호등이 감지된 경우

                - **"UNKNOWN"**: 신호등이 감지되지 않았거나, 색상을 정확히 판별하기 어려운 경우

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작

            >>> while True:
            >>>     light_color = zumiAI.get_traffic_light_color()
            >>>     if light_color == "RED":
            >>>         print("신호등이 빨간색입니다! 정지하세요.")
            >>>         zumiAI.stop()
            >>>     elif light_color == "GREEN":
            >>>         print("신호등이 초록색입니다! 출발하세요.")
            >>>         zumiAI.forward(20)
            >>>     elif light_color == "YELLOW":
            >>>         print("신호등이 노란색입니다! 주의하세요.")
            >>>         zumiAI.stop()
            >>>     else:
            >>>         print("신호등 인식 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``object_detector_init()`` 로 물체 인식 기능을 초기화한 후, ``object_detector_start()`` 를 호출하여 물체 인식을 활성화해야 합니다.
            - `object_detector_start()` 의 기본 인식 목록에 "traffic light"가 포함되어 있어야 신호등 인식이 가능합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getTrafficLightColor()


    def object_check_add_obj(self, obj_name=""):
        """
        스트리밍되는 카메라 영상에서 물체 인식 목록에 새로운 물체(객체)를 추가합니다.

        이 함수를 사용하면 ``object_detector_start()`` 가 기본으로 인식하는 물체들 외에, 다른 종류의 물체도 주미의 인식 대상에 포함시킬 수 있습니다.
        추가하려는 물체의 이름을 obj_name으로 지정하면, 주미는 해당 물체도 화면에서 찾아내기 시작합니다.

        Args:
            obj_name (str, optional): 물체 인식 목록에 추가할 물체의 이름.
                                  (예: "chair", "keyboard", "bottle" 등)
                                  만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환되어 처리됩니다.
                                  (예: "개" 입력 시 "dog"으로 변환)
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작 (기본 물체 인식 시작)

            >>> # 'keyboard'와 'mouse'를 추가로 인식하도록 설정
            >>> zumiAI.object_check_add_obj(obj_name="keyboard")
            >>> zumiAI.object_check_add_obj(obj_name="mouse")
            >>> print("인식 목록에 'keyboard'와 'mouse'가 추가되었습니다.")

            >>> # 한글 이름으로 '컵'과 '의자'를 추가 (한글-영어 매핑 사전이 구현되어 있다고 가정)
            >>> zumiAI.object_check_add_obj(obj_name="컵")
            >>> zumiAI.object_check_add_obj(obj_name="의자")
            >>> print("인식 목록에 '컵'과 '의자'가 추가되었습니다.")

            >>> # 이제 'keyboard', 'mouse', '컵', '의자' 등도 화면에서 인식될 수 있습니다.
            >>> while True:
            >>>     if zumiAI.is_obj_detected(name="keyboard"):
            >>>         print("키보드 감지!")
            >>>     elif zumiAI.is_obj_detected(name="컵"): # 한글 이름으로도 인식 여부 확인 가능
            >>>         print("컵 감지!")
            >>>     time.sleep(0.5)

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수는 물체 인식이 시작되기 전(``object_detector_init()`` 이후, ``object_detector_start()`` 이전) 또는 물체 인식이 실행 중인 상태에서 사용할 수 있습니다.
            - 추가하려는 obj_name 이 모델이 인식할 수 있는 COCO 데이터셋 클래스에 포함되어 있어야 제대로 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._yoloCheckAddObj(obj_name)


    def object_check_all_add_obj(self):
        """
        스트리밍되는 카메라 영상에서 물체 인식 목록에 모델이 인식 가능한 모든 물체(객체)를 추가합니다.

        이 함수를 사용하면 ``object_detector_start()`` 가 기본으로 인식하는 소수의 물체들뿐만 아니라, 모델이 학습된 'COCO 데이터셋'에 포함된 약 80가지 종류의 모든 물체를 주미가 화면에서 찾아내기 시작합니다.
        사람, 자동차, 신호등 같은 기본 물체부터 의자, 책, 자전거, 동물 등 훨씬 더 다양한 물체들을 인식할 수 있게 됩니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작 (기본 물체만 인식)

            >>> # 이제 모든 종류의 물체를 인식하도록 변경
            >>> zumiAI.object_check_all_add_obj()
            >>> print("이제 모든 종류의 물체 인식을 시작합니다.")

            >>> # 이제 화면에 보이는 다양한 물체들이 인식될 수 있습니다.
            >>> while True:
            >>>     # 인식된 모든 물체의 정보를 가져오는 다른 함수들과 함께 사용할 수 있습니다.
            >>>     pass
            >>>     time.sleep(0.5)

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수는 물체 인식이 시작되기 전(``object_detector_init()`` 이후, ``object_detector_start()`` 이전) 또는 물체 인식이 실행 중인 상태에서 사용할 수 있습니다.
            - 모든 물체를 인식하도록 설정하면, 시스템의 처리량이 늘어나 주미의 성능에 영향을 줄 수 있습니다. 정확히 필요한 물체만 인식하도록 설정하는 것이 효율적일 수 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._yoloCheckAllAddObj()


    def object_check_del_obj(self, obj_name: str = ""):
        """
        스트리밍되는 카메라 영상에서 물체 인식 목록에서 특정 물체(객체)를 제거합니다.

        이 함수를 사용하면 ``object_detector_start()`` 로 현재 인식 중인 물체들 중에서
        더 이상 인식하고 싶지 않은 물체(예: "cat", "dog" 등)를 obj_name으로 지정하여
        인식 대상에서 제외시킬 수 있습니다. 이렇게 하면 주미는 해당 물체를 더 이상 화면에서
        찾아내지 않게 됩니다.

        Args:
            obj_name (str, optional): 물체 인식 목록에서 제거할 물체의 이름.
                                  (예: "chair", "keyboard", "bottle" 등)
                                  만약 한글 이름으로 입력할 경우, 내부적으로 정의된 매핑 사전을 통해 자동으로 영어 이름으로 변환되어 처리됩니다.
                                  (예: "개" 입력 시 "dog"으로 변환)
        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작 (기본 물체 인식 시작)

            >>> # 'cat'과 'dog'을 인식 목록에서 제거
            >>> zumiAI.object_check_del_obj(obj_name="cat")
            >>> zumiAI.object_check_del_obj(obj_name="dog")
            >>> print("인식 목록에서 'cat'과 'dog'이 제거되었습니다.")

            >>> # 이제 주미는 'cat'과 'dog'을 더 이상 인식하지 않습니다.
            >>> while True:
            >>>     if zumiAI.is_obj_detected(name="person"):
            >>>         print("사람 감지!")
            >>>     # 'cat'이나 'dog'은 감지되지 않습니다.
            >>>     time.sleep(0.5)

            >>> zumiAI.object_detector_stop() # 물체 인식 중지

        Note:
            - 이 함수는 물체 인식이 시작되기 전(``object_detector_init()`` 이후, ``object_detector_start()`` 이전) 또는 물체 인식이 실행 중인 상태에서 사용할 수 있습니다.
            - 제거하려는 obj_name이 현재 인식 목록에 없으면 아무런 작업도 수행되지 않습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._yoloCheckDelObj(obj_name)

    def object_check_all_del_obj(self):
        """
        스트리밍되는 카메라 영상에서 물체 인식 목록에 있는 모든 물체(객체)를 제거합니다.

        이 함수를 사용하면 ``object_detector_start()`` 로 현재 인식 중인 모든 물체들을
        인식 대상에서 한 번에 제외시킬 수 있습니다. 주미가 더 이상 어떤 물체도
        자동으로 인식하지 않도록 하고 싶을 때 이 함수를 사용합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.object_detector_init() # 물체 인식 초기화
            >>> zumiAI.object_detector_start() # 물체 인식 시작 (기본 물체 인식 시작)

            >>> # 모든 물체를 인식 목록에서 제거
            >>> zumiAI.object_check_all_del_obj()
            >>> print("모든 물체 인식 목록이 비워졌습니다.")

            >>> # 이제 주미는 어떤 물체도 인식하지 않습니다.
            >>> while True:
            >>>     if zumiAI.is_obj_detected(name="person"):
            >>>         print("사람 감지!") # 이 메시지는 출력되지 않습니다.
            >>>     else:
            >>>         print("모든 물체 감지 중지됨...")
            >>>     time.sleep(0.5)

            >>> zumiAI.object_detector_stop() # 물체 인식 중지


        Note:
            - 이 함수는 물체 인식이 시작되기 전(``object_detector_init()`` 이후, ``object_detector_start()`` 이전) 또는 물체 인식이 실행 중인 상태에서 사용할 수 있습니다.

            - 이 함수를 호출하면 모든 물체 인식이 중지되는 것이 아니라, 현재 인식하고 있는 목록만 비워지는 것입니다. 따라서 ``is_obj_detected()`` 같은 함수들은 항상 False를 반환하게 됩니다.
            - 특정 물체만 다시 인식하고 싶다면 ``object_check_add_obj()`` 함수를 사용하여 원하는 물체만 다시 추가할 수 있습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._yoloCheckAllDelObj()


    ##--------------------------------------------------------------------#]
    # scketch
    def sketch_detector_init(self):
        """
        스트리밍되는 카메라 영상에서 스케치 인식 기능을 초기화합니다.

        이 함수는 주미에서 PC로 전송되는 실시간 영상 스트림을 사용하여
        컴퓨터가 그림이나 간단한 스케치를 인식할 수 있도록 필요한 설정과 리소스를 준비합니다.
        특히, 이 기능은 흰색 종이에 검은색 펜으로 그린 그림을 인식하는 데 최적화되어 있습니다.
        사각형 테두리 안에 그려진 그림을 주미의 카메라에 보여주면 이를 인식할 수 있게 됩니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 먼저 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # PC 기반 스케치 인식 기능 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작
            # ... 흰 종이에 검은 펜으로 그린 그림을 사각형 안에 넣고 인식 로직 실행 ...
            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 스케치 인식을 사용하기 전에 ``camera_stream_start()`` 함수를 호출하여 영상 스트리밍을 시작해야 합니다.
            - 이 함수로 초기화한 후, ``sketch_detector_start()`` 함수를 호출해야 실제로 스케치 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._sketchDetectorInit()


    def sketch_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 스케치 인식 기능을 시작합니다.

        이 함수를 호출하면 주미의 카메라 영상이 PC로 스트리밍될 때,
        영상 내에서 인식된 스케치가 자동으로 감지되고 다음과 같이 화면에 표시됩니다:

        - **테두리 표시**: 인식된 스케치 주변에 사각형 테두리가 그려집니다.

        - **이름 표시**: 만약 등록된 스케치라면 해당 이름이 표시됩니다.

        - **인식률 표시**: 스케치 인식의 정확도(신뢰도)가 숫자로 표시됩니다.

        - **중심 좌표**: 스케치의 중심 x, y 좌표가 표시됩니다.

        - **크기**: 스케치의 크기 정보가 표시됩니다.

        이후 ``is_sketch_detected()``, ``get_sketch_center()``, ``get_sketch_size()`` 등
        관련 함수를 사용하여 인식된 스케치의 다양한 정보를 프로그램 내에서 가져올 수도 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 기능 초기화
            >>> zumiAI.sketch_detector_start() # PC 화면에서 스케치 인식 및 시각화 시작
            # 이제 PC 화면의 스트리밍 영상에 인식된 스케치 정보가 표시됩니다.
            >>> # ... 스케치 인식을 사용하는 로직 ...
            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화해야 합니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._sketchDetectorStart()

    def sketch_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 스케치 인식 기능을 중지합니다.

        이 함수는 ``sketch_detector_start()`` 함수로 시작된 스케치 인식 프로세스와
        관련된 시각화(테두리, 이름, 인식률, 중심 좌표, 크기 등) 및 데이터 처리를 모두 종료합니다.
        더 이상 스케치 인식이 필요하지 않을 때 호출하여 시스템 자원을 해제합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 기능 초기화
            >>> zumiAI.sketch_detector_start() # PC 화면에서 스케치 인식 시작
            # ... 스케치 인식을 사용하는 로직 ...
            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지
            # 이제 PC 화면에서 스케치 인식 관련 표시가 사라지고, 자원이 해제됩니다.

        Note:
            - 스케치 인식 기능을 다시 사용하려면 ``sketch_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._sketchDetectorStop()



    def is_sketch_detected(self,name:str="Sketch") -> bool:
        """
        스트리밍되는 카메라 영상에서 특정 이름의 스케치가 감지되었는지 확인합니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        PC 화면에 스트리밍되는 영상에 지정된 name을 가진 스케치가 있는지 여부를
        True 또는 False로 반환합니다.

        Args:
            name (str, optional): 감지 여부를 확인할 스케치의 이름.
                                기본값은 "Sketch"입니다.

        Returns:
            bool: 지정된 name을 가진 스케치가 현재 영상에서 감지되었는지 여부.

                - **True**: 해당 이름의 스케치가 현재 영상에서 감지되었습니다.

                - **False**: 해당 이름의 스케치가 현재 영상에 감지되지 않았습니다.

        Examples:
            >>> zumiAI.camera_stream_start()
            >>> zumiAI.sketch_detector_init()
            >>> zumiAI.sketch_detector_start()
            >>>
            >>> # 'my_drawing_1'이라는 이름의 스케치가 감지되었는지 확인
            >>> detected_my_sketch = zumiAI.is_sketch_detected(name="my_drawing_1")
            >>> print(f"'my_drawing_1' 스케치 감지 여부: {detected_my_sketch}")
            # 'my_drawing_1' 스케치 감지 여부: True (예시 출력: 'my_drawing_1' 스케치가 감지됨)

            >>> # 'Sketch'라는 기본 이름의 스케치가 감지되었는지 확인
            >>> detected_default_sketch = zumiAI.is_sketch_detected()
            >>> print(f"기본 스케치 감지 여부: {detected_default_sketch}")
            # 기본 스케치 감지 여부: False (예시 출력: 기본 스케치가 감지되지 않음)

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._isSketchDetected(name)

    def get_sketch_center(self,name:str="Sketch") -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 스케치의 중심 좌표를 가져옵니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        현재 영상에 지정된 name의 스케치가 인식되었다면 해당 스케치의 중심이 되는
        x, y 좌표를 리스트 형태로 반환합니다. 이 좌표를 통해 주미가 스케치를 화면의
        어느 위치에서 보고 있는지 알 수 있습니다.

        Args:
            name (str, optional): 중심 좌표를 가져올 스케치의 이름.
                                기본값은 "Sketch"입니다.

        Returns:
            list: 인식된 스케치의 중심 x, y 좌표를 담은 리스트.

                - **[0] x축 위치 (int)**: 스케치의 중심 x 좌표.

                - **[1] y축 위치 (int)**: 스케치의 중심 y 좌표.

                스케치가 인식되지 않았다면 `[-1, -1]`을 반환합니다. 예시: `[0, 0]` (스트리밍 화면의 중앙)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작

            >>> while True:
            >>>     center_x, center_y = zumiAI.get_sketch_center(name="my_drawing")
            >>>     if center_x != -1 or center_y != -1: # 스케치가 감지되어 유효한 좌표가 반환된 경우
            >>>         print(f"스케치 'my_drawing'의 중심 좌표: X={center_x}, Y={center_y}")
            >>>     else:
            >>>         print("'my_drawing' 스케치 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 반환되는 좌표는 스트리밍 영상 화면의 크기(해상도)에 따라 달라질 수 있습니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getSketchCenter(name)


    def get_sketch_size(self,name:str="Sketch") -> int:
        """
        스트리밍되는 카메라 영상에서 인식된 스케치의 크기를 가져옵니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        현재 영상에 지정된 name의 스케치가 인식되었다면 해당 스케치의 크기를
        숫자(픽셀 또는 상대적인 값)로 반환합니다. 이 값을 통해 스케치가 화면에서 얼마나
        크게 보이는지, 즉 주미와의 거리가 어느 정도인지 예측하는 데 사용할 수 있습니다.

        Args:
            name (str, optional): 크기를 가져올 스케치의 이름.
                                기본값은 "Sketch"입니다.

        Returns:
            int: 인식된 스케치의 크기.
                스케치가 인식되지 않았다면 0 을 반환합니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작

            >>> while True:
            >>>     sketch_size = zumiAI.get_sketch_size(name="my_circle")
            >>>     if sketch_size != -1: # 스케치가 감지되어 유효한 크기 값이 반환된 경우
            >>>         print(f"스케치 'my_circle'의 크기: {sketch_size}")
            >>>         if sketch_size > 100:
            >>>             print("스케치가 가까이 있네요!")
            >>>         else:
            >>>             print("스케치가 조금 멀리 있거나 작게 보이네요.")
            >>>     else:
            >>>         print("'my_circle' 스케치 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 반환되는 크기 값은 스트리밍 영상 화면의 해상도나 스케치의 실제 크기, 주미와의 거리에 따라 달라질 수 있습니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getSketchSize(name)



    def sketch_train(self,name:str=""):
        """
        스트리밍되는 카메라 영상에서 새로운 스케치를 학습시키고 등록합니다.

        이 함수를 실행하면 주미의 카메라 영상이 PC로 스트리밍되는 화면에서
        스케치 학습 모드가 시작됩니다. 이 모드에서는 키보드 입력을 통해
        직접 그린 스케치를 학습시키고 저장할 수 있습니다.

        Args:
            name (str, optional): 등록할 스케치의 이름.
                                기본값은 빈 문자열("")이며, 이 경우 스케치 학습 모드 시작 시 이름을 입력하라는 안내가 나옵니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start() # 카메라 스트리밍 시작 (필수)
            >>> zumiAI.sketch_train(name="my_car_drawing") # 'my_car_drawing' 이름으로 스케치 학습 모드 시작
            # 이제 PC 화면을 보면서 'r'키를 눌러 스케치를 학습하고 'e'키로 종료하세요.
            >>> print("'my_car_drawing' 스케치 학습 모드가 종료되었습니다.")
            # 학습된 스케치는 이제 'sketch_detector_start()'로 인식될 수 있습니다.

            >>> # 이름을 지정하지 않고 학습 모드를 시작하는 경우
            >>> zumiAI.sketch_train()
            # 학습 모드 시작 시 이름을 입력하라는 메시지가 화면에 표시됩니다.

        Note:
            - **학습 과정**:
                1. ``sketch_train()`` 함수를 실행하면 스케치 학습 모드가 시작됩니다.
                2. 흰 종이에 검은 펜으로 사각형 테두리를 그리고 그 안에 그림을 그린 후, 주미의 카메라에 해당 스케치가 잘 보이도록 합니다.
                3. 화면에 스케치가 인식된 상태에서 `r` 키를 누르면 현재 화면에 있는 스케치가 한 장씩 캡처되어 학습됩니다.
                4. 스케치가 인식되지 않은 상태에서 `r` 키를 누르면 수집되지 않으므로, 스케치가 화면에 잘 보이도록 한 후 여러 번 `r` 키를 눌러 다양한 각도와 조명에서 학습시키는 것이 좋습니다.
                5. 충분히 학습되었다고 판단되면 `e` 키를 눌러 학습 모드를 종료합니다.

            - 학습된 스케치 정보는 자동으로 저장되어 다음에 주미를 시작할 때 자동으로 불러와져 인식에 사용됩니다.
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._sketchTrain(name)


    def delete_sketch_data(self,name:str=""):
        """
        스트리밍되는 카메라 영상에서 학습된 특정 이름의 스케치 데이터를 삭제합니다.

        이 함수는 ``sketch_train()`` 함수를 통해 이전에 학습하고 저장했던 스케치 데이터 중에서,
        지정된 name과 일치하는 스케치 정보를 인식 시스템에서 완전히 지웁니다.
        더 이상 특정 스케치를 인식하고 싶지 않을 때 사용합니다.

        Args:
            name (str, optional): 삭제할 스케치 데이터의 이름.
                                기본값은 빈 문자열("")이며, 이 경우 아무것도 삭제되지 않습니다.
                                만약 이름을 지정하지 않고 이 함수를 호출하면,
                                이름이 없는 스케치 데이터는 삭제되지 않습니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 'my_house'라는 이름의 스케치 데이터 삭제
            >>> zumiAI.delete_sketch_data(name="my_house")
            >>> print("'my_house' 스케치 데이터가 삭제되었습니다.")

            >>> # 'my_car'라는 이름의 스케치 데이터 삭제 (만약 등록되지 않았다면 아무 일도 일어나지 않음)
            >>> zumiAI.delete_sketch_data(name="my_car")
            >>> print("'my_car' 스케치 데이터 삭제를 시도했습니다.")

        Note:
            - 이 함수는 영구적으로 스케치 데이터를 삭제합니다. 삭제된 데이터는 복구할 수 없습니다.
            - 삭제하려는 이름이 시스템에 등록되어 있지 않으면 아무런 작업도 수행되지 않습니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._deleteSketchData(name)


    def delete_all_sketch_data(self):
        """
        스트리밍되는 카메라 영상에서 학습된 모든 스케치 데이터를 삭제합니다.

        이 함수는 ``sketch_train()`` 함수를 통해 이전에 학습하고 저장했던
        모든 스케치 인식 데이터를 인식 시스템에서 완전히 지웁니다.
        주미의 스케치 인식 기록을 완전히 초기화하고 싶을 때 사용합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 저장된 모든 스케치 데이터 삭제
            >>> zumiAI.delete_all_sketch_data()
            >>> print("모든 스케치 데이터가 삭제되었습니다.")
            # 이제 주미는 학습된 어떤 스케치도 인식하지 못하게 됩니다.

        Note:
            - 이 작업은 되돌릴 수 없습니다! 모든 학습된 스케치 데이터가 영구적으로 삭제되니 신중하게 사용해 주세요.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._deleteAllSketchData()


    def get_sketch_result(self,name:str="Sketch") -> list:
        """
        스트리밍되는 카메라 영상에서 인식된 스케치의 결과(이름과 인식률)를 가져옵니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        현재 영상에 스케치가 인식되었다면 해당 스케치의 이름과 인식률(신뢰도 점수)을
        리스트 형태로 반환합니다. 인식률은 주미가 스케치를 얼마나 정확하게 인식했는지
        나타내는 값으로, 0.0부터 1.0 사이의 숫자로 표현됩니다. (예: 0.95는 95% 정확도)

        Args:
            name (str, optional): 결과를 가져올 스케치의 이름.
                                기본값은 "Sketch"입니다.

        Returns:
            list: 인식된 스케치의 이름과 신뢰도 점수를 담은 리스트.

                - **[0] 인식된 스케치 이름 (str)**: 인식된 스케치의 이름.

                - **[1] 신뢰도 점수 (float)**: 스케치 인식의 정확도를 나타내는 0.0 ~ 1.0 사이의 값.

                스케치가 인식되지 않았거나, 지정된 `name`의 스케치 데이터가 없으면 `["None", 0.0]`을 반환합니다.
                예시: `["my_drawing", 0.85]` (인식된 스케치는 'my_drawing'이며, 85%의 신뢰도)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작

            >>> while True:
            >>>     sketch_name, confidence = zumiAI.get_sketch_result(name="my_car_drawing")
            >>>     if sketch_name != "None": # 스케치가 감지되어 유효한 결과가 반환된 경우
            >>>         print(f"인식된 스케치: {sketch_name}, 신뢰도: {confidence:.2f}")
            >>>         if confidence > 0.7:
            >>>             print("스케치가 아주 잘 인식되었네요!")
            >>>     else:
            >>>         print("스케치 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getSketchResult(name)

    def get_sketch_name(self,name:str="Sketch") -> str:
        """
        스트리밍되는 카메라 영상에서 인식된 스케치의 이름을 가져옵니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        현재 영상에 스케치가 인식되었다면 해당 스케치의 이름을 문자열로 반환합니다.
        이 이름을 통해 주미가 어떤 스케치를 보고 있는지 확인할 수 있습니다.

        Args:
            name (str, optional): 이름을 가져올 스케치의 기준이 되는 이름.
                                기본값은 "Sketch"입니다. (참고: 이 인자는 주로 내부 처리에서 특정 스케치 데이터를 구분하는 데 사용될 수 있습니다.)

        Returns:
            str: 인식된 스케치의 이름.
                스케치가 인식되지 않았거나, 지정된 name의 스케치 데이터가 없으면 "None" 반환합니다. 예시: "my_house" (인식된 스케치의 이름)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작

            >>> while True:
            >>>     detected_name = zumiAI.get_sketch_name(name="circle_drawing")
            >>>     if detected_name != "None": # 스케치가 감지되어 유효한 이름이 반환된 경우
            >>>         print(f"인식된 스케치 이름: {detected_name}")
            >>>         if detected_name == "circle_drawing":
            >>>             print("제가 그린 원이네요!")
            >>>     else:
            >>>         print("스케치 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._getSketchName(name)

    def get_sketch_confidence(self,name:str="Sketch") -> float:
        """
        스트리밍되는 카메라 영상에서 인식된 스케치의 신뢰도 점수를 가져옵니다.

        이 함수는 ``sketch_detector_start()`` 로 스케치 인식이 활성화된 상태에서,
        현재 영상에 스케치가 인식되었다면 해당 스케치 인식의 정확도를 나타내는 숫자를 반환합니다.
        이 신뢰도 점수는 0.0(0%)부터 1.0(100%) 사이의 값으로, 주미가 스케치를 얼마나
        확실하게 인식했는지 판단하는 데 사용될 수 있습니다.

        Args:
            name (str, optional): 신뢰도 점수를 가져올 스케치의 이름.
                                **이름은 영어로만 입력해야 합니다.**
                                기본값은 "Sketch"입니다.

        Returns:
            float: 인식된 스케치의 신뢰도 점수. 0.0부터 1.0 사이의 값입니다.
                스케치가 인식되지 않았거나, 지정된 `name`의 스케치 데이터가 없으면 0.0을 반환합니다.
                예시: `0.92` (92%의 정확도로 인식됨)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.sketch_detector_init() # 스케치 인식 초기화
            >>> zumiAI.sketch_detector_start() # 스케치 인식 시작

            >>> while True:
            >>>     confidence_score = zumiAI.get_sketch_confidence(name="my_tree")
            >>>     if confidence_score > 0.0: # 스케치가 감지되어 유효한 신뢰도 값이 반환된 경우
            >>>         print(f"스케치 'my_tree'의 신뢰도: {confidence_score:.2f}")
            >>>         if confidence_score > 0.85:
            >>>             print("정확도가 매우 높네요! 잘 인식했어요!")
            >>>     else:
            >>>         print("'my_tree' 스케치 감지 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.sketch_detector_stop() # 스케치 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``sketch_detector_init()`` 로 스케치 인식 기능을 초기화한 후, ``sketch_detector_start()`` 를 호출하여 스케치 인식을 활성화해야 합니다.
            - 스케치 인식은 흰 종이에 검은 펜으로 사각형 테두리를 그리고, 그 안에 그린 그림을 보여줄 때 가장 잘 작동합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        return self._connection_handler._getSketchConfidence(name)



    ##--------------------------------------------------------------------#]
    # teachablemachine
    # https://teachablemachine.withgoogle.com/

    def teachable_detector_init(self, model_path = 'model_unquant.tflite', lable_path = 'labels.txt'):
        """
        스트리밍되는 카메라 영상에서 티처블 머신 모델 인식 기능을 초기화합니다.

        이 함수는 구글의 '티처블 머신'을 사용하여 직접 학습시킨 이미지 인식 모델을
        주미의 카메라 스트리밍 영상에 적용할 수 있도록 준비합니다. 모델 파일(`.tflite`)과
        클래스 이름이 담긴 라벨 파일(`.txt`)을 지정하여, 주미가 사용자가 학습시킨
        특정 물체나 제스처 등을 인식할 수 있도록 설정합니다.

        Args:
            model_path (str, optional): 티처블 머신으로 학습시킨 모델 파일(`.tflite`)의 경로.
                                        기본값은 'model_unquant.tflite'입니다.

            label_path (str, optional): 모델이 인식할 각 클래스(카테고리)의 이름이 적힌 라벨 파일(`.txt`)의 경로.
                                        기본값은 'labels.txt'입니다.

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> # 기본 모델과 라벨 파일로 티처블 머신 인식 기능 초기화
            >>> zumiAI.teachable_detector_init()
            >>> print("티처블 머신 인식 기능이 기본 설정으로 초기화되었습니다.")

            >>> # 'my_custom_model' 폴더에 있는 모델과 라벨 파일로 초기화하는 경우
            >>> zumiAI.teachable_detector_init(model_path='my_custom_model/model.tflite',
            >>>                               label_path='my_custom_model/labels.txt')
            >>> print("사용자 정의 티처블 머신 모델로 초기화되었습니다.")

            >>> zumiAI.camera_stream_start() # 카메라 스트리밍 시작 (필수)
            >>> zumiAI.teachable_detector_start() # 티처블 머신 인식 시작
            # ... 티처블 머신 인식 로직 ...
            >>> zumiAI.teachable_detector_stop() # 티처블 머신 인식 중지

        Note:
            - 티처블 머신으로 학습시킨 모델 파일과 라벨 파일은 파이썬 스크립트와 같은 폴더에 있거나, 정확한 경로를 지정해 주어야 합니다.
            - 이 함수로 초기화한 후, ``teachable_detector_start()`` 함수를 호출해야 실제로 인식이 시작됩니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        self._connection_handler._teachableInit(model_path, lable_path)


    def teachable_detector_start(self):
        """
        스트리밍되는 카메라 영상에서 티처블 머신 모델 인식 기능을 시작합니다.

        이 함수를 호출하면 ``teachable_detector_init()`` 으로 준비된 티처블 머신 모델을 사용하여
        주미의 실시간 카메라 영상 속에서 학습된 특정 물체나 제스처를 인식하기 시작합니다.
        인식된 대상은 화면에 표시될 수 있으며, 해당 대상의 이름과 인식률(신뢰도) 정보를 얻을 수 있습니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.teachable_detector_init(model_path='my_model/model.tflite', label_path='my_model/labels.txt') # 모델 초기화
            >>> zumiAI.teachable_detector_start() # 티처블 머신 인식 시작
            # 이제 PC 화면의 스트리밍 영상에서 학습시킨 물체나 제스처가 인식되기 시작합니다.
            >>> # ... 인식 결과를 사용하는 로직 ...
            >>> zumiAI.teachable_detector_stop() # 티처블 머신 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``teachable_detector_init()`` 로 티처블 머신 모델을 초기화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._teachableStart()

    def teachable_detector_stop(self):
        """
        스트리밍되는 카메라 영상의 티처블 머신 모델 인식 기능을 중지합니다.

        이 함수는 ``teachable_detector_start()`` 로 시작된 티처블 머신 인식 프로세스를
        종료하고 관련된 리소스(자원)를 해제합니다. 더 이상 주미가 학습된 대상을
        인식할 필요가 없을 때 이 함수를 사용합니다.

        Args:
            없음

        Returns:
            이 함수는 값을 반환하지 않습니다.

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.teachable_detector_init(model_path='my_model/model.tflite', label_path='my_model/labels.txt') # 모델 초기화
            >>> zumiAI.teachable_detector_start() # 티처블 머신 인식 시작
            >>> # ... 티처블 머신 인식 로직 ...
            >>> zumiAI.teachable_detector_stop() # 티처블 머신 인식 중지
            >>> print("티처블 머신 인식 기능이 종료되었습니다.")

        Note:
            - 티처블 머신 인식 기능을 다시 사용하려면 ``teachable_detector_start()`` 함수를 다시 호출해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """
        self._connection_handler._teachableStop()


    def get_teachable_result(self):
        """
        스트리밍되는 카메라 영상에서 티처블 머신 모델의 예측 결과를 가져옵니다.

        이 함수는 ``teachable_detector_start()`` 로 티처블 머신 인식이 활성화된 상태에서,
        현재 영상에 학습된 대상이 인식되었다면, 가장 확실하게 인식된 대상의 이름과
        그 예측에 대한 신뢰도 점수(confidence score)를 리스트 형태로 반환합니다.
        신뢰도 점수는 0.0(0%)부터 1.0(100%) 사이의 값으로, 주미가 대상을 얼마나
        정확하게 인식했는지 알려줍니다.

        Args:
            없음

        Returns:
            list: 인식된 대상의 이름과 신뢰도 점수를 담은 리스트.

                - **[0] 클래스 이름 (str)**: 인식된 대상의 이름 (예: "고양이", "주먹").

                - **[1] 신뢰도 점수 (float)**: 인식의 정확도를 나타내는 0.0 ~ 1.0 사이의 값.

                아무것도 인식되지 않았다면 `["None", 0.0]`을 반환합니다. 예시: `["happy_face", 0.98]` ('happy_face'를 98%의 신뢰도로 인식함)

        Examples:
            >>> zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
            >>> zumiAI.teachable_detector_init() # 티처블 머신 모델 초기화 (기본 모델 사용)
            >>> zumiAI.teachable_detector_start() # 티처블 머신 인식 시작

            >>> while True:
            >>>     class_name, confidence = zumiAI.get_teachable_result()
            >>>     if class_name != "None": # 무언가 인식된 경우
            >>>         print(f"인식 결과: {class_name}, 신뢰도: {confidence:.2f}")
            >>>         if confidence > 0.9:
            >>>             print("아주 정확하게 인식되었네요!")
            >>>     else:
            >>>         print("인식 대기 중...")
            >>>     time.sleep(1) # 1초 대기

            >>> zumiAI.teachable_detector_stop() # 티처블 머신 인식 중지

        Note:
            - 이 함수를 사용하기 전에 ``camera_stream_start()`` 로 영상 스트리밍을 시작하고, ``teachable_detector_init()`` 로 티처블 머신 모델을 초기화한 후, ``teachable_detector_start()`` 를 호출하여 인식을 활성화해야 합니다.
            - 이 기능은 주미 자체의 하드웨어 기능이 아니라, PC 기반 소프트웨어로 처리됩니다.
        """

        return self._connection_handler._getTeachableResult()
