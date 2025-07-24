import tensorflow as tf
import numpy as np
import requests
import cv2
from PIL import Image
import io

# --- 1. 설정 변수 ---
ESP32_STREAM_URL = 'http://192.168.1.100:59/stream' 
# TensorFlow Lite 모델 파일 경로로 변경
MODEL_PATH = 'model_unquant.tflite' # Teachable Machine에서 내보낸 .tflite 파일 이름
LABELS_PATH = 'labels.txt'
IMAGE_WIDTH = 224
IMAGE_HEIGHT = 224

# --- 2. 모델 및 레이블 로드 ---
print(f"TensorFlow Lite 모델 로딩 중: {MODEL_PATH}")
try:
    # TFLite 인터프리터 로드
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors() # 텐서 할당

    # 입력 및 출력 텐서 가져오기
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    print("TensorFlow Lite 모델 로드 완료.")
except Exception as e:
    print(f"TensorFlow Lite 모델 로드 중 오류 발생: {e}")
    exit()

print(f"레이블 로딩 중: {LABELS_PATH}")
try:
    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        labels = [line.strip() for line in f.readlines()]
    print("레이블 로드 완료.")
    print(f"로딩된 레이블: {labels}")
except Exception as e:
    print(f"레이블 로드 중 오류 발생: {e}")
    exit()
