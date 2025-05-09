#내부테스트

from zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM84")

zumi.control_motor(2,40,1,40)
time.sleep(1)
zumi.control_motor(1,40,2,40)

time.sleep(1)
##
##
##zumi.forward_infinite(2)
##time.sleep(1)
##
##zumi.reverse_infinite(2)
##time.sleep(1)
##
##
##zumi.led_control(10,10,10)
##time.sleep(1)
##
##zumi.led_pattern(2, 0.1)
##time.sleep(1)
##
##zumi.led_pattern(LED_effectType.LED_FLICKER, 0.1)
##
##
###zumi.control_motor_time(2,50,1,50,1)
###zumi.display_text("테스트중입니다")
###time.sleep(1)
##
##
##detect_btn = zumi.get_button()
##print(detect_btn)
##
##
###zumi.go_sensor(3,150,150)
##
##
##zumi.forward_infinite(2)
##time.sleep(1)
##
##zumi.reverse_infinite(2)
##time.sleep(1)



zumi.stop()
zumi.close()
