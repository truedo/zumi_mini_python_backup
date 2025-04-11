#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM84")

#zumi.sendCommand2(CommandType.COMMAND_GO_UNTIL_DIST)
#zumi.send_until_dist(1,20,0)

#umi.forward_dist()
#time.sleep(3)
#zumi.reverse_dist()

#zumi.send_turn(3,720,1)
#time.sleep(5)
#zumi.left_turn(3,90)
#time.sleep(3)
#zumi.right_turn(3,90)


#zumi.forward_dist_quick(20)
#time.sleep(2)
#zumi.reverse_dist_quick(20)


#zumi.left_turn_quick(360)
#time.sleep(10)
#zumi.right_turn_quick(360)


#zumi.led_control(10, 0, 0)
#time.sleep(0.5)
#zumi.led_control(0, 10, 0)
#time.sleep(0.5)
#zumi.led_control(0, 0, 10)
#time.sleep(0.5)
#zumi.led_control(10, 10, 10)
#time.sleep(0.1)


#zumi.led_pattern(LED_effectType.LED_BLINK,1)
#time.sleep(0.1)


#zumi.go_sensor(1,750,750)

#zumi.play_sound(2) #!!


#zumi.control_motor(2,50,1,50)
#time.sleep(2)
#zumi.control_motor(1,50,2,50)
#time.sleep(2)
#zumi.control_motor(2,0,2,0)

#zumi.stop()  
#zumi.control_motor(2,0,2,0)

#zumi.control_motor_time(2,50,1,50,1)



#zumi.linefollower_distance(1,20)

#zumi.linefollower(1,700,700,700,1)

zumi.forward_infinite(1)
#zumi.reverse_infinite(1)

#zumi.linefollower_infinite(2)


time.sleep(1)
zumi.stop()


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



