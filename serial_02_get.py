#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM637")

zumi.forward_infinite(1)

time.sleep(1)
zumi.stop()

ir = zumi.get_IR_sensor_all()
print("Front L",ir[0])
print("Front R",ir[1])
print("Bottom L",ir[2])
print("Bottom C",ir[3])
print("Bottom R",ir[4])


ir = zumi.get_IR_sensor_front()
print("Front L",ir[0])
print("Front R",ir[1])


ir = zumi.get_IR_sensor_bottom()
print("Bottom L",ir[0])
print("Bottom C",ir[1])
print("Bottom R",ir[2])

try:
    while True:
        ir = zumi.get_IR_sensor_all()
        
        
        #if(ir[1] < 181):
        #    zumi.stop()
        #    break
            
        print(ir)
        #print("Front L",ir[0])
        #print("Front R",ir[1])

        #print("Bottom L",ir[2])
        #print("Bottom C",ir[3])
        #print("Bottom R",ir[4])

        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("Done")



