#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM637")

#zumi.forward_infinite(1)
#time.sleep(1)
#zumi.stop()

zumi.display_text("하하하",1)
time.sleep(0.1)

zumi.display_text_add("1",1)
time.sleep(0.1)

zumi.display_text_set(0,1)

#zumi.send_text("Hello, world!2")


