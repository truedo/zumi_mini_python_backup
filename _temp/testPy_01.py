from zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM637")



zumi.led_control(10, 0, 0)
time.sleep(0.5)
zumi.led_control(0, 10, 0)
#time.sleep(0.5)
#zumi.led_control(0, 0, 10)
#time.sleep(0.5)
#zumi.led_control(10, 10, 10)
#time.sleep(0.1)



ir = zumi.get_IR_sensor_all()
print("Front L",ir[0])
print("Front R",ir[1])
print("Bottom L",ir[2])
print("Bottom C",ir[3])
print("Bottom R",ir[4])

try:
    while True:
        ir = zumi.get_IR_sensor_bottom()
        
        
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
