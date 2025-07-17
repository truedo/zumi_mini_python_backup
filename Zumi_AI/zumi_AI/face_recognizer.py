import cv2
import mediapipe as mp
import time
import numpy as np
import os
import math
import tensorflow as tf # TensorFlow Lite Interpreter를 위해 필요
import pickle # 객체 직렬화를 위해 pickle 모듈 추가

# --- 기존 FaceRecognizer 클래스 정의 시작 ---
# 이 부분은 사용자님의 FaceRecognizer.py 파일 내용이라고 가정합니다.
# 실제 프로젝트에서는 이 클래스를 별도의 파일로 분리하고 import하여 사용하세요.

class RecognitionData:
    def __init__(self, name) -> None:
        self.name = name
        self.distance = np.empty((0,1), dtype=np.float32)
        self.extra = np.empty((0,192), dtype=np.float32) # 임베딩 차원이 192로 가정

class FaceRecognizer:
    def __init__(self, face_recognaze_threshold=0.8) -> None: # 기본 임계값 0.8로 조정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(current_dir, "res", "model", "face_recognizer.tflite")
        self.data_dir = os.path.join(current_dir, "res", "face") # 학습된 얼굴 데이터 저장 경로
        self.registered_data_file = os.path.join(self.data_dir, "registered_faces.pkl") # pickle 파일 경로

        # 데이터 저장 디렉토리 생성
        os.makedirs(self.data_dir, exist_ok=True)

        if not os.path.exists(self.model_path):
            print(f"오류: 얼굴 인식 모델 파일이 존재하지 않습니다. 경로를 확인하세요: {self.model_path}")
            raise FileNotFoundError(f"모델 파일 없음: {self.model_path}")

        try:
            self.model = tf.lite.Interpreter(model_path=self.model_path)
            self.model.allocate_tensors()
            self.trainModel = tf.lite.Interpreter(model_path=self.model_path) # trainModel도 동일 모델 사용
            self.trainModel.allocate_tensors()
        except Exception as e:
            print(f"얼굴 인식 TFLite 모델 로드 또는 텐서 할당 중 오류 발생: {e}")
            raise

        self.input_details = self.model.get_input_details()
        self.output_details = self.model.get_output_details()
        self.registerd = {} # 학습된 얼굴 데이터 (이름: RecognitionData 객체)
        self.min_face = 20 # 최소 얼굴 크기 (픽셀)

        self.face_recognaze_threshold = face_recognaze_threshold # 얼굴 인식 임계값 (유사도)

        print("\n--- FaceRecognizer 모델 초기화 완료 ---")
        # print(f"모델 경로: {self.model_path}")
        # print(f"입력 텐서 모양: {self.input_details[0]['shape']}")
        # print(f"출력 텐서 모양: {self.output_details[0]['shape']}")
        # print("------------------------------------------\n")

        # 초기화 시 학습된 얼굴 데이터 불러오기
        self._load_registered_faces()


    def _load_registered_faces(self):
        """
        저장된 얼굴 인식 데이터를 파일에서 불러옵니다.
        """
        if os.path.exists(self.registered_data_file):
            try:
                with open(self.registered_data_file, 'rb') as f:
                    self.registerd = pickle.load(f)

                registered_info = []
                for name, data in self.registerd.items():
                    # 각 이름별 학습된 데이터 수 (data.extra.shape[0])를 추가
                    count = data.extra.shape[0] if hasattr(data, 'extra') else 0
                    registered_info.append(f"{name} ({count}개)")

                if registered_info:
                    print(f"'{self.registered_data_file}'에서 학습된 얼굴 데이터 {len(self.registerd)}명 불러오기 완료.")
                    #print(f"  - 상세: {', '.join(registered_info)}")
                    for item in registered_info:
                        # Split the string to separate the name from the parenthesized count
                        parts = item.split(' (')
                        name = parts[0]

                        # Extract the count and remove the closing parenthesis
                        count = parts[1].replace(')', '')

                        print(f"    - {name}: {count}")

                else:
                    print(f"'{self.registered_data_file}'에서 학습된 얼굴 데이터 {len(self.registerd)}개 불러오기 완료. (학습된 이름 없음)")
            except Exception as e:
                print(f"오류: 학습된 얼굴 데이터 불러오기 실패: {e}")
                print(f"  - 오류 내용: {e}") # 상세 오류 내용 추가
                self.registerd = {} # 실패 시 빈 딕셔너리로 초기화
        else:
            print(f"'{self.registered_data_file}' 파일이 존재하지 않습니다. 새로운 등록을 시작합니다.")

    def _save_registered_faces(self):
        """
        현재 학습된 얼굴 인식 데이터를 파일에 저장합니다.
        """
        try:
            with open(self.registered_data_file, 'wb') as f:
                pickle.dump(self.registerd, f)
            print(f"학습된 얼굴 데이터 {len(self.registerd)}개 '{self.registered_data_file}'에 저장 완료.")
        except Exception as e:
            print(f"오류: 학습된 얼굴 데이터 저장 실패: {e}")


    def __call__(self, image: np.ndarray, bboxes: list) -> list[tuple[str, float]]: # 반환 타입을 수정
        ret_results = [] # (이름, 신뢰도) 튜플을 저장할 리스트

        if len(bboxes) == 0:
            return ret_results

        for idx, bbox_tuple in enumerate(bboxes):
            processed_face_img = self.__preprocess(image, (idx, bbox_tuple))

            if processed_face_img is None:
                ret_results.append(('Too Small', 0.0)) # 너무 작은 경우 신뢰도 0으로 반환
                continue

            image_fornet = np.expand_dims(processed_face_img, 0).astype(np.float32)

            try:
                self.model.set_tensor(self.input_details[0]['index'], image_fornet)
                self.model.invoke()
                embeedings = self.model.get_tensor(self.output_details[0]['index'])
            except Exception as e:
                print(f"RECOGNITION ERROR in FaceRecognizer: {e}")
                ret_results.append(('Error', 0.0)) # 오류 발생 시 신뢰도 0으로 반환
                continue

            if len(self.registerd) > 0:
                nearest_result = self.__findNearest(embeedings)
                if nearest_result is not None:
                    name, distance = nearest_result
                    # 거리(distance)를 신뢰도(0.0 ~ 1.0)로 변환하는 로직 추가
                    # 예를 들어, (1 - distance / 임계값_최대_거리) 같은 형태로 변환 가능
                    # 여기서는 간단하게 임계값에 대한 상대적인 값으로 표현하거나, distance 자체를 신뢰도로 해석

                    # distance가 낮을수록 신뢰도가 높으므로, 간단하게 1 - (distance / (최대_거리_가정))
                    # 혹은 그냥 distance 값을 신뢰도로 보고 사용자에게 임계값과의 비교를 맡길 수도 있습니다.

                    # 여기서는 distance를 그대로 반환하고, 외부에서 임계값과 비교하여 해석하도록 합니다.
                    # 또는 다음과 같이 신뢰도를 '역거리' 개념으로 맵핑할 수 있습니다.
                    # threshold = self.face_recognaze_threshold
                    # confidence = max(0, 1 - (distance / threshold)) # 임계값 내에서는 0~1 사이 값
                    # 이 방법은 threshold를 넘어서면 음수가 될 수 있으므로, 아래와 같이 조정합니다.

                    # 좀 더 직관적인 신뢰도 점수 (threshold 값에 기반)
                    if distance < self.face_recognaze_threshold:
                        # 임계값 이내일 경우, 거리가 짧을수록 높은 신뢰도
                        # 예를 들어, 0 ~ self.face_recognaze_threshold 범위의 거리를 1 ~ 0 범위의 신뢰도로 변환
                        # 0.0 (최소 거리) -> 1.0 (최고 신뢰도)
                        # self.face_recognaze_threshold (최대 허용 거리) -> 0.0 (최저 허용 신뢰도)
                        # confidence = 1 - (distance / self.face_recognaze_threshold)
                        confidence = 1 - (distance / 2.0) # 최대 예상 거리를 2.0 정도로 가정하고 정규화
                        # 만약 distance가 0이면 confidence는 1.0, distance가 2.0이면 confidence는 0.0
                        confidence = max(0.0, min(1.0, confidence)) # 0~1 범위로 클리핑
                        ret_results.append((name, confidence))
                    else:
                        ret_results.append(('Unknown', 0.0)) # 임계값 초과 시 신뢰도 0
                else:
                    ret_results.append(('Unknown', 0.0)) # 가장 가까운 얼굴을 찾지 못한 경우
            else:
                ret_results.append(('Unknown', 0.0)) # 등록된 얼굴이 없는 경우

        return ret_results # np.array 대신 list 반환 (튜플 포함)

    def __preprocess(self, image: np.ndarray, bb: tuple) -> np.ndarray:
        bbox = bb[1]
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

        bbox_width = x2 - x1
        bbox_height = y2 - y1

        if bbox_width <= self.min_face or bbox_height <= self.min_face:
            return None

        add_pad = int(max(bbox_width, bbox_height) * 0.5)

        bimg = cv2.copyMakeBorder(image, add_pad, add_pad, add_pad, add_pad,
                                  borderType=cv2.BORDER_CONSTANT, value=[127, 127, 127])

        x1_padded = x1 + add_pad
        y1_padded = y1 + add_pad
        x2_padded = x2 + add_pad
        y2_padded = y2 + add_pad

        face_width_extended = int((1 + 2 * 0.2) * bbox_width)
        face_height_extended = int((1 + 2 * 0.2) * bbox_height)

        center_x = (x1_padded + x2_padded) // 2
        center_y = (y1_padded + y2_padded) // 2

        crop_x1 = max(0, center_x - face_width_extended // 2)
        crop_y1 = max(0, center_y - face_height_extended // 2)
        crop_x2 = min(bimg.shape[1], center_x + face_width_extended // 2)
        crop_y2 = min(bimg.shape[0], center_y + face_height_extended // 2)

        crop_image = bimg[crop_y1:crop_y2, crop_x1:crop_x2, :]

        if crop_image.shape[0] == 0 or crop_image.shape[1] == 0:
            return None

        crop_image = cv2.resize(crop_image, (112, 112))

        return crop_image

    def SaveFace(self, image: np.ndarray, bbox: list, name: str, facePath: str = None):
        if facePath is None:
            facePath = self.data_dir # 기본 저장 경로 사용

        os.makedirs(facePath, exist_ok=True)

        if not os.path.isdir(facePath):
            print(f"{facePath} is not a valid directory.")
            return -1

        if not name:
            print("Name parameter is Empty.")
            return -1

        dataCnt = 0
        for filename in os.listdir(facePath):
            if name in filename:
                dataCnt += 1

        processed_img = self.__preprocess(image, (0, bbox))

        if processed_img is None:
            print(f"얼굴 전처리 실패: {name}의 얼굴을 저장할 수 없습니다.")
            return -1

        save_path = os.path.join(facePath, f"{name}_{dataCnt}.jpg")
        cv2.imwrite(save_path, processed_img)
        print(f"얼굴 저장됨: {save_path}")
        return 0

    def RemoveFace(self, name: str, facePath: str = None):
        if facePath is None:
            facePath = self.data_dir # 기본 저장 경로 사용

        if not os.path.isdir(facePath):
            print(f"{facePath} is not a valid directory.")
            return -1

        if not name:
            print("Name parameter is Empty.")
            return -1

        deleted_count = 0
        for filename in os.listdir(facePath):
            if filename.startswith(f"{name}_"):
                try:
                    file_to_delete = os.path.join(facePath, filename)
                    os.remove(file_to_delete)
                    print(f"파일 삭제됨: {file_to_delete}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete file: {file_to_delete} - {e}")
        print(f"{deleted_count} files for '{name}' have been deleted.")

        # 해당 이름의 학습 데이터도 메모리에서 삭제
        if name in self.registerd:
            del self.registerd[name]
            self._save_registered_faces() # 변경 사항 저장
            print(f"'{name}'의 학습 정보가 메모리 및 파일에서 삭제되었습니다.")


    def RemoveAllFace(self, facePath: str = None):
        """
        해당 디렉토리의 모든 학습된 얼굴 파일과 저장된 .pkl 파일을 삭제합니다.
        서브디렉토리는 삭제하지 않습니다.
        """
        if facePath is None:
            facePath = self.data_dir # 기본 저장 경로 사용

        if not os.path.isdir(facePath):
            print(f"{facePath} is not a valid directory.")
            return -1

        deleted_files = 0
        for filename in os.listdir(facePath):
            file_path = os.path.join(facePath, filename)
            if os.path.isfile(file_path): # 파일만 삭제, 서브디렉토리 제외
                try:
                    os.remove(file_path)
                    deleted_files += 1
                except Exception as e:
                    print(f"Failed to delete file: {file_path} - {e}")

        print(f"{deleted_files} files have been deleted from {facePath}.")

        # 메모리의 학습 정보도 초기화
        self.registerd = {}
        # 저장된 .pkl 파일도 삭제
        if os.path.exists(self.registered_data_file):
            try:
                os.remove(self.registered_data_file)
                print(f"학습 데이터 파일 '{self.registered_data_file}'도 삭제되었습니다.")
            except Exception as e:
                print(f"오류: 학습 데이터 파일 삭제 실패: {e}")


    def TrainModel(self, image: np.ndarray, bbox: list, name: str):
        processed_face_img = self.__preprocess(image, (0, bbox))

        if processed_face_img is None:
            print(f"얼굴 전처리 실패: {name}의 얼굴을 훈련(학습)할 수 없습니다.")
            return

        image_fornet = np.expand_dims(processed_face_img, 0).astype(np.float32)

        try:
            self.trainModel.set_tensor(self.input_details[0]['index'], image_fornet)
            self.trainModel.invoke()
            embeedings = self.trainModel.get_tensor(self.output_details[0]['index'])
            embeedings_flat = embeedings.flatten()
        except Exception as e:
            print(f"TRAIN MODEL ERROR: {e}")
            return

        if name not in self.registerd:
            self.registerd[name] = RecognitionData(name)
            print(f"새로운 이름 '{name}' 학습 시작.")

        self.registerd[name].distance = np.append(self.registerd[name].distance, np.array([[0.0]]), axis=0)
        self.registerd[name].extra = np.append(self.registerd[name].extra, np.array([embeedings_flat]), axis=0)

        print(f"'{name}' 얼굴 데이터 {self.registerd[name].extra.shape[0]}개 학습 완료.")
        # self._save_registered_faces() # 'r' 키 누를 때마다 저장하는 대신, 'e' 키 누를 때 저장하도록 변경
        # 이 줄은 제거되었습니다.


    def __findNearest(self, embeedings: np.ndarray) -> tuple[str, float]:
        query_emb = embeedings.flatten()

        ret_name = None
        min_distance = float('inf')

        for name, data in self.registerd.items():
            if data.extra.shape[0] > 0:
                mean_known_emb = np.mean(data.extra, axis=0) # 학습된 모든 임베딩들의 평균 사용
                distance = np.linalg.norm(query_emb - mean_known_emb)
            else:
                continue

            if ret_name is None or distance < min_distance:
                min_distance = distance
                ret_name = name

        if ret_name is None:
            return None

        return (ret_name, min_distance)

# --- FaceRecognizer 클래스 정의 끝 ---