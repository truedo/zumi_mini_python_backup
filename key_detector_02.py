import cv2
import keyboard

def send_forward_command():
    print("전진 명령 전송")
    # 전진을 위한 명령을 전송하는 코드를 넣으세요

def send_stop_command():
    print("정지 명령 전송")
    # 정지를 위한 명령을 전송하는 코드를 넣으세요

# 'r'키 눌림 이벤트 등록
keyboard.on_press_key("r", lambda _: send_forward_command())
# 'r'키 떼어짐 이벤트 등록
keyboard.on_release_key("r", lambda _: send_stop_command())

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Frame", frame)
    
    # 영상 창에서 'q' 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
