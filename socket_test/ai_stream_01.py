from Zumi_AI.robot_controller import RobotController

# ai 모드
client = RobotController(
    ws_url="ws://192.168.0.63/ws",
    mode="ai",
    model_path = "keras_model.h5",        # path to .h5 model for AI mode
    labels_path = "labels.txt",           # path to labels.txt for AI mode
    show_video=True
)


# 스트리밍 모드
#client = RobotController(
#    ws_url="ws://192.168.0.63/ws",
#    mode="stream",
#    show_video=True
#)
#client.start()

try:
    client.start()
except KeyboardInterrupt:
    print("안전하게 종료 중...")
    client.stop()
