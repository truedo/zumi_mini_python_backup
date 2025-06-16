import serial
import time
from queue import Queue
from time import sleep
from threading import Thread
from colorama import Fore, Back, Style
from serial.tools.list_ports import comports

from .receiver import *

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

        self._usePosThreadRun = False
        self._thread = None

        #self.reqCOM = 0
        self.reqINFO = 0
        self.reqREQ = 0
        self.reqPSTAT = 0


        self.senFL = 0
        self.senFR = 0
        self.senBL = 0
        self.senBR = 0
        self.senBC = 0



        self.zumiFaceDetected = False
        self.zumiFaceCenter = [0, 0]

        self.zumiColorDetected = False
        self.zumiColorCenter = [0, 0]

        self.zumiMarkerDetected = False
        self.zumiMarkerCenter = [0, 0]

        self.zumiCatDetected = False
        self.zumiCatCenter = [0, 0]



        self.btn = 0
        self.battery = 0

    def __handler(self, dataArray):

        # for i in range(0, 24):
        #     print("0x%02X" % dataArray[i])
        # self.senFL = dataArray[4]
        # self.senFR = dataArray[3]
        # self.senBL = dataArray[7]
        # self.senBC = dataArray[6]
        # self.senBR = dataArray[5]


        #self.reqCOM = dataArray[PacketDataIndex.DATA_COM.value - self.headerLen]
        self.reqINFO = dataArray[PacketDataIndex.DATA_INFO.value - self.headerLen]
        self.reqREQ = dataArray[PacketDataIndex.DATA_REQ.value - self.headerLen]
        self.reqPSTAT = dataArray[PacketDataIndex.DATA_PSTAT.value - self.headerLen]

        # if(dataArray[0] == 1)
        self.senFR = dataArray[PacketDataIndex.DATA_SEN_FR.value - self.headerLen]
        self.senFL = dataArray[PacketDataIndex.DATA_SEN_FL.value - self.headerLen]
        self.senBR = dataArray[PacketDataIndex.DATA_SEN_BR.value - self.headerLen]
        self.senBC = dataArray[PacketDataIndex.DATA_SEN_BC.value - self.headerLen]
        self.senBL = dataArray[PacketDataIndex.DATA_SEN_BL.value - self.headerLen]

        self.btn = dataArray[PacketDataIndex.DATA_BTN_INPUT.value - self.headerLen]
        self.battery = dataArray[PacketDataIndex.DATA_BATTERY.value - self.headerLen]


        self.zumiFaceDetected = dataArray[PacketDataIndex.DATA_DETECT_FACE.value - self.headerLen]
        self.zumiFaceCenter[0] = dataArray[PacketDataIndex.DATA_DETECT_FACE_X.value - self.headerLen]
        self.zumiFaceCenter[1] = dataArray[PacketDataIndex.DATA_DETECT_FACE_Y.value - self.headerLen]

        self.zumiColorDetected = dataArray[PacketDataIndex.DATA_DETECT_COLOR.value - self.headerLen]
        self.zumiColorCenter[0] = dataArray[PacketDataIndex.DATA_DETECT_COLOR_X.value - self.headerLen]
        self.zumiColorCenter[1] = dataArray[PacketDataIndex.DATA_DETECT_COLOR_Y.value - self.headerLen]

        self.zumiMarkerDetected = dataArray[PacketDataIndex.DATA_DETECT_MARKER.value - self.headerLen]
        self.zumiMarkerCenter[0] = dataArray[PacketDataIndex.DATA_DETECT_MARKER_X.value - self.headerLen]
        self.zumiMarkerCenter[1] = dataArray[PacketDataIndex.DATA_DETECT_MARKER_Y.value - self.headerLen]

        self.zumiCatDetected = dataArray[PacketDataIndex.DATA_DETECT_CAT.value - self.headerLen]
        self.zumiCatCenter[0] = dataArray[PacketDataIndex.DATA_DETECT_CAT_X.value - self.headerLen]
        self.zumiCatCenter[1] = dataArray[PacketDataIndex.DATA_DETECT_CAT_Y.value - self.headerLen]


        # Verify data processing complete
        self._receiver.checked()

        #return header.dataType

    def __receiving(self):
        while self._usePosThreadRun:

            self._bufferQueue.put(self._serialport.read())

            # Automatic update of data when incoming data background check is enabled
            if self._usePosCheckBackground:
                # while self.__check() != DataType.None_:
                #     pass

                while self.__check() != 0:
                    #print("check")
                    pass

            # sleep(0.001)

    def __check(self):

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

                self.__handler(self._receiver.data)
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
                self._thread = Thread(target=self.__receiving, args=(), daemon=True)
                self._thread.start()
                self._debugger._printLog("Connected.({0})".format(portname))

            else:
                self._debugger._printError("Could not connect to device.")
                print("Serial port could not open. Check the dognle and port.")
                self.close()
                #exit()
                return False

        # Could not find device
        except:
            self._debugger._printError("Could not connect to device.")
            print("Could not find ZumiAI dongle.")
            self.close()
            #exit()
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

    def _get_req_datas(self):
        return (self.reqINFO, self.reqREQ, self.reqPSTAT) # Return a tuple copy

    def _get_PSTAT_data(self):
        return (self.reqPSTAT) # Return a PSTAT flag

    def _get_ir_all_readings(self):
        """Returns the latest IR sensor readings (FL, FR, BL, BC, BR)."""
        #with self._data_lock:
        return (self.senFL, self.senFR, self.senBL, self.senBC, self.senBR) # Return a tuple copy

    def _get_detect_data(self,dataIndex):

        if dataIndex == PacketDataIndex.DATA_DETECT_FACE:
            return self.zumiFaceDetected

        if dataIndex == PacketDataIndex.DATA_DETECT_FACE_X:
            return self.zumiFaceCenter


        elif dataIndex == PacketDataIndex.DATA_DETECT_COLOR:
            return self.zumiColorDetected
        elif dataIndex == PacketDataIndex.DATA_DETECT_COLOR_X:
            return self.zumiColorCenter


        elif dataIndex == PacketDataIndex.DATA_DETECT_MARKER:
            return self.zumiMarkerDetected
        elif dataIndex == PacketDataIndex.DATA_DETECT_MARKER_X:
            return self.zumiMarkerCenter


        elif dataIndex == PacketDataIndex.DATA_DETECT_CAT:
            return self.zumiCatDetected

        elif dataIndex == PacketDataIndex.DATA_DETECT_CAT_X:
            return self.zumiCatCenter





    def _get_btn_data(self):
        return self.btn

    def _get_battery_data(self):
        return self.battery
