import sys
import serial
import time
import queue
from queue import Queue
from time import sleep
import threading
from threading import Thread
from colorama import Fore, Back, Style
#from serial.tools.list_ports import comports

# from protocol import * # make html 사용시 적용
# from receiver import * # make html 사용시 적용

from .protocol import *
from .receiver import *

def add(a: int, b: int) -> int:
    """
    테스트 함수
    두 개의 정수를 더합니다.

    Args:
        a (int): 첫 번째 정수.
        b (int): 두 번째 정수.

    Returns:
        int: a와 b의 합.

    Examples:
        >>> add(2, 3)
        5


    How to Use:
        >>> zumi.display_text_set(12,5)



    Args:
        param1 (int): The first parameter used for ...
        param2 (str): The second parameter used for ...

    Returns:
        bool: True if successful, False otherwise.

    Raises:
        TypeError: If `param1` is not an integer.
        ValueError: If `param2` is an empty string.

    Notes:
        This is an additional note or a set of notes that provide extra
        information about the function, but are not part of the main description.

    Examples:
        >>> example_function(5, "hello")
        True
        >>> example_function(10, "")
        ValueError: param2 should not be an empty string.
        ``code sample``

    .. note:: 용을 ''조심''하십시오.

    +-----+---+---+----+
    | mul | 2 | 3 | 4  |
    +=====+===+===+====+
    | 2   | 4 | 6 | 8  |
    +-----+---+---+----+
    | 3   | 6 | 9 | 12 |
    +-----+---+---+----+

    ===== ===== =======
    A     B     A and B
    ===== ===== =======
    False False False
    False True  False
    True  False False
    True  True  True
    ===== ===== =======

    """
    return a + b

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


class ZumiAI:
    def __init__(self, flagCheckBackground=True, flagShowErrorMessage=True, flagShowLogMessage=False,
                 flagShowTransferData=True, flagShowReceiveData=False):

        self._serialport = None
        self._bufferQueue = Queue(4096)
        self._bufferHandler = bytearray()
        self._flagConnected = False  # Lets you know if you're connected to a device when you connect automatically

        self._thread = None
        self._flagThreadRun = False


        self._flagShowErrorMessage = flagShowErrorMessage
        self._flagShowLogMessage = flagShowLogMessage
        self._flagShowTransferData = flagShowTransferData

        self.timeStartProgram = time.time()  # Program Start Time Recording

        self._current_request = RequestType.None_



        self._receiver = Receiver()
        self._flagCheckBackground = flagCheckBackground
        self._flagShowReceiveData = flagShowReceiveData

        self.senFL = 0
        self.senFR = 0
        self.senBL = 0
        self.senBR = 0
        self.senBC = 0

        self.detectFace = 0
        self.detectCat = 0
        self.detectFace = 0


    def _printLog(self, message):

        # Log output
        if self._flagShowLogMessage and message is not None:
            print(Fore.GREEN + "[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram),
                                                         message) + Style.RESET_ALL)

    def _printError(self, message):

        # Error message output
        if self._flagShowErrorMessage and message is not None:
            print(
                Fore.RED + "[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram), message) + Style.RESET_ALL)

    def _printTransferData(self, dataArray):

        # Send data output
        if self._flagShowTransferData and (dataArray is not None) and (len(dataArray) > 0):
            print(Back.YELLOW + Fore.BLACK + convertByteArrayToString(dataArray) + Style.RESET_ALL)

    def _printReceiveData(self, dataArray):

        # Receive data output
        if self._flagShowReceiveData and (dataArray is not None) and (len(dataArray) > 0):
            print(Back.CYAN + Fore.BLACK + convertByteArrayToString(dataArray) + Style.RESET_ALL, end='')

    def _printReceiveDataEnd(self):

        # Incoming data output (skipped)
        if self._flagShowReceiveData:
            print("")

    def _handler(self, dataArray):



        # for i in range(0, 24):
        #     print("0x%02X" % dataArray[i])

        # if(dataArray[0] == 1)

        self.senFL = dataArray[4]
        self.senFR = dataArray[3]
        self.senBL = dataArray[7]
        self.senBC = dataArray[6]
        self.senBR = dataArray[5]

        self.detectFace = dataArray[8]
        self.detectFace = dataArray[8]
        self.detectFace = dataArray[8]



        print(self.detectFace)


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
        while self._flagThreadRun:

            self._bufferQueue.put(self._serialport.read())

            # Automatic update of data when incoming data background check is enabled
            if self._flagCheckBackground:
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
                self._printReceiveData(dataArray)
                self._bufferHandler.extend(dataArray)

        while len(self._bufferHandler) > 0:
            stateLoading = self._receiver.call(self._bufferHandler.pop(0))

            # error output
            if stateLoading == StateLoading.Failure:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()
                # Error message output
                self._printError(self._receiver.message)

            # log output
            if stateLoading == StateLoading.Loaded:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()
                # Log output
                self._printLog(self._receiver.message)

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
            return self._flagConnected

    def open(self, portname=None):

        try:
            print("Serial connect")
            ser = serial.Serial()  # open first serial port
            ser.close()
        except:
            print("Serial library not installed")
            self.close()
           # exit()
            return False

        # if portname is None:
        #     nodes = comports()
        #     size = len(nodes)

        #     for item in nodes:
        #         if item.vid == cde_controller_vid:
        #             portname = item.device
        #             print("Found CoDrone EDU controller. ", portname)
        #             break
        # try:

        print("Connecting to ZumiAI.")
        self._serialport = serial.Serial(
            port=portname,
            baudrate=115200)

        if self.isOpen():
            self._flagThreadRun = True
            self._thread = Thread(target=self._receiving, args=(), daemon=True)
            self._thread.start()
            self._printLog("Connected.({0})".format(portname))

        else:
            self._printError("Could not connect to device.")
            print("Serial port could not open. Check the microUSB cable and port. ")
            self.close()
            exit()
            return False

        # # TODO: Fix this bare except
        # except:
        #     self._printError("Could not connect to device.")
        #     print("Could not find CoDrone EDU controller.")
        #     self.close()
        #     exit()
        #     return False
        # # check about 10 times
        # for i in range(10):
        #     state = self.get_state_data()
        #     state_flight = state[2]
        #     if state_flight is ModeFlight.Ready:
        #         break
        #     else:
        #         time.sleep(0.1)

        # if state_flight is ModeFlight.Ready:
        #     print("Connected to CoDrone EDU")
        #     battery = state[6]
        #     print("Battery =", battery, "%")
        #     # set the speed to medium level
        #     self.speed_change(speed_level=2)
        #     for i in range(10):
        #         # disable the previous YPRT commands
        #         self.sendControl(0, 0, 0, 0)
        #         time.sleep(0.1)
        # else:
        #     print("Could not connect to CoDrone EDU.")
        #     print("Check that the controller and drone are on and paired.")
        #     # print("Exiting program")
        #     # self.close()
        #     # exit()

        # return True

    def close(self):
        # log output
        if self.isOpen():
            self._printLog("Closing serial port.")
        else:
            self._printLog("not connected.")


        self._printLog("Thread Flag False.")

        if self._flagThreadRun:
            self._flagThreadRun = False
            time.sleep(0.1)

        self._printLog("Thread Join.")

        if self._thread is not None:
            self._thread.join(timeout=1)

        self._printLog("Port Close.")

        if self.isOpen():
            self._serialport.close()
            time.sleep(0.2)

    # def makeTransferDataArray(self, data):
    #     if (data is None):
    #         return None
    #     ##if not isinstance(header, Header):
    #     #    return None
    #     if isinstance(data, ISerializable):
    #         data = data.toArray()
    #     # = CRC16.calc(header.toArray(), 0)
    #     #crc16 = CRC16.calc(data, crc16)
    #    # crc16 = 0x0000
    #     dataArray = bytearray()
    #     dataArray.extend((0x24, 0x52))
    #    # dataArray.extend(header.toArray())
    #     dataArray.extend(data)
    #    # dataArray.extend(pack('H', crc16))
    #     return dataArray

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
        if not self.isOpen():
            return

        dataArray = self.makeTransferDataArray(data)

        self._serialport.write(dataArray)

        # send data output
        self._printTransferData(dataArray)

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
        명령을 전송합니다.

        Args:
            commandType

        Returns:
            int: a와 b의 합.

        Examples:
            >>> add(2, 3)
            5
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
            >>> sendForward_until_dist(1, 20, 0)
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
            >>> forward_dist(1, 20)
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
            >>> forward_dist(1, 20)
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
            >>> send_turn_angle(1, 20, 0)
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
            >>> left_turn_angle(1, 90)
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
            >>> right_turn_angle(1, 90)
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
            >>> forward_dist_quick(20)
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
            >>> reverse_dist_quick(20)
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
            >>> left_turn_quick(90)
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
            >>> right_turn_quick(90)
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
            >>> led_control(10,10,10)
        """
        return self.sendCommand(CommandType.COMMAND_LED, r, g, b)



    def led_pattern(self, pattern=LED_effectType.LED_BLINK, time=1):
        """
        led 패턴을 변경

        Args:
            pattern  : - LED_effectType.LED_NORMAL  : 켜있는 상태
                       - LED_effectType.LED_BLINK   : 깜박이기
                       - LED_effectType.LED_FLICKER : 두번 깜박이기
                       - LED_effectType.LED_DIMMING : 점점 밝아졌다가 어두워지기
                       - LED_effectType.LED_SUNRIZE : 점점 어두워지기
                       - LED_effectType.LED_SUNSET  : 점점 밝아지기
                       - LED_effectType.LED_RAINBOW : 무지개색상으로 변하기
            time     : 시간 (초)

        Returns:
            없음

        Examples:
            >>> led_pattern(LED_effectType.LED_BLINK, 1)
        """

        time_high = 0
        time_low = 0
        time = int(time *1000)
        if(time < 255) : time_low = time

        else :
            time_high = time // 256  # 상위 바이트 (몫)
            time_low = time % 256   # 하위 바이트 (나머지)

        return self.sendCommand(CommandType.COMMAND_PATTERN_LED, pattern.value, time_high, time_low)




    def go_sensor(self, speed = 1, senL = 700, senR = 700):
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
            >>> zumi.go_sensor(3,700,700)
        """

        if(speed < 1) :speed = 1
        if(speed > 3) :speed = 3

        if(senL < 0) :senL = 0
        if(senL > 1024) :senL = 1024

        if(senR < 0) :senR = 0
        if(senR > 1024) :senR = 1024

        senL = int(senL/4)
        senR = int(senR/4)

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
        if(senBL > 1024) :senBL = 1024

        if(senBR < 0) :senBR = 0
        if(senBR > 1024) :senBR = 1024

        if(senBC < 0) :senBC = 0
        if(senBC > 1024) :senBC = 1024

        senBL = int(senBL/4)
        senBR = int(senBR/4)
        senBC = int(senBC/4)

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
            dir   : 방향 (0:후진 , 1:전진)

        Returns:
            없음

        Examples:
            >>> forward_infinite(1, 20)
        """

        if(speed < 0) : speed = 0
        if(speed > 3) : speed = 3

        dir = 0

        return self.sendCommand(CommandType.COMMAND_GO_INFINITE,speed,dir)

    def forward_infinite(self, speed=1):
        """
        계속 전진합니다.

        Args:
            speed : 속도 (1, 2, 3)

        Returns:
            없음

        Examples:
            >>> forward_infinite(1, 20)
        """

        return self.move_infinite(speed,dir)


    def reverse_infinite(self, speed=1):
        """
        계속 후진합니다.

        Args:
            speed : 속도 (1, 2, 3)

        Returns:
            없음

        Examples:
            >>> reverse_infinite(1, 20)
        """

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
            IR sensor value :   - 전방 왼쪽
                                - 전방 오른쪽
                                - 하단 왼쪽
                                - 하단 중앙
                                - 오른쪽

        Returns:
            없음

        Examples:
            >>> ir = zumi.get_IR_sensor_all()
                print(ir)
        """

        ir_data = []
        ir_data.append(self.senFL)
        ir_data.append(self.senFR)
        ir_data.append(self.senBL)
        ir_data.append(self.senBC)
        ir_data.append(self.senBR)

        return ir_data


    def get_IR_sensor_bottom(self):
        """
        하단 센서 값을 가져옵니다.

        Args:
            IR sensor value :   - 하단 왼쪽
                                - 하단 중앙
                                - 오른쪽
        Returns:
            없음

        Examples:
            >>> ir = zumi.get_IR_sensor_bottom()
                print(ir)
        """

        ir_data = []
        ir_data.append(self.senBL)
        ir_data.append(self.senBC)
        ir_data.append(self.senBR)

        return ir_data


    def get_IR_sensor_front(self):
        """
        전방 센서 값을 가져옵니다.

        Args:
             IR sensor value :  - 전방 왼쪽
                                - 전방 오른쪽

        Returns:
            없음

        Examples:
            >>> ir = zumi.get_IR_sensor_front()
                print(ir)
        """

        ir_data = []
        ir_data.append(self.senFL)
        ir_data.append(self.senFR)

        return ir_data

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
            set : (1 카메라, 1 표정)

        Returns:
            없음

        Examples:
            >>> zumi.set_screen(2)
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
            색상 : 0~20 (0의 경우 현재 상태 유지)
            크기 : 0~5 (0의 경우 현재 상태 유지)

        Returns:
            없음

        Examples:
            >>> zumi.display_text_set(12,5)

        """

        self.sendCommand(CommandType.COMMAND_TEXT_SET, color ,size)



    # def sendForward(self):
    #     data = Command()
    #     data.commandType = CommandType.COMMAND_GOGO
    #     data.option = 0
    #     return self.transfer(data)

