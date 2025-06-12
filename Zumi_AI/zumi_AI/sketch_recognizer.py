import math
import cv2
import os
import numpy as np
from numpy.core.defchararray import array
from tensorflow.python.eager.context import disable_graph_collection
import pkg_resources
import pickle # pickle 모듈 임포트
from collections import Counter # Counter 모듈 임포트

class SketchProcessor:

    # 학습 데이터 저장 파일 이름
    # 이 파일은 self.sketchPath 내부에 저장됩니다.
    TRAINING_DATA_FILE = "sketch_training_data.pkl"

    def __init__(self) -> None:

        self.orbDetector = cv2.ORB_create()
        self.matcherHamming = cv2.DescriptorMatcher_create(cv2.DescriptorMatcher_BRUTEFORCE_HAMMINGLUT)

        self.sketchPath = pkg_resources.resource_filename(__package__,"res/sketch/")
        if os.path.exists(self.sketchPath) is False:
            os.makedirs(self.sketchPath)

        # 학습된 스케치 데이터를 저장할 변수 초기화
        self.orbDescriptors = []
        self.nameIndexList = []
        self.nameIntList = []

        # 실시간 학습을 위해 캡처된 특징점과 이름을 임시로 저장할 리스트 추가
        self.captured_descriptors = []
        self.captured_names = []
        self.unique_names_map = {} # 고유 이름에 대한 인덱스 맵
        self.current_unique_idx = 0

        # -----------------------------------------------------------------------
        # 추가: 객체 초기화 시 학습 데이터 로드 시도
        self.load_training_data()
        # -----------------------------------------------------------------------

    def __call__(self, image):
        retName = np.array([])
        retRect = np.empty((1,4,2), dtype=int)
        retConfidence = np.array([]) # 신뢰도 반환을 위한 배열 추가

        h,w,c = image.shape
        sketchImage = None

        kernel = np.ones((3,3), np.uint8)

        processedImg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processedImg = cv2.pyrDown(processedImg)
        processedImg = cv2.pyrUp(processedImg)
        processedImg = cv2.Canny(processedImg,0,100)
        processedImg = cv2.dilate(processedImg, kernel, anchor=(-1,1), iterations=1)

        contours, hierarchy = cv2.findContours(processedImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < 2500 or area > 75000:
                continue

            approx = cv2.approxPolyDP(contour, cv2.arcLength(contour, True) * 0.02, True)
            edge = len(approx)

            if edge == 4 and cv2.isContourConvex(approx):
                approx = approx.reshape (4,2)
                src_pts = np.array([ approx[1],approx[0],approx[2],approx[3] ], dtype=np.float32)
                dst_pts = np.array([[0,0],[w,0],[0,h],[w,h]], dtype=np.float32)
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                sketchImage = cv2.warpPerspective(processedImg, M, (w,h))
                retRect = np.append(retRect, np.array([approx]), axis=0)
                break

        if sketchImage is not None:
            if len(self.matcherHamming.getTrainDescriptors()) > 0:
                sketchImage = cv2.resize(sketchImage, (150,150))
                _, des = self.orbDetector.detectAndCompute(sketchImage, None)

                #idx = self.__checkMatches(des)
                idx, confidence = self.__checkMatches(des) # 신뢰도 값도 함께 받아옴
                if idx != -1:
                    retName = np.append(retName, np.array([self.nameIndexList[idx]]), axis=0)
                    retConfidence = np.append(retConfidence, np.array([confidence]), axis=0) # 신뢰도 추가
                else:
                    retName = np.append(retName, np.array(['Sketch']), axis=0)
                    retConfidence = np.append(retConfidence, np.array([0.0]), axis=0) # 인식 실패 시 신뢰도 0

            else:
                retName = np.append(retName, np.array(['Sketch']), axis=0)
                retConfidence = np.append(retConfidence, np.array([0.0]), axis=0) # 학습된 데이터 없을 시 신뢰도 0

        retRect = np.delete(retRect, [0, 0], axis=0)
        #return retName, retRect
        return retName, retRect, retConfidence # 신뢰도도 반환하도록 변경

    # 새롭게 추가되거나 변경된 메서드
    # ----------------------------------------------------------------------------------

    def _capture_and_process_image(self, image):
        """
        주어진 이미지에서 스케치를 캡처하고 전처리하여 특징점을 추출합니다.
        SaveSketch와 __call__에서 공통으로 사용되는 이미지 처리 로직을 캡슐화합니다.
        """

        h,w,c = image.shape
        sketchImage = None

        kernel = np.ones((3,3), np.uint8)

        processedImg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processedImg = cv2.pyrDown(processedImg)
        processedImg = cv2.pyrUp(processedImg)
        processedImg = cv2.Canny(processedImg,0,100)
        processedImg = cv2.dilate(processedImg, kernel, anchor=(-1,1), iterations=1)

        contours, hierarchy = cv2.findContours(processedImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

        for contour in contours:
            area = abs( cv2.contourArea(contour) )

            if area < 2500 or area > 75000:
                continue

            approx = cv2.approxPolyDP(contour, cv2.arcLength(contour, True) * 0.02, True)
            edge = len(approx)

            if edge == 4 and cv2.isContourConvex(approx):
                approx = approx.reshape (4,2)
                if approx[1][1] < approx[3][1]:
                    src_pts = np.array([ approx[1],approx[0],approx[2],approx[3] ], dtype=np.float32)
                else:
                    src_pts = np.array([ approx[0],approx[3],approx[1],approx[2] ], dtype=np.float32)

                dst_pts = np.array([[0,0],[w,0],[0,h],[w,h]], dtype=np.float32)
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                sketchImage = cv2.warpPerspective(processedImg, M, (w,h))

                return sketchImage

        #return sketchImage
        return None # 스케치를 찾지 못했으면 None 반환

    def add_sketch_for_training(self, image, name: str):
        """
        새로운 스케치 이미지를 학습 데이터셋에 추가합니다.
        """
        if not name:
            print("이름 파라미터가 비어 있습니다.")
            return -1

        processed_sketch = self._capture_and_process_image(image)

        if processed_sketch is not None:
            resized_sketch = cv2.resize(processed_sketch, (150, 150))

            # 특징점 추출
            _, des = self.orbDetector.detectAndCompute(resized_sketch, None)

            if des is not None:
                self.captured_descriptors.append(des)
                self.captured_names.append(name)

                # 고유 이름 인덱싱 업데이트
                if name not in self.unique_names_map:
                    self.unique_names_map[name] = self.current_unique_idx
                    self.current_unique_idx += 1

                # nameIntList는 TrainModel에서 일괄 생성

                # 변경된 부분: 이름별 추가된 스케치 수 출력
                name_counts = Counter(self.captured_names)
                print(f"'{name}' 스케치 데이터 {name_counts[name]}개 학습 완료.")
                #print(f"✔️ '{name}' 스케치 추가됨.")
                #print(f"   - 현재 '{name}' 스케치 개수: {name_counts[name]}개")


                #print(f"   - 전체 학습 대기 스케치 수: {len(self.captured_descriptors)}개")
                return 0 # 성공
            else:
                print(f"경고: '{name}' 스케치에서 특징점을 추출하지 못했습니다.")
                return -1
        else:
            print("스케치 이미지에서 유효한 사각형을 찾을 수 없습니다.")
            return -1


    def train_from_captured_data(self):
        """
        현재까지 캡처된 스케치 데이터를 사용하여 모델을 학습합니다.
        """
        if not self.captured_descriptors:
            print("학습할 스케치 데이터가 없습니다.")
            return

        # nameIntList를 `self.captured_names`와 `self.unique_names_map`을 기반으로 생성
        nameIntList = [self.unique_names_map[name] for name in self.captured_names]

        # SketchProcessor 내부의 TrainModel 메서드 호출
        self.TrainModel(self.captured_names, nameIntList, self.captured_descriptors)
        #print(f"전체 스케치 모델 학습 완료. 학습된 스케치 개수: {len(self.captured_descriptors)}")
        # -----------------------------------------------------------------------
        # 추가: 학습이 완료되면 데이터 저장
        self.save_training_data()
        # -----------------------------------------------------------------------

    # ----------------------------------------------------------------------------------

    def TrainModel(self, nameIndexList:list, nameIntList:list, orbDescriptors:list):
        """
        모델을 학습하는 핵심 메서드.
        매칭기에 특징점 데이터를 추가하고 학습시킵니다.
        """
        self.orbDescriptors = orbDescriptors.copy()
        self.nameIndexList = nameIndexList.copy()
        self.nameIntList = nameIntList.copy()
        self.matcherHamming.clear() # 기존 훈련 데이터 클리어

        if len(self.orbDescriptors) > 0:
            self.matcherHamming.add(self.orbDescriptors)
            self.matcherHamming.train()
            #print("매칭기 학습 완료.")
        else:
            print("학습할 특징점 데이터가 없어 학습할수 없습니다.")

    def __checkMatches(self, descriptor):
        matchIdx = -1
        best_confidence = 0.0

        if len(self.matcherHamming.getTrainDescriptors()) == 0:
            return -1, 0.0

        if descriptor is None or len(descriptor) == 0:
            return -1, 0.0

        # 매칭 임계값. 이 값을 조절하여 매칭의 엄격도를 제어할 수 있습니다.
        # ORB/Hamming 거리에서 50은 비교적 관대한 편입니다.
        # 더 엄격하게 하려면 값을 낮추세요 (예: 40, 35)
        MATCH_DISTANCE_THRESHOLD = 45 # 이전 논의에서 제안된 값 사용 (조정 가능)

        for idx, trainDescriptor in enumerate(self.matcherHamming.getTrainDescriptors()):
            if trainDescriptor is None or len(trainDescriptor) == 0:
                continue

            matches = self.matcherHamming.match(descriptor, trainDescriptor)

            if not matches:
                continue

            # 좋은 매칭의 개수를 셉니다.
            good_matches_count = sum(1 for dMatch in matches if dMatch.distance <= MATCH_DISTANCE_THRESHOLD)

            # 신뢰도 계산:
            # 쿼리 이미지의 특징점 수와 학습된 모델의 특징점 수 중 더 작은 값을 기준으로 합니다.
            # 이렇게 하면 특징점 수가 크게 다른 경우에도 신뢰도가 합리적으로 계산됩니다.
            max_possible_matches = min(len(descriptor), len(trainDescriptor))

            current_confidence = 0.0
            if max_possible_matches > 0:
                # 0.0 ~ 1.0 사이의 값으로 계산합니다.
                current_confidence = good_matches_count / max_possible_matches
                # 소수점 두 자리로 반올림
                current_confidence = round(current_confidence, 2)

            # 현재까지의 최고 신뢰도를 갱신합니다.
            if current_confidence > best_confidence:
                best_confidence = current_confidence
                matchIdx = idx

        return matchIdx, best_confidence

    def __angle(self, pt1:array, pt2:array, pt0:array):
        # 이 함수는 현재 스케치 인식 로직에서 직접 사용되지 않으므로 유지합니다.
        abx1 = pt1[0] - pt0[0]
        aby1 = pt1[1] - pt0[1]
        cbx2 = pt2[0] - pt0[0]
        cby2 = pt2[1] - pt0[1]

        dot = abx1*cbx2 + aby1*cby2
        cross = abx1*cby2 - aby1*cbx2

        alpha = math.atan2(cross,dot)

        return int(math.floor( alpha * 180.0) / 3.1415926535897932384626433832795 + 0.5)

 # -----------------------------------------------------------------------
    # 추가: 학습 데이터 저장 및 로드 메서드

    def save_training_data(self):
        """
        현재 학습된 orbDescriptors, nameIndexList, nameIntList,
        그리고 captured_descriptors, captured_names, unique_names_map을 파일로 저장합니다.
        """
        data_to_save = {
            'orbDescriptors': self.orbDescriptors,
            'nameIndexList': self.nameIndexList,
            'nameIntList': self.nameIntList,
            'captured_descriptors': self.captured_descriptors, # 실시간 학습을 위해 캡처된 데이터도 저장
            'captured_names': self.captured_names,             # 다음 실행 시 이어서 학습 가능
            'unique_names_map': self.unique_names_map,
            'current_unique_idx': self.current_unique_idx
        }

        file_path = os.path.join(self.sketchPath, self.TRAINING_DATA_FILE)

        try:
            with open(file_path, 'wb') as f:
                pickle.dump(data_to_save, f)
            print(f"학습 데이터가 '{file_path}'에 성공적으로 저장되었습니다.")
        except Exception as e:
            print(f"학습 데이터 저장 중 오류 발생: {e}")

    def load_training_data(self):
        file_path = os.path.join(self.sketchPath, self.TRAINING_DATA_FILE)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    loaded_data = pickle.load(f)

                self.orbDescriptors = loaded_data.get('orbDescriptors', [])
                self.nameIndexList = loaded_data.get('nameIndexList', [])
                self.nameIntList = loaded_data.get('nameIntList', [])
                self.captured_descriptors = loaded_data.get('captured_descriptors', [])
                self.captured_names = loaded_data.get('captured_names', [])
                self.unique_names_map = loaded_data.get('unique_names_map', {})
                self.current_unique_idx = loaded_data.get('current_unique_idx', 0)

                if self.orbDescriptors:
                    self.matcherHamming.clear()
                    self.matcherHamming.add(self.orbDescriptors)
                    self.matcherHamming.train()

                    # -------------------------------------------------------------------
                    # 변경: 로드된 학습 데이터에 대한 정보 출력
                    #print(f"✔️ '{file_path}'에서 학습된 스케치 데이터 불러오기 완료.")
                    #print(f"   - 총 학습된 스케치 개수: {len(self.orbDescriptors)}개")

                    # 각 스케치 이름별 개수를 세어 출력
                    if self.nameIndexList:
                        name_counts = Counter(self.nameIndexList)
                        print(f"✔️ '{file_path}'에서 학습된 스케치 데이터 {len(name_counts.items())}개 불러오기 완료.")
                        #print(f"   - 학습된 스케치 개수:")
                        for name, count in sorted(name_counts.items()): # 이름 순으로 정렬하여 출력
                            print(f"     - {name}: {count}개")
                    else:
                        print(f"   - 학습된 스케치 종류: 없음")
                    # -------------------------------------------------------------------
                else:
                    print("⚠️ 로드된 학습 데이터가 없거나 비어 있습니다. 매칭기를 학습하지 않았습니다.")

            except Exception as e:
                print(f"❌ 학습 데이터 로드 중 오류 발생: {e}")
                self.orbDescriptors = []
                self.nameIndexList = []
                self.nameIntList = []
                self.captured_descriptors = []
                self.captured_names = []
                self.unique_names_map = {}
                self.current_unique_idx = 0
        else:
            print(f"ℹ️ 저장된 학습 데이터 파일 '{file_path}'을 찾을 수 없습니다. 새로운 학습을 시작합니다.")

    ## New Deletion Functions

    def delete_model_by_name(self, name: str):
        """
        특정 이름을 가진 스케치 모델의 모든 학습 데이터를 삭제합니다.
        삭제 후 매칭기를 재학습하고 변경사항을 저장합니다.
        """
        if not name:
            print("🚫 삭제할 모델의 이름을 입력해주세요.")
            return

        initial_total_descriptors = len(self.orbDescriptors) + len(self.captured_descriptors)

        # 1. captured_data (학습 대기 중인 데이터)에서 삭제
        new_captured_descriptors = []
        new_captured_names = []
        deleted_from_captured = 0
        for i in range(len(self.captured_names)):
            if self.captured_names[i] != name:
                new_captured_descriptors.append(self.captured_descriptors[i])
                new_captured_names.append(self.captured_names[i])
            else:
                deleted_from_captured += 1

        self.captured_descriptors = new_captured_descriptors
        self.captured_names = new_captured_names

        # 2. orbDescriptors (이미 학습된 데이터)에서 삭제
        new_orbDescriptors = []
        new_nameIndexList = []
        new_nameIntList = []
        deleted_from_trained = 0

        # unique_names_map에서 해당 이름을 제거하고 다시 매핑합니다.
        # 이전에 매핑된 인덱스가 변경될 수 있으므로, nameIntList를 다시 생성해야 합니다.
        temp_unique_names = set(self.nameIndexList) - {name}
        temp_unique_names.update(set(self.captured_names)) # captured_names에도 남은 이름이 있을 수 있으므로 추가

        self.unique_names_map = {n: i for i, n in enumerate(sorted(list(temp_unique_names)))}
        self.current_unique_idx = len(self.unique_names_map)

        for i in range(len(self.nameIndexList)):
            if self.nameIndexList[i] != name:
                new_orbDescriptors.append(self.orbDescriptors[i])
                new_nameIndexList.append(self.nameIndexList[i])
                new_nameIntList.append(self.unique_names_map[self.nameIndexList[i]]) # 새 인덱스 적용
            else:
                deleted_from_trained += 1

        self.orbDescriptors = new_orbDescriptors
        self.nameIndexList = new_nameIndexList
        self.nameIntList = new_nameIntList

        total_deleted = deleted_from_captured + deleted_from_trained

        if total_deleted > 0:
            print(f"🗑️ 모델 '{name}'에 대한 학습 데이터 {total_deleted}개를 삭제했습니다.")
            if deleted_from_captured > 0:
                print(f"   - 학습 대기 중인 데이터 {deleted_from_captured}개 삭제됨.")
            if deleted_from_trained > 0:
                print(f"   - 이미 학습된 데이터 {deleted_from_trained}개 삭제됨.")

            # 삭제 후 매칭기 재학습
            print("매칭기를 재학습합니다...")
            self.TrainModel(self.nameIndexList, self.nameIntList, self.orbDescriptors)
            self.save_training_data()
            print("✅ 모델 삭제 및 재학습, 데이터 저장이 완료되었습니다.")
        else:
            print(f"ℹ️ 모델 '{name}'을(를) 찾을 수 없거나 삭제할 데이터가 없습니다.")

    def clear_all_models(self):
        """
        모든 학습된 스케치 모델과 캡처된 스케치 데이터를 완전히 초기화합니다.
        초기화 후 변경사항을 저장합니다.
        """
        print("🚨 모든 스케치 모델 및 학습 데이터 초기화를 시작합니다...")
        self.orbDescriptors = []
        self.nameIndexList = []
        self.nameIntList = []
        self.captured_descriptors = []
        self.captured_names = []
        self.unique_names_map = {}
        self.current_unique_idx = 0

        self.matcherHamming.clear() # 매칭기 데이터도 클리어

        self.save_training_data()
        print("✨ 모든 스케치 모델과 학습 데이터가 성공적으로 초기화되고 저장되었습니다.")

