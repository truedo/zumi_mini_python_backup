# -*-coding:utf-8-*-
import tensorflow as tf
import cv2
import numpy as np
import pkg_resources

class FaceLandmark:
    """
           the model was constructed by the params in config.py
    """

    def __init__(self):
        self.model_path = pkg_resources.resource_filename(__package__,"res/model/face_keypoints.tflite")
        self.min_face = 20
        self.keypoints_num = 68

        self.model = tf.lite.Interpreter(model_path=self.model_path)
        self.model.allocate_tensors()
        self.input_details = self.model.get_input_details()
        self.output_details = self.model.get_output_details()
        self.tflite=True


    ##below are the method  run for one by one, will be deprecated in the future
    def __call__(self, img, bboxes):
        '''
        should be batched process
        but process one by one, more simple
        :param img:
        :param bboxes:
        :return: landmark and some cls results
        '''

        landmark_result = []
        states_result = []

        for bbox in enumerate(bboxes):

            image_croped, detail = self.preprocess(img, bbox)

            ##inference
            image_croped = np.expand_dims(image_croped, axis=0)
            image_croped = image_croped.astype(np.float32)
            self.model.set_tensor(self.input_details[0]['index'], image_croped)
            self.model.invoke()

            landmark = self.model.get_tensor(self.output_details[2]['index']).reshape((-1, self.keypoints_num, 2))
            states = self.model.get_tensor(self.output_details[0]['index'])

            landmark = self.postprocess(landmark, detail)

            if landmark is not None:
                landmark_result.append(landmark)
                states_result.append(states)

        return np.array(landmark_result), np.array(states_result)

    def preprocess(self, image, param_bbox):
        """
        :param image: raw image
        :param bbox: the bbox for the face
        :param i: index of face
        :return:
        """
        bbox = param_bbox[1]
        ##preprocess
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        if bbox_width <= self.min_face or bbox_height <= self.min_face:
            return None, None
        add = int(max(bbox_width, bbox_height))
        bimg = cv2.copyMakeBorder(image, add, add, add, add,
                                  borderType=cv2.BORDER_CONSTANT,
                                  value=np.array([127., 127., 127.]))
        bbox += add

        face_width = (1 + 2 * 0.2) * bbox_width
        center = [(bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2]

        ### make the box as square
        bbox[0] = center[0] - face_width // 2
        bbox[1] = center[1] - face_width // 2
        bbox[2] = center[0] + face_width // 2
        bbox[3] = center[1] + face_width // 2

        # crop
        bbox = bbox.astype(int)
        crop_image = bimg[bbox[1]:bbox[3], bbox[0]:bbox[2], :]

        h, w, _ = crop_image.shape
        crop_image = cv2.resize(crop_image, (160,160))

        return crop_image, [h, w, bbox[1], bbox[0], add]

    def postprocess(self, landmark, detail):

        ##recorver, and grouped as [68,2]
        landmark = landmark[0]
        # landmark[:, 0] = landmark[:, 0] * w + bbox[0] -add
        # landmark[:, 1] = landmark[:, 1] * h + bbox[1] -add
        landmark[:, 0] = landmark[:, 0] * detail[1] + detail[3] - detail[4]
        landmark[:, 1] = landmark[:, 1] * detail[0] + detail[2] - detail[4]

        return landmark

    ##below are the method run for batch
    def batch_call(self, image, bboxes):
        ret = np.empty((0,68,2), dtype=np.int32)
        if len(bboxes) == 0:
            return ret

        for bbox in enumerate(bboxes):
            face = np.array([])
            try:
                images_batched, details_batched = self.batch_preprocess(image, bbox)
                images_batched=images_batched.astype(np.float32)

                self.model.set_tensor(self.input_details[0]['index'], images_batched)
                self.model.invoke()

                landmark = self.model.get_tensor(self.output_details[2]['index']).reshape((-1, self.keypoints_num, 2))
            except:
                return ret

            landmark = self.batch_postprocess(landmark, details_batched)
            face = np.append(face, np.array([landmark]))
            face = np.reshape(face, (68,2))
            face = face.astype(np.int32)

            ret = np.append(ret, [np.reshape(face, (68,2))], axis=0)

        return ret

    def batch_preprocess(self, image, bboxes):
        """
        :param image: raw image
        :param bbox: the bbox for the face
        :return:
        """

        images_batched = []
        details = []  ### details about the extra params that needed in postprocess

        ##preprocess
        bbox = bboxes[1]
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        if bbox_width <= self.min_face or bbox_height <= self.min_face:
            return None, None
        add = int(max(bbox_width, bbox_height))
        bimg = cv2.copyMakeBorder(image, add, add, add, add,borderType=cv2.BORDER_CONSTANT,value=np.array([127., 127., 127.]))
        bbox += add

        face_width = (1 + 2 * 0.2) * bbox_width
        center = [(bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2]

        ### make the box as square
        bbox[0] = center[0] - face_width // 2
        bbox[1] = center[1] - face_width // 2
        bbox[2] = center[0] + face_width // 2
        bbox[3] = center[1] + face_width // 2

        # crop
        bbox = bbox.astype(int)
        crop_image = bimg[bbox[1]:bbox[3], bbox[0]:bbox[2], :]

        h, w, _ = crop_image.shape
        crop_image = cv2.resize(crop_image, (160,160))

        images_batched.append(crop_image)

        details.append([h, w, bbox[1], bbox[0], add])

        return np.array(images_batched), np.array(details)

    def batch_postprocess(self, landmark, details):

        assert landmark.shape[0] == details.shape[0]

        # landmark[:, :, 0] = landmark[:, :, 0] * w + bbox[0] - add
        # landmark[:, :, 1] = landmark[:, :, 1] * h + bbox[1] - add

        landmark[:, :, 0] = landmark[:, :, 0] * details[:, 1:2] + details[:, 3:4] - details[:, 4:]
        landmark[:, :, 1] = landmark[:, :, 1] * details[:, 0:1] + details[:, 2:3] - details[:, 4:]

        return landmark
