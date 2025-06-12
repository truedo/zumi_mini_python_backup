#내부테스트
from datetime import datetime

from zumi_AI.zumi_AI import *


zumi = ZumiAI()
# serial
#zumi.connect()
#zumi.connect("COM84")

# web socket
zumi.connect('192.168.0.59')


zumi.camera_stream_start()




##
##
zumi.sensor_start()
#zumi.sensor_visible(True)
#zumi.frame_rate_visible(True)

##zumi.display_text_set(5,5)
##zumi.display_text("Motor",1)
##zumi.display_text_add("calibration",1)
##zumi.display_text_add("Start",1)
##zumi.display_text_pos(0,20)


#zumi.yolo_check_add_obj("stop sign")
##
zumi.object_detector_init()
zumi.object_detector_start()
##zumi.object_detector_stop()


##
##zumi.marker_detector_init()
##zumi.marker_detector_start()
##zumi.marker_detector_stop()


##
##zumi.gesture_detector_init()
##zumi.gesture_detector_start()
#zumi.gesture_detector_stop()



##
##zumi.teachable_detector_init(model_path = 'model_unquant.tflite', lable_path = 'labels.txt')
##zumi.teachable_detector_start()
#zumi.teachable_detector_stop()





##
##zumi.face_detector_init()
##zumi.face_detector_start()
######zumi.face_detector_stop()
####
#zumi.face_train("bin")
####zumi.delete_face_data("child")


##zumi.face_landmark_visible(True)
##zumi.face_contours_visible(True)


##
##zumi.sketch_detector_init()
##zumi.sketch_detector_start()
#zumi.sketch_train("school")

#zumi.delete_sketch_data("school")
                        
#zumi.sketch_capture("tower",captureCount=5)
#zumi.sketch_train()
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

##
##zumi.SketchDetectorInit()
##zumi.SketchDetectorStart()
##

#zumi.SketchCapture("flower",20)

#zumi.TrainSketchData()



time.sleep(1)
count1 = 0

try:
    while True:

##        current_timestamp = time.time()
##
##        # datetime 객체로 변환
##        dt_object = datetime.fromtimestamp(current_timestamp)
##        formatted_time = dt_object.strftime("%H:%M:%S")
##        
##        zumi.display_text(formatted_time)
##
##        time.sleep(0.5)

##        ir = zumi.get_battery()
##        print(ir)
##
##
##        
        count1 = zumi.is_obj_detected("cat")
        print(count1)
        
####
##        class_name, confidence_score = zumi.get_sketch_result("queen")
##        print(class_name, confidence_score)
####        if class_name == "queen":
####            print("ukikiki")
####            zumi.forward_infinite(2)
####        else:
####            zumi.stop()
##            

        
        time.sleep(0.5)
        
except KeyboardInterrupt:

    zumi.stop()
    zumi.disconnect()
    print("Done")












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
 
