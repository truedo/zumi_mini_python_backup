#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM84")


#zumi.set_detect_face(1)
#time.sleep(3)
#zumi.set_detect_face(0)

#zumi.set_detect_marker(1)




try:
    while True:
        zumi.set_detect_marker(1)
        detect = zumi.get_detect_marker()
        ir = zumi.get_IR_sensor_all()
        print(ir)
        
        print(detect)
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("Done")

