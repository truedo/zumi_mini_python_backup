import math
import cv2
import os
import numpy as np
from numpy.core.defchararray import array
from tensorflow.python.eager.context import disable_graph_collection
import pkg_resources

class SketchRecognizer:
    def __init__(self) -> None:

        self.orbDetector = cv2.ORB_create()
        self.matcherHamming = cv2.DescriptorMatcher_create(cv2.DescriptorMatcher_BRUTEFORCE_HAMMINGLUT)
        self.sketchPath = pkg_resources.resource_filename(__package__,"res/sketch/")
        self.orbDescriptors = []
        self.nameIndexList = []
        self.nameIntList = []

        if os.path.exists(self.sketchPath) is False:
            os.makedirs(self.sketchPath)

    def __call__(self, image):
        retName = np.array([])
        retRect = np.empty((1,4,2), dtype=int)
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

                idx = self.__checkMatches(des)
                if idx != -1:
                    retName = np.append(retName, np.array([self.nameIndexList[idx]]), axis=0)
                else:
                    retName = np.append(retName, np.array(['Sketch']), axis=0)

            else:
                retName = np.append(retName, np.array(['Sketch']), axis=0)

        retRect = np.delete(retRect, [0, 0], axis=0)
        return retName, retRect


    def SaveSketch(self, image, name:str, sketchPath:str =pkg_resources.resource_filename(__package__,"res/sketch/")):
        if os.path.isdir(sketchPath) is False:
            print(sketchPath + " is not directory.")
            return -1

        if bool(name) is False:
            print("Name parameter is Empty.")
            return -1

        dataCnt = 0
        for filename in os.listdir(sketchPath):
            if name in filename:
                dataCnt += 1

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
                break

        if sketchImage is not None:
            sketchImage = cv2.resize(sketchImage, (150,150))
            cv2.imwrite(sketchPath+name+'_'+str(dataCnt)+'.jpg', sketchImage)
            return 0

        return -1

    def RemoveSketch(self, name:str, sketchPath:str=pkg_resources.resource_filename(__package__,"res/sketch/")):
        if os.path.isdir(sketchPath) is False:
            print( sketchPath +" is not directory.")
            return

        if bool(name) is False:
            print("Name parameter is Empty.")
            return

        for filename in os.listdir(sketchPath):
            basename = os.path.basename(filename)
            if name == basename.split('_')[0]:
                os.remove(sketchPath+filename)

    def TrainModel(self, nameIndexList:list, nameIntList:list, orbDescriptors:list):
        self.orbDescriptors = orbDescriptors.copy()
        self.nameIndexList = nameIndexList.copy()
        self.nameIntList = nameIntList.copy()
        self.matcherHamming.clear()

        self.matcherHamming.add(self.orbDescriptors)
        self.matcherHamming.train()

    def __checkMatches(self, descriptor):
        matchCnt = 0
        max_dist = 0
        min_dist = 100

        matchIdx = -1
        matchMaxCnt = 0

        idx = 0
        for trainDescriptor in self.matcherHamming.getTrainDescriptors():
            matchCnt = 0
            max_dist = 0
            min_dist = 100

            matches = self.matcherHamming.match(descriptor, trainDescriptor)
            for dMatch in matches:
                dist = dMatch.distance
                if dist < min_dist:
                    min_dist = dist
                if dist > max_dist:
                    max_dist = dist

                if dist <= 30:
                    matchCnt += 1

            if min_dist < 30 and matchCnt > 0:
                if matchMaxCnt < matchCnt:
                    matchIdx = idx
                    matchMaxCnt = matchCnt

            idx += 1

        return matchIdx

    def __angle(self, pt1:array, pt2:array, pt0:array):
        abx1 = pt1[0] - pt0[0]
        aby1 = pt1[1] - pt0[1]
        cbx2 = pt2[0] - pt0[0]
        cby2 = pt2[1] - pt0[1]

        dot = abx1*cbx2 + aby1*cby2
        cross = abx1*cby2 - aby1*cbx2

        alpha = math.atan2(cross,dot)

        return int(math.floor( alpha * 180.0) / 3.1415926535897932384626433832795 + 0.5)
        # return (dx1*dx2 + dy1*dy2)/math.sqrt((dx1*dx1 + dy1*dy1)*(dx2*dx2 + dy2*dy2) + 1e-10)