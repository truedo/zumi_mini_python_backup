from posixpath import basename
import numpy as np
import cv2
import tensorflow as tf
import os
import math
import pkg_resources

class RecognitionData:
    def __init__(self, name) -> None:
        self.name = name
        self.distance = np.empty((0,1), dtype=np.float32)
        self.extra = np.empty((0,192), dtype=np.float32)

class FaceRecognizer:
    def __init__(self, face_recognaze_threshold=0.2) -> None:
        self.model_path = pkg_resources.resource_filename(__package__,"res/model/face_recognizer.tflite")
        self.model = tf.lite.Interpreter(model_path=self.model_path)
        self.model.allocate_tensors()
        self.trainModel = tf.lite.Interpreter(model_path=self.model_path)
        self.trainModel.allocate_tensors()
        self.input_details = self.model.get_input_details()
        self.output_details = self.model.get_output_details()
        self.registerd = {}
        self.min_face = 20

        self.face_recognaze_threshold = face_recognaze_threshold

    def __call__(self, image, bboxes) -> np.array:
        ret = np.array([])
        idx = 0
        if len(bboxes) == 0:
            return ret

        for bbox in enumerate(bboxes):
            image_fornet = self.__preprocess(image,bbox)
            image_fornet = np.expand_dims(image_fornet, 0).astype(np.float32)

            try:
                self.model.set_tensor(self.input_details[0]['index'], image_fornet)
                self.model.invoke()
                embeedings = self.model.get_tensor(self.output_details[0]['index'])
            except Exception as e:
                print("RECO : " , e)
                return ret

            if len(self.registerd) > 0:
                #print("reg")
                nearest = self.__findNearest(embeedings)
                #print(nearest)
                if nearest is not None:
                    if nearest[1] < self.face_recognaze_threshold:
                        ret = np.append(ret, np.array([nearest[0]]))
                    else:
                        ret = np.append(ret, np.array(['Human' + str(idx)]))
            else:
                #print("not reg")
                ret = np.append(ret, np.array(['Human' + str(idx)]))

            idx += 1

        return ret

    def __preprocess(self, image, bb):
        bbox = bb[1]
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        if bbox_width <= self.min_face or bbox_height <= self.min_face:
            return None, None
        add = int(max(bbox_width, bbox_height))
        bimg = cv2.copyMakeBorder(image, add, add, add, add,borderType=cv2.BORDER_CONSTANT,value=np.array([127., 127., 127.]))
        bbox += add

        face_width = (1 + 2 * 0.2) * bbox_width
        center = [(bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2]

        bbox[0] = center[0] - face_width // 2
        bbox[1] = center[1] - face_width // 2
        bbox[2] = center[0] + face_width // 2
        bbox[3] = center[1] + face_width // 2

        bbox = bbox.astype(np.int32)
        crop_image = bimg[bbox[1]:bbox[3], bbox[0]:bbox[2], :]
        crop_image = cv2.resize(crop_image, (112, 112))

        return crop_image

    def SaveFace(self, image, bbox, name:str, facePath:str=pkg_resources.resource_filename(__package__,"res/face/")):
        if os.path.isdir(facePath) is False:
            print(facePath +" is not directory.")
            return -1

        if bool(name) is False:
            print("Name parameter is Empty.")
            return -1

        dataCnt = 0
        for filename in os.listdir(facePath):
            if name in filename:
                dataCnt += 1

        cropImg = self.__preprocess(image,bbox)

        cv2.imwrite(facePath+name+'_'+str(dataCnt)+'.jpg', cropImg)
        return 0

    def RemoveFace(self, name, facePath:str='.res/face/'):
        if os.path.isdir(facePath) is False:
            print(facePath +" is not directory.")
            return -1

        if bool(name) is False:
            print("Name parameter is Empty.")
            return -1

        for filename in os.listdir(facePath):
            basename = os.path.basename(filename)
            if name == basename.split('_')[0]:
                try:
                    os.remove(facePath+filename)
                except Exception as e:
                    print(f"Failed to delete file: {facePath+filename} - {e}")

    def RemoveAllFace(self, facePath:str='.res/face/'):
        """
        해당 디렉토리의 모든 파일을 삭제합니다.
        서브디렉토리는 삭제하지 않습니다.
        """

        if not os.path.isdir(facePath):
            print(facePath +"is not directory.")
            return -1

        deleted_files = 0
        for filename in os.listdir(facePath):
            try:
                os.remove(facePath+filename)
                deleted_files += 1
            except Exception as e:
                print(f"Failed to delete file: {facePath+filename} - {e}")

        print(f"{deleted_files} have deleted the files.")


    def TrainModel(self, image, bbox, name):
        self.registerd = {}
        image_fornet = self.__preprocess(image, bbox)
        image_fornet = np.expand_dims(image_fornet, 0).astype(np.float32)
        try:
            self.trainModel.set_tensor(self.input_details[0]['index'], image_fornet)
            self.trainModel.invoke()
            embeedings = self.trainModel.get_tensor(self.output_details[0]['index'])

        except Exception as e:
            print(e)
            return


        if len(self.registerd) > 0:
            #print("len>0")
            nearest = self.__findNearest(embeedings)
            if nearest is not None:
                if name in self.registerd:
                    ret = self.registerd[name]
                else:
                    ret = RecognitionData(name)
                ret.distance = np.append( ret.distance ,np.array([[0.0]]) , axis=0)
                ret.extra = np.append( ret.extra, np.array([embeedings.flatten()]), axis=0)
                self.registerd[name] = ret

        else:
            #print("len:else")
            ret = RecognitionData(name)
            ret.distance = np.append( ret.distance ,np.array([[0.0]]), axis=0)
            ret.extra = np.append( ret.extra, np.array([embeedings.flatten()]), axis=0)
            self.registerd[name] = ret

            #print(self.registerd[name])
            #print(ret.extra)
            #print(ret.distance)
            #print("")



    def __findNearest(self, embeedings:np.ndarray):
        emb = embeedings.flatten()

        ret = None
        for key, val in self.registerd.items():
            name = key
            distance = 0.

            for ext in val.extra:

                knownEmb = ext.flatten()
                for i in range(0, len(emb)):
                    diff = emb[i] - knownEmb[i]
                    distance += diff * diff

                distance = math.sqrt(distance)

                if ret is None or distance < ret[1]:
                    ret = (name, distance)

        return ret