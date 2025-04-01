import sys
import serial
import time
from time import sleep
import threading
from threading import Thread
from colorama import Fore, Back, Style

from protocol import *


def convertByteArrayToString(dataArray):
    if dataArray == None:
        return ""

    string = ""

    if (isinstance(dataArray, bytes)) or (isinstance(dataArray, bytearray)) or (not isinstance(dataArray, list)):
        for data in dataArray:
            string += "{0:02X} ".format(data)

    return string


class ZumiAI:
    def __init__(self, flagCheckBackground=True, flagShowErrorMessage=True, flagShowLogMessage=True,
                 flagShowTransferData=True, flagShowReceiveData=True):

        self._serialport = None        
        self._flagConnected = False  # Lets you know if you're connected to a device when you connect automatically

        self._flagShowErrorMessage = flagShowErrorMessage
        self._flagShowLogMessage = flagShowLogMessage
        self._flagShowTransferData = flagShowTransferData

        self.timeStartProgram = time.time()  # Program Start Time Recording

        self._current_request = RequestType.None_



    def _printLog(self, message):

        # Log output
        if self._flagShowLogMessage and message is not None:
            print(Fore.GREEN + "[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram),
                                                         message) + Style.RESET_ALL)
    def _printTransferData(self, dataArray):

        # Send data output
        if self._flagShowTransferData and (dataArray is not None) and (len(dataArray) > 0):
            print(Back.YELLOW + Fore.BLACK + convertByteArrayToString(dataArray) + Style.RESET_ALL)


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
            exit()
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

        print("Connecting to CoDrone EDU controller.")
        self._serialport = serial.Serial(
            port=portname,
            baudrate=115200)

        if self.isOpen():
            self._flagThreadRun = True
            # self._thread = Thread(target=self._receiving, args=(), daemon=True)
            # self._thread.start()
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


        # self._printLog("Thread Flag False.")

        # if self._flagThreadRun:
        #     self._flagThreadRun = False
        #     time.sleep(0.1)

        # self._printLog("Thread Join.")

        # if self._thread is not None:
        #     self._thread.join(timeout=1)

        # self._printLog("Port Close.")

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
        self._current_request = request
        

    def build_request_section(self, request: RequestType) -> bytearray:
        """
        리퀘스트 값을 구성합니다.
        (이 예제에서는 커맨드 섹션과 별도로 리퀘스트를 구성하고 최종 데이터에 삽입합니다.)
        """
        return bytearray([request.value])


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
            self.size = CommandType_SIZE[commandType.name].value

            if self.size > 8:
                self.size = 8
            
        except KeyError:
            # 기본 사이즈를 지정할 수 있음 (필요에 따라 조정)
            self.size = 8
        return self.size



    def sendCommand(self,commandType):

        self.set_request(RequestType.REQUEST_ENTRY_COLOR_DETECT)

        data = Command_variable_byte()

        data.commandType = commandType
        data.size = self.update_size(data.commandType)

        data.param1 = 20
        data.param2 = 20
        data.param3 = 20
        data.param4 = 20
        data.param5 = 20
        data.param6 = 0x06
        data.param7 = 0x07

        return self.transfer(data)





    def sendForward_until_dist(self):

        data = Command_go_until_dist()

        data.commandType = CommandType.COMMAND_GO_UNTIL_DIST
        data.speed = 20
        data.dist = 20
        data.dir = 20        

        return self.transfer(data)


    def sendForward(self):

        data = Command()

        data.commandType = CommandType.COMMAND_GOGO
        data.option = 0

        return self.transfer(data)
