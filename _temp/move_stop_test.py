from zumi_AI.zumi_AI import *
import keyboard
import time

# 주미 AI 인스턴스 생성 및 연결
zumiAI = ZumiAI()
zumiAI.connect("192.168.0.59")
#zumiAI.connect()

print("▶ 키보드 입력 대기 중입니다.")
print("1: 무한 전진 / 2: 정지 / 3: 인사 출력")

try:
    while True:
        if keyboard.is_pressed('1'):
            print("▶ 전진 명령 실행")
            zumiAI.move_infinite(1, 0)
            time.sleep(0.3)  # 중복입력 방지용 딜레이

        elif keyboard.is_pressed('2'):
            print("■ 정지 명령 실행")
            zumiAI.stop()
            time.sleep(0.3)

        elif keyboard.is_pressed('3'):
            print("안녕")
            zumiAI.forward_dist(1, 20)
            time.sleep(0.3)

except KeyboardInterrupt:
    print("\n프로그램 종료")
    zumiAI.stop()

