#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM84")

zumi.set_detect_color(1)


zumi.forward_infinite(1)
time.sleep(1)
zumi.stop()


zumi.set_detect_color(0)

time.sleep(1)

zumi.change_screen(2)

time.sleep(2)


zumi.change_emotion(6)

time.sleep(3)

zumi.change_emotion(3)
