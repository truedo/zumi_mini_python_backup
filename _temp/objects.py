#[Python]_EX_11 신호등 예제
from zumi_AI.zumi_AI import *

zumiAI = ZumiAI()
zumiAI.connect("192.168.0.88")

zumiAI.camera_stream_start()  # 카메라 스트리밍 시작
zumiAI.object_detector_init(performance_mode="balance") # 'balance' 모드로 물체 인식 모델 초기화
zumiAI.object_detector_start() # 물체 인식 시작
# 이제 PC 화면의 스트리밍 영상에서 설정된 물체들이 인식되기 시작합니다.
# ... 인식 결과를 사용하는 로직 ...
#zumiAI.object_detector_stop() # 물체 인식 중지

