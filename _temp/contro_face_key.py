from zumi_AI.zumi_AI import *  # ZumiAI 클래스 임포트
import time
import keyboard  # 키보드 입력 감지를 위한 라이브러리

# Zumi 인스턴스 생성 및 연결
zumiAI = ZumiAI()
zumiAI.connect("192.168.0.59")

zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
time.sleep(0.2)
zumiAI.face_detector_init()   # 얼굴 인식 초기화
time.sleep(0.2)

print("=== 얼굴 인식 제어 프로그램 시작 ===")
print("1: 얼굴 인식 시작")
print("2: 얼굴 인식 중지")
print("3: 얼굴 데이터 삭제")
print("ESC: 종료")

face_detection_active = False  # 얼굴 인식 활성 상태 플래그

#zumiAI.face_detector_start()


try:
    while True:
        if keyboard.is_pressed('1'):
            print("▶ 얼굴 인식 시작")
            zumiAI.face_detector_start()
            face_detection_active = True
            time.sleep(0.5)

        elif keyboard.is_pressed('2'):
            print("▶ 얼굴 인식 중지")
            zumiAI.face_detector_stop()
            face_detection_active = False
            time.sleep(0.5)

        elif keyboard.is_pressed('3'):
            print("▶ 얼굴 데이터 삭제")
            zumiAI.delete_all_Face_data()  # 모든 얼굴 데이터 삭제
            time.sleep(0.5)

        elif keyboard.is_pressed('esc'):
            print("프로그램 종료")
            break

        # 얼굴 인식이 활성화되어 있으면 'Unknown' 감지 여부 체크
        if face_detection_active:
            detected_unknown = zumiAI.is_face_detected("Unknown")
            if detected_unknown:
                print("알 수 없는 얼굴 감지!")
            #time.sleep(0.1)  # 너무 빠르게 루프 도는 것 방지
                

except KeyboardInterrupt:
    print("사용자 인터럽트로 종료됨")

finally:
    zumiAI.camera_stream_stop()
    print("카메라 스트리밍 종료")
















