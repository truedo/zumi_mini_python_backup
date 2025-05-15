from zumi_AI.zumi_AI import *


# 'a' 키가 눌렸을 때 실행될 함수
def handle_a_key():
    print("\n>>> 'a' 키가 눌려서 이 함수가 실행되었습니다! <<<")
    # 여기에 'a' 키 눌림 시 필요한 동작 추가
    #zumi.forward_dist()

# 'esc' 키가 눌렸을 때 실행될 함수 (리스너를 멈추도록 함)
def handle_esc_key():
    print("\n>>> 'esc' 키가 눌려서 이 함수가 실행되었습니다!. <<<")
    #zumi.key_press_stop() # 이 함수는 리스너를 멈추는 함수를 호출



zumi = ZumiAI()

#1 자동 연결
zumi.connect()

#2 캘리브레이션
#zumi.set_calibration_motors() 

#3 디스플레이 색상 위치
##zumi.display_text_set(5,5)
##zumi.display_text("Motor",1)
##zumi.display_text_add("calibration",1)
##zumi.display_text_add("Start",1)
##zumi.display_text_pos(0,-20)

#4 키보드 긴급 정지 
# 스페이스키로 작동 

#5 사용자 키보드 입력
##zumi.key_press_set("a", handle_a_key)
##zumi.key_press_set("esc", handle_esc_key)
##zumi.key_press_start()
###zumi.key_press_stop()



#zumi.stop()
#zumi.disconnect()

