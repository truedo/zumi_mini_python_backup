#내부테스트

from zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.connect()



time.sleep(1)
zumi.led_control(0,10,0)
time.sleep(1)
zumi.led_control(10,0,10)
time.sleep(1)
#zumi.led_control(0,10,0)

zumi.led_pattern(1, 0.5)


##
##zumi.forward_dist(1,10)
##time.sleep(1)
##zumi.reverse_dist(1,10)

##time.sleep(5)
##zumi.set_calibration_motors() 


##zumi.left_turn(1,180)
##time.sleep(5)
##zumi.left_turn(1,180)
##time.sleep(5)

##print("!1")
##
##zumi.control_motor(2,50,1,50)
##time.sleep(1)
##print("!2")
##
##zumi.control_motor(2,150,2,20)
##time.sleep(1)
##
##print("!3")
##
##zumi.control_motor(2,50,1,50)
##time.sleep(0.5)
##
##print("!4")
##
##zumi.control_motor(1,20,1,150)
##time.sleep(1)
##
##
##
##print("!5")
##zumi.control_motor_time(2,50,1,50,5)
##time.sleep(1)







#zumi.get_detect_face()


#zumi.set_detect_face(1)
#time.sleep(3)
#zumi.set_detect_face(0)

#zumi.set_detect_marker(1)


##
##
try:
    while True:
        #zumi.play_sound(0)
        #time.sleep(1)

        #zumi.set_detect_color(1)
        #detect = zumi.get_detect_face()
        #ir = zumi.get_IR_sensor_all()
        #print(ir)
        
        #btn = zumi.get_button()
        #print(btn)

##        battery = zumi.get_battery()
##        print(battery)
        
        #print(detect)

##        detect = zumi.get_detect_face()
##        detect_face = detect[0]
##        print(detect_face)
##        
##        if detect_face == 1:
##            zumi.led_control(10,10,10)
##        else:
##            zumi.led_control(0,0,0)
##            
            


        
        time.sleep(0.5)
        
except KeyboardInterrupt:

    zumi.stop()
    zumi.close()
    print("Done")
