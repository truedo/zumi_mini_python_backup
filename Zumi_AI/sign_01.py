import tensorflow as tf
import numpy as np
import cv2
import os





# 1. GTSRB 클래스 라벨 정의 (가장 일반적인 GTSRB 클래스 순서)
# 모델이 이 순서대로 학습되었다고 가정합니다.
# 실제 모델의 학습 클래스 순서와 다를 경우, 결과가 정확하지 않을 수 있습니다.



# 1. GTSRB 클래스 라벨 정의 (제공해주신 모델 학습 코드 기반)
num_classes = 43 # GTSRB는 총 43개의 클래스

# Speed Class 0-9
speed_class = ['Speed Limit ' + item for item in ['20', '30', '50', '60', '70', '80']] + \
              ['End of Speed Limit 80 kmph']
speed_class += ['Speed Limit ' + item for item in ['100', '120']]

# 10, 11 No Passing
no_pass = ['No Passing' + item for item in ['', ' vehicle over 3.5 ton']]

# 12-42 (총 31개)
rest = ['Right-of-way at intersection', 'Priority road', 'Yield', 'Stop', 'No vehicles', 'Veh > 3.5 tons prohibited',
        'No entry', 'General caution', 'Dangerous curve left', 'Dangerous curve right', 'Double curve', 'Bumpy road',
        'Slippery road', 'Road narrows on the right', 'Road work', 'Traffic signals', 'Pedestrians', 'Children crossing',
        'Bicycles crossing', 'Beware of ice/snow','Wild animals crossing', 'End speed + passing limits', 'Turn right ahead',
        'Turn left ahead', 'Ahead only', 'Go straight or right', 'Go straight or left', 'Keep right', 'Keep left',
        'Roundabout mandatory', 'End of no passing', 'End no passing vehicle > 3.5 tons'] # GTSRB는 42번이 마지막 클래스입니다.

gtsrb_labels = speed_class + no_pass + rest




# 2. 모델 파일 경로 설정
model_path = 'my_model2.h5' # 다운로드 받은 .h5 파일 경로를 여기에 입력하세요.

# 3. 테스트할 이미지 파일 경로 설정
# GTSRB 데이터셋에서 표지판만 잘려진 이미지를 구하거나, 직접 표지판만 잘라낸 이미지를 사용하세요.
# 예시 이미지: GTSRB 학습 데이터셋의 일부 이미지
test_image_path = '06413.png' # 실제 테스트 이미지 파일 경로를 여기에 입력하세요.

# 테스트 이미지 준비 (예시로 사용할 이미지 생성 - 실제 사용시에는 주석 처리)
# 실제 표지판 이미지를 사용해주세요.
# cv2.imwrite('test_sign_image.png', np.zeros((32,32,3), dtype=np.uint8)) # 비어있는 이미지 생성


# 모델 로드
try:
    model = tf.keras.models.load_model(model_path)
    print(f"모델 '{model_path}' 로드 성공.")
    print("모델 입력 형태:", model.input_shape) # (None, height, width, channels) 형태일 것
    
    # 모델이 예상하는 입력 이미지 크기 추출
    # 보통 (batch_size, height, width, channels) 이므로, height와 width는 1, 2번째 인덱스
    input_height, input_width = model.input_shape[1], model.input_shape[2]
    print(f"모델은 {input_width}x{input_height} 크기의 이미지를 기대합니다.")

except Exception as e:
    print(f"오류: 모델 로드 실패. '{model_path}' 경로를 확인하거나 파일이 손상되지 않았는지 확인하세요.")
    print(f"에러 메시지: {e}")
    exit()

# 테스트 이미지 로드 및 전처리
if not os.path.exists(test_image_path):
    print(f"오류: 테스트 이미지 파일 '{test_image_path}'을 찾을 수 없습니다. 올바른 경로를 입력하세요.")
    exit()

try:
    img = cv2.imread(test_image_path)
    if img is None:
        print(f"오류: '{test_image_path}' 이미지를 읽을 수 없습니다. 파일이 유효한 이미지인지 확인하세요.")
        exit()

    # 모델이 요구하는 크기로 이미지 리사이즈
    img_resized = cv2.resize(img, (input_width, input_height))

    # 이미지 픽셀 값 정규화 (모델 학습 방식에 따라 0-1 또는 -1-1)
    # GTSRB 모델은 보통 0-1로 정규화됩니다.
    img_normalized = img_resized / 255.0 

    # 배치 차원 추가 (모델은 보통 (배치 크기, 높이, 너비, 채널) 형태의 입력을 기대)
    img_input = np.expand_dims(img_normalized, axis=0) # (1, height, width, channels)

    print(f"테스트 이미지 '{test_image_path}' 로드 및 전처리 완료. 입력 형태: {img_input.shape}")

except Exception as e:
    print(f"오류: 테스트 이미지 전처리 실패: {e}")
    exit()


# 예측 수행
try:
    predictions = model.predict(img_input)
    # predictions는 각 클래스에 대한 확률을 담고 있는 배열입니다.
    # np.argmax()를 사용하여 가장 높은 확률을 가진 클래스의 인덱스를 찾습니다.
    predicted_class_id = np.argmax(predictions[0])
    confidence = np.max(predictions[0])

    # 결과 해석
    predicted_label = gtsrb_labels[predicted_class_id]

    print("\n--- 예측 결과 ---")
    print(f"예측된 표지판: {predicted_label}")
    print(f"확률(Confidence): {confidence:.4f}")
    print(f"예측된 클래스 ID: {predicted_class_id}")






    
    # 원본 이미지와 예측 결과 함께 보여주기 (선택 사항)
    display_img = cv2.putText(img, predicted_label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    display_img = cv2.putText(display_img, f"Conf: {confidence:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("Test Result", display_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

except Exception as e:
    print(f"오류: 예측 수행 중 실패: {e}")
