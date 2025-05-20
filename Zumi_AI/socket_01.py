#내부테스트

from zumi_AI.zumi_AI import *


zumi = ZumiAI()

#zumi.connect('ws://192.168.0.59/ws')

zumi.connect()


zumi.start_sensors()

zumi.start_video_viewer() # 루프가 되어 버림


time.sleep(1)
zumi.led_control(10,10,10)
time.sleep(0.5)
zumi.led_control(10,0,0)
time.sleep(1)

zumi.forward_dist()
time.sleep(2)
zumi.stop()



#zumi.stop()
#zumi.disconnectqq
 
