import pygame
import cv2

pygame.init()
screen_width = 640
screen_height = 480
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("키보드 이벤트 감지")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            print(f"키 눌림: {pygame.key.name(event.key)}")
            if event.key == pygame.K_q:
                running = False
            elif event.key == pygame.K_r:
                # self.send_custom_packet() 호출 (해당 클래스 및 메서드가 있다면)
                print("'r' 키 눌림 감지")
        elif event.type == pygame.KEYUP:
            print(f"키 떼어짐: {pygame.key.name(event.key)}")

    # OpenCV를 사용하는 경우 여기에 프레임 처리 등을 추가할 수 있습니다.
    # 예: ret, frame = cap.read()
    #      cv2.imshow("Frame", frame)

pygame.quit()
cv2.destroyAllWindows()
