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
        self.data_dir = os.path.join(current_dir, "res", "face") # 등록된 얼굴 데이터 저장 경로
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
        self.registerd = {} # 등록된 얼굴 데이터 (이름: RecognitionData 객체)
        self.min_face = 20 # 최소 얼굴 크기 (픽셀)

        self.face_recognaze_threshold = face_recognaze_threshold # 얼굴 인식 임계값 (유사도)

        print("\n--- FaceRecognizer 모델 초기화 완료 ---")
        # print(f"모델 경로: {self.model_path}")
        # print(f"입력 텐서 모양: {self.input_details[0]['shape']}")
        # print(f"출력 텐서 모양: {self.output_details[0]['shape']}")
        # print("------------------------------------------\n")

        # 초기화 시 등록된 얼굴 데이터 불러오기
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
                    # 각 이름별 등록된 데이터 수 (data.extra.shape[0])를 추가
                    count = data.extra.shape[0] if hasattr(data, 'extra') else 0
                    registered_info.append(f"{name} ({count}개)")

                if registered_info:
                    print(f"'{self.registered_data_file}'에서 등록된 얼굴 데이터 {len(self.registerd)}명 불러오기 완료.")
                    print(f"  - 상세: {', '.join(registered_info)}")
                else:
                    print(f"'{self.registered_data_file}'에서 등록된 얼굴 데이터 {len(self.registerd)}개 불러오기 완료. (등록된 이름 없음)")
            except Exception as e:
                print(f"오류: 등록된 얼굴 데이터 불러오기 실패: {e}")
                print(f"  - 오류 내용: {e}") # 상세 오류 내용 추가
                self.registerd = {} # 실패 시 빈 딕셔너리로 초기화
        else:
            print(f"'{self.registered_data_file}' 파일이 존재하지 않습니다. 새로운 등록을 시작합니다.")

    def _save_registered_faces(self):
        """
        현재 등록된 얼굴 인식 데이터를 파일에 저장합니다.
        """
        try:
            with open(self.registered_data_file, 'wb') as f:
                pickle.dump(self.registerd, f)
            print(f"등록된 얼굴 데이터 {len(self.registerd)}개 '{self.registered_data_file}'에 저장 완료.")
        except Exception as e:
            print(f"오류: 등록된 얼굴 데이터 저장 실패: {e}")


    def __call__(self, image: np.ndarray, bboxes: list) -> np.ndarray:
        ret_names = []

        if len(bboxes) == 0:
            return np.array(ret_names)

        for idx, bbox_tuple in enumerate(bboxes):
            processed_face_img = self.__preprocess(image, (idx, bbox_tuple))

            if processed_face_img is None:
                ret_names.append('Too Small')
                continue

            image_fornet = np.expand_dims(processed_face_img, 0).astype(np.float32)

            try:
                self.model.set_tensor(self.input_details[0]['index'], image_fornet)
                self.model.invoke()
                embeedings = self.model.get_tensor(self.output_details[0]['index'])
            except Exception as e:
                print(f"RECOGNITION ERROR in FaceRecognizer: {e}")
                ret_names.append('Error')
                continue

            if len(self.registerd) > 0:
                nearest_result = self.__findNearest(embeedings)
                if nearest_result is not None:
                    name, distance = nearest_result
                    #print(distance)
                    if distance < self.face_recognaze_threshold:
                        ret_names.append(name)
                    else:
                        ret_names.append(f'Unknown') # 임계값 초과
                else:
                    ret_names.append(f'Unknown')
            else:
                ret_names.append(f'Unknown')

        return np.array(ret_names)

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

        # 해당 이름의 등록 데이터도 메모리에서 삭제
        if name in self.registerd:
            del self.registerd[name]
            self._save_registered_faces() # 변경 사항 저장
            print(f"'{name}'의 등록 정보가 메모리 및 파일에서 삭제되었습니다.")


    def RemoveAllFace(self, facePath: str = None):
        """
        해당 디렉토리의 모든 등록된 얼굴 파일과 저장된 .pkl 파일을 삭제합니다.
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

        # 메모리의 등록 정보도 초기화
        self.registerd = {}
        # 저장된 .pkl 파일도 삭제
        if os.path.exists(self.registered_data_file):
            try:
                os.remove(self.registered_data_file)
                print(f"등록 데이터 파일 '{self.registered_data_file}'도 삭제되었습니다.")
            except Exception as e:
                print(f"오류: 등록 데이터 파일 삭제 실패: {e}")


    def TrainModel(self, image: np.ndarray, bbox: list, name: str):
        processed_face_img = self.__preprocess(image, (0, bbox))

        if processed_face_img is None:
            print(f"얼굴 전처리 실패: {name}의 얼굴을 훈련(등록)할 수 없습니다.")
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
            print(f"새로운 이름 '{name}' 등록 시작.")

        self.registerd[name].distance = np.append(self.registerd[name].distance, np.array([[0.0]]), axis=0)
        self.registerd[name].extra = np.append(self.registerd[name].extra, np.array([embeedings_flat]), axis=0)

        print(f"'{name}' 얼굴 데이터 {self.registerd[name].extra.shape[0]}개 등록 완료.")
        # self._save_registered_faces() # 'r' 키 누를 때마다 저장하는 대신, 'e' 키 누를 때 저장하도록 변경
        # 이 줄은 제거되었습니다.


    def __findNearest(self, embeedings: np.ndarray) -> tuple[str, float]:
        query_emb = embeedings.flatten()

        ret_name = None
        min_distance = float('inf')

        for name, data in self.registerd.items():
            if data.extra.shape[0] > 0:
                mean_known_emb = np.mean(data.extra, axis=0) # 등록된 모든 임베딩들의 평균 사용
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