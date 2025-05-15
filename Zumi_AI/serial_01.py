#내부테스트

from zumi_AI.zumi_AI import *



# 'a' 키가 눌렸을 때 실행될 함수
def handle_a_key():
    print("\n>>> 'a' 키가 눌려서 이 함수가 실행되었습니다! <<<")
    # 여기에 'a' 키 눌림 시 필요한 동작 추가
    #zumi.forward_dist()

# 'esc' 키가 눌렸을 때 실행될 함수 (리스너를 멈추도록 함)
def handle_esc_key():
    print("\n>>> 'esc' 키가 눌려서 이 함수가 실행되었습니다!. <<<")
    zumi.key_press_stop() # 이 함수는 리스너를 멈추는 함수를 호출


 
zumi = ZumiAI()
zumi.connect(portname="COM84")

 #zumi.set_calibration_motors()
#zumi.forward_dist()
#zumi.control_motor(2,40,1,40)
#time.sleep(3)

zumi.display_text_set(5,5)
zumi.display_text("Motor",1)
zumi.display_text_add("calibration",1)
zumi.display_text_add("Start",1)

zumi.display_text_pos(0,-20)

zumi.key_press_set("a", handle_a_key)
zumi.key_press_set("esc", handle_esc_key)
#key_interrupt_set("space", lambda: print("\n>>> 스페이스바 눌림! 등록된 콜백 실행. <<<")) # 람다 함수도 가능
zumi.key_press_start()
#zumi.key_press_stop()

#zumi.forward_dist()
#time.sleep(2)aa
#zumi.stop()
###zumi.control_motor(2,40,1,40)
##time.sleep(1)
##zumi.control_motor(1,40,2,40)
##
##time.sleep(1)
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
##zumi.go_sensor(3,150,150)
##
##
#zumi.forward_infinite(2)
#time.sleep(1)
##
##zumi.reverse_infinite(2)
##time.sleep(1)


##
zumi.stop()
zumi.disconnect()
#listener.stop() 
