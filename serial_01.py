import zumi_mini    # import로 person 모듈을 가져옴
from zumi_mini import *

# 모듈.클래스()로 person 모듈의 클래스 사용
zumi = ZumiAI()
zumi.open(portname="COM84")
zumi.sendCommand(CommandType.COMMAND_GO_UNTIL_DIST)
zumi.close()
