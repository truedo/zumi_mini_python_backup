#내부테스트

from zumi_AI.zumi_AI import *


zumi = ZumiAI()
# serial
#zumi.connect()
#zumi.connect("COM84")

# web socket
zumi.connect('192.168.0.59')


zumi.camera_stream_start()




##
##zumi.sensor_init()
##zumi.sensor_start()
#zumi.sensor_stop()

#zumi.yolo_check_add_obj("stop sign")

##zumi.object_detector_init()
##zumi.object_detector_start()
#zumi.object_detector_stop()


##
##zumi.marker_detector_init()
##zumi.marker_detector_start()
##zumi.marker_detector_stop()


##
##zumi.gesture_detector_init()
##zumi.gesture_detector_start()
#zumi.gesture_detector_stop()




##
zumi.face_detector_init()
zumi.face_detector_start()
#zumi.face_detector_stop()

##
##time.sleep(1)
##
###zumi.DeleteAllFaceData()
###zumi.DeleteFaceData("aa")
##
###zumi.FaceTrain("girl")

##
##time.sleep(3)




##
##time.sleep(3)
##zumi.LeftRightFlipMode(True)
##
##time.sleep(3)
##zumi.LeftRightFlipMode(False)

##
#zumi.FacedetectorInit()
#zumi.FacedetectorStart()
##
##print("start captur")
##time.sleep(1)
##zumi.FaceCapture("CHA",5)
##time.sleep(1)
##
##zumi.TrainFaceData()


#time.sleep(3)
#zumi.DeleteFaceData("CHA")


##zumi.SketchDetectorInit()
##zumi.SketchDetectorStart()
##

#zumi.SketchCapture("flower",20)

#zumi.TrainSketchData()


##
##time.sleep(1)
##
##try:
##    while True:
##        count1 = zumi.get_traffic_light_color()
##        print(count1)        
##        
##        time.sleep(0.5)
##        
##except KeyboardInterrupt:
##
##    zumi.stop()
##    zumi.disconnect()
##    print("Done")
##











##time.sleep(1)
##zumi.led_control(10,10,10)
##time.sleep(0.5)
##zumi.led_control(10,0,0)
##time.sleep(1)
##
##zumi.forward_dist()
##time.sleep(2)
##zumi.stop()



#zumi.stop()
#zumi.disconnectqq
 
