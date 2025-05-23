from os import sep
from warnings import catch_warnings
import cv2
from numpy.testing._private.utils import assert_approx_equal
import tensorflow as tf
import numpy as np
from numpy.core.defchararray import array
from tensorflow.python.eager.context import disable_graph_collection
import pkg_resources

class NumberRecognizer:
    def __init__(self) -> None:
        self.model_path = pkg_resources.resource_filename(__package__,"res/model/mnist_model.tflite")
        self.model = tf.lite.Interpreter(model_path=self.model_path)
        self.model.allocate_tensors()

        self.input_details = self.model.get_input_details()
        self.output_details = self.model.get_output_details()

        self.kernel = np.ones((3,3), np.uint8)

    def __call__(self, image) -> np.array:
        retNumber = ''
        retRect = np.empty((1,4,2), dtype=int)
        h,w,c = image.shape
        numberImage = None
        grayImage = None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processedImg = cv2.pyrDown(gray)
        processedImg = cv2.pyrUp(processedImg)
        #processedImg = cv2.Canny(processedImg,0,100)
        processedImg = cv2.Canny(processedImg, 50, 150)

        processedImg = cv2.dilate(processedImg, self.kernel, anchor=(-1,1), iterations=1)

        contours, hierarchy = cv2.findContours(processedImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]

        for contour in contours:
            area = cv2.contourArea(contour)

            # if area < 2500 or area > 250000:
            #     continue
            img_area = image.shape[0] * image.shape[1]
            if area < 0.01 * img_area or area > 0.8 * img_area:
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
                numberImage = cv2.warpPerspective(processedImg, M, (w,h))
                grayImage = cv2.warpPerspective(gray, M, (w,h))

                retRect = np.append(retRect, np.array([approx]), axis=0)
                break

        if numberImage is not None:
            retNumber = self.__findNumeric(grayImage, numberImage)

        retRect = np.delete(retRect, [0, 0], axis=0)
        return retNumber, retRect

    def __findNumeric(self, grayImg, cannyImg) -> str:
        rectList = []
        isAdded = False
        contours, _ = cv2.findContours(cannyImg, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        for i in range(0, len(contours)):
            area = cv2.contourArea(contours[i])
            x,y,w,h = cv2.boundingRect(contours[i])

            # if area < 10000 or area > 100000:
            #     continue
            img_area = grayImg.shape[0] * grayImg.shape[1]
            if area < 0.005 * img_area or area > 0.3 * img_area:
                continue

            if len(rectList) == 0:
                isAdded = False
            else:
                for i in range(0, len(rectList)):
                    if rectList[i][0] > x:
                        rectList.insert(i, [x,y,w,h])
                        isAdded = True
                        break

            if isAdded == False:
                rectList.append([x,y,w,h])
        numberStr = []

        for x,y,w,h in rectList:
            numRoi = grayImg[y:y+h, x:x+w]
            numRoi = self.__makeSquare(numRoi)
            number = self.__recognizeNumericImage(numRoi)
            numberStr = (str(number))
            # numberStr.append(str(number))

        return ''.join(numberStr)

    def __makeSquare(self, image):
        height, width = image.shape
        retImg = image.copy()

        if height != width:
            if width > height:
                pad = int((width - height) / 2)
                retImg = cv2.copyMakeBorder(retImg, pad,pad,0,0,cv2.BORDER_CONSTANT, value=[255,255,255])
            else:
                pad = int((height - width) / 2)
                retImg = cv2.copyMakeBorder(retImg, 0,0,pad,pad,cv2.BORDER_CONSTANT, value=[255,255,255])
        retImg = cv2.copyMakeBorder(retImg, 50,50,50,50,cv2.BORDER_CONSTANT, value=[255,255,255])
        retImg = cv2.resize(retImg, (28,28))
        retImg = cv2.bitwise_not(retImg)
        _, retImg = cv2.threshold(retImg, 156, 255, cv2.THRESH_BINARY)
        # retImg = cv2.adaptiveThreshold(retImg, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        #                        cv2.THRESH_BINARY, 11, 2)
        #_, retImg = cv2.threshold(retImg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)


        return retImg

    def __recognizeNumericImage(self, image):
        #bimage = np.expand_dims(image, axis=0).astype(np.float32)
        bimage = image[np.newaxis, ...].astype(np.float32) / 255.0
        #bimage = np.expand_dims(image, axis=(0, -1)).astype(np.float32) / 255.0

        try:
            self.model.set_tensor(self.input_details[0]['index'],bimage)
            self.model.invoke()
            outputs = self.model.get_tensor(self.output_details[0]['index'])
            number = self.__findNearest(outputs)
        except Exception as e:
            print("RECO : " , e)
            return ''

        return number

    def __findNearest(self, outputs):
        ret = -1
        maxVal = 0.0

        for i in range(0, outputs.size):
            if outputs[0][i] > maxVal:
                maxVal = outputs[0][i]
                ret = i

        return ret