#내부테스트

from zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM84")

zumi.set_detect_face(1)
#time.sleep(3)
#zumi.set_detect_face(0)

#zumi.set_detect_marker(1)




try:
    while True:
        #zumi.set_detect_color(1)
        #detect = zumi.get_detect_face()
        #ir = zumi.get_IR_sensor_all()
        #print(ir)
        
        #btn = zumi.get_button()
        #print(btn)

        #battery = zumi.get_battery()
        #print(battery)
        
        #print(detect)

        detect = zumi.get_detect_face()
        detect_face = detect[0]
        print(detect_face)
        
        if detect_face == 1:
            zumi.led_control(10,10,10)
        else:
            zumi.led_control(0,0,0)
            
            


        
        time.sleep(0.5)
        
except KeyboardInterrupt:

    zumi.stop()
    zumi.close()
    print("Done")
