from struct import *
from enum import Enum, IntEnum
import abc


class ISerializable:

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def getSize(self):
        pass

    @abc.abstractmethod
    def ToArray(self):
        pass




class RequestType(IntEnum):

    None_                      = 0x00      # 없음
    REQUEST_ENTRY_FACE_DETECT  = 0x01
    REQUEST_ENTRY_COLOR_DETECT = 0x02
    REQUEST_ENTRY_APRIL_DETECT = 0x04
    REQUEST_ENTRY_EULER        = 0x08
    REQUEST_ENTRY_USERDEFINED  = 0x10

class LED_effectType(Enum):

    LED_NORMAL          = 0
    LED_BLINK           = 1
    LED_FLICKER         = 2
    LED_DIMMING         = 3
    LED_SUNRIZE         = 4
    LED_SUNSET          = 5
    LED_RAINBOW         = 6


class CommandType(Enum):

    None_                           = 0x00      # 없음

    COMMAND_GOGO                            = 1
    COMMAND_LEFT                            = 2
    COMMAND_RIGHT                           = 3
    COMMAND_GOBACK                          = 4
    COMMAND_WAIT                            = 5         # 시간 설정 x 0.5
    COMMAND_WAIT1                           = 6         # 1초
    COMMAND_SPEAK                           = 7
    COMMAND_HUMAN                           = 8
    COMMAND_HAND                            = 9
    COMMAND_LED                             = 10
    COMMAND_COLOR_RED                       = 19
    COMMAND_COLOR_GREEN                     = 20
    COMMAND_CARD_NUM1                       = 21
    COMMAND_CARD_NUM2                       = 22
    COMMAND_CARD_NUM3                       = 23
    COMMAND_MOTION_STOP                     = 25

    COMMAND_GO_UNTIL_DIST                   = 26
    COMMAND_FREE_TURN                       = 27
    COMMAND_LINE_TRACE_DIST                 = 28
    COMMAND_GO_INFINITE                     = 29
    COMMAND_TRACE_INFINITE                  = 30

    COMMAND_LED_CONTROL                     = 31
    COMMAND_MOTOR1_INFINITE                 = 32
    COMMAND_MOTOR2_INFINITE                 = 33
    COMMAND_LED_INFINITE                    = 34

    COMMAND_CONTROL_MODE1                   = 35

    COMMAND_LINE_LEFT                       = 39
    COMMAND_LINE_RIGHT                      = 40

    COMMAND_MOTOR_TIME                      = 41

    COMMAND_QUICK_GOGO                      = 50
    COMMAND_QUICK_GOBACK                    = 51
    COMMAND_QUICK_LEFT                      = 52
    COMMAND_QUICK_RIGHT                     = 53

    COMMAND_FREE_TURN_PYTHON                = 70

    COMMAND_GOSENSOR                        = 100
    COMMAND_LINE_TRACING                    = 101
    COMMAND_COLOR_TRACKING                  = 102

    COMMAND_ROBOT_LINE                      = 103
    COMMAND_ROBOT_AVOIDANCE                 = 104
    COMMAND_ROBOT_FOLLOWER                  = 105
    COMMAND_ROBOT_CLIFF                     = 106

    COMMAND_SET_IR_THREADHOLD               = 150
    COMMAND_SET_MOTOR_DEGREE                = 151

    COMMAND_CONTROL_LED                     = 200
    COMMAND_PATTERN_LED                     = 201

    COMMAND_COLOR_TRACKING2                 = 211
    COMMAND_COLOR_TRACKING3                 = 212

    COMMAND_TEXT_INPUT                      = 230
    COMMAND_TEXT_SET                        = 231
    COMMAND_TEXT_ADD                        = 232



    COMMAND_SCREEN_TOGGLE                   = 240
    COMMAND_EMOTION_CHANGE                  = 241
    COMMAND_PLAY_SOUND                      = 242


    #     EndOfType               = 0xFF





class CommandType_SIZE(Enum):

    None_                           = 0      # 없음

    COMMAND_GOGO                            = 1
    COMMAND_LEFT                            = 1
    COMMAND_RIGHT                           = 1
    COMMAND_GOBACK                          = 1
    COMMAND_WAIT                            = 4         # 시간 설정 x 0.5
    COMMAND_WAIT1                           = 5         # 1초
    COMMAND_SPEAK                           = 8
    COMMAND_HUMAN                           = 4
    COMMAND_HAND                            = 9
    COMMAND_LED                             = 4

    COMMAND_COLOR_RED                       = 19
    COMMAND_COLOR_GREEN                     = 20
    COMMAND_CARD_NUM1                       = 21
    COMMAND_CARD_NUM2                       = 22
    COMMAND_CARD_NUM3                       = 23
    COMMAND_MOTION_STOP                     = 25

    COMMAND_GO_UNTIL_DIST                   = 26
    COMMAND_FREE_TURN                       = 27
    COMMAND_LINE_TRACE_DIST                 = 28
    COMMAND_GO_INFINITE                     = 2
    COMMAND_TRACE_INFINITE                  = 30

    COMMAND_LED_CONTROL                     = 31
    COMMAND_MOTOR1_INFINITE                 = 32
    COMMAND_MOTOR2_INFINITE                 = 33
    COMMAND_LED_INFINITE                    = 34

    COMMAND_CONTROL_MODE1                   = 35

    COMMAND_LINE_LEFT                       = 39
    COMMAND_LINE_RIGHT                      = 40

    COMMAND_MOTOR_TIME                      = 41

    COMMAND_QUICK_GOGO                      = 1
    COMMAND_QUICK_GOBACK                    = 1
    COMMAND_QUICK_LEFT                      = 1
    COMMAND_QUICK_RIGHT                     = 1

    COMMAND_FREE_TURN_PYTHON                = 4

    COMMAND_GOSENSOR                        = 3
    COMMAND_LINE_TRACING                    = 101
    COMMAND_COLOR_TRACKING                  = 102

    COMMAND_ROBOT_LINE                      = 103
    COMMAND_ROBOT_AVOIDANCE                 = 104
    COMMAND_ROBOT_FOLLOWER                  = 105
    COMMAND_ROBOT_CLIFF                     = 106

    COMMAND_SET_IR_THREADHOLD               = 150
    COMMAND_SET_MOTOR_DEGREE                = 151

    COMMAND_CONTROL_LED                     = 200
    COMMAND_PATTERN_LED                     = 3

    COMMAND_COLOR_TRACKING2                 = 211
    COMMAND_COLOR_TRACKING3                 = 212

    COMMAND_TEXT_INPUT                      = 1
    COMMAND_TEXT_SET                        = 2
    COMMAND_TEXT_ADD                        = 1



    COMMAND_SCREEN_TOGGLE                   = 1
    COMMAND_EMOTION_CHANGE                  = 1
    COMMAND_PLAY_SOUND                      = 1
    #     EndOfType               = 0xFF



# enum을 사용하여 관련 있는 상수를 묶음
class PersonDataIndex(Enum):
    DATA_SEN_FL = 04
    AGE = 1
    CITY = 2
    EMAIL = 3

# pair = bytearray([0x24, 0x52, 0xCD, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF])
# move = bytearray([0x24, 0x52, 0x01, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x21, 0xFF, 0xFF])


# header1 '$'  : 0x24
# header2 'R'  : 0x52
# command      : 0x01
# request (추가 기능) : 0x48
# param1(sp)   : 0x45
# param2(dis)  : 0x4c
# param3(dir)  : 0x4c
# param (예비1)   : 0x4f
# param (예비2)   : 0x21
# param (예비3)   : 0xff
# param (예비4)   : 0xff


class Command_variable_byte(ISerializable):

    def __init__(self):
        self.commandType   = CommandType.None_
        self.param1        = 0
        self.param2        = 0
        self.param3        = 0
        self.param4        = 0
        self.param5        = 0
        self.param6        = 0
        self.param7        = 0
        self.size          = 0

    @classmethod
    def getSize(cls):
        return self.size

    def toArray(self):
        """
        size 값에 따라 동적으로 pack 포맷 문자열을 생성하여 데이터를 직렬화합니다.
        첫 번째 바이트는 commandType, 나머지 바이트는 param1~param7 순서로 할당합니다.
        """
        fmt = '<B' + 'B' * (self.size - 1)
        # 모든 파라미터를 리스트로 구성한 후, size에 맞게 잘라서 사용합니다.
        params = [
            self.commandType.value,
            self.param1,
            self.param2,
            self.param3,
            self.param4,
            self.param5,
            self.param6,
            self.param7
        ]
        return pack(fmt, *params[:self.size])

    @classmethod
    def parse(cls, dataArray):
        """
        dataArray의 길이를 기준으로 동적으로 unpack 포맷 문자열을 생성하고,
        해당 데이터를 Command_variable_byte 객체로 복원합니다.
        입력된 size는 dataArray의 길이로 자동 할당합니다.
        """
        if len(dataArray) < 1:
            return None

        data = Command_variable_byte()
        data.size = len(dataArray)
        fmt = '<B' + 'B' * (data.size - 1)
        unpacked = unpack(fmt, dataArray)
        data.commandType = CommandType(unpacked[0])
        params = list(unpacked[1:])

        # 존재하는 파라미터 값만 순서대로 할당 (size에 따라 가변적으로)
        if len(params) > 0: data.param1 = params[0]
        if len(params) > 1: data.param2 = params[1]
        if len(params) > 2: data.param3 = params[2]
        if len(params) > 3: data.param4 = params[3]
        if len(params) > 4: data.param5 = params[4]
        if len(params) > 5: data.param6 = params[5]
        if len(params) > 6: data.param7 = params[6]

        return data

        # data.commandType, data.param1, data.param2, data.param3, data.param4, data.param5, data.param6, data.param7  = unpack('<BBBBBBBB', dataArray)
        # data.commandType = CommandType(data.commandType)
        # return data


