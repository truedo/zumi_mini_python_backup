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
zumi.frame_rate_visible(True)

##zumi.display_text_set(5,5)
##zumi.display_text("Motor",1)
##zumi.display_text_add("calibration",1)
##zumi.display_text_add("Start",1)
##zumi.display_text_pos(0,20)


##
##


##zumi.face_landmark_visible(True)
##zumi.face_contours_visible(True)

zumi.face_detector_init()
zumi.face_detector_start()
######zumi.face_detector_stop()
####
#zumi.face_train("dr")
####zumi.delete_face_data("child")




##
zumi.marker_detector_init()
zumi.marker_detector_start()
##zumi.marker_detector_stop()


##
zumi.gesture_detector_init()
zumi.gesture_detector_start()
#zumi.gesture_detector_stop()



##
zumi.sketch_detector_init()
zumi.sketch_detector_start()
#zumi.sketch_train("school")


##
zumi.object_detector_init() #speed
##zumi.object_detector_init("balance")
##zumi.object_detector_init("power")
zumi.object_detector_start()
##zumi.object_detector_stop()

##zumi.object_check_add_obj("사람")



##
##zumi.teachable_detector_init(model_path = 'model_unquant.tflite', lable_path = 'labels.txt')
##zumi.teachable_detector_start()
#zumi.teachable_detector_stop()





#zumi.delete_sketch_data("school")
                        
#zumi.sketch_capture("tower",captureCount=5)
#zumi.sketch_train()
##
##time.sleep(3)
##zumi.LeftRightFlipMode(True)
##
##time.sleep(3)
##zumi.LeftRightFlipMode(False)



#time.sleep(3)
#zumi.DeleteFaceData("CHA")

##
##zumi.SketchDetectorInit()
##zumi.SketchDetectorStart()
##

#zumi.SketchCapture("flower",20)

#zumi.TrainSketchData()

##################################################


##zumi.display_text_set(5,5)
##zumi.display_text("Motor",1)
##
##zumi.play_sound(0)
##
##zumi.change_screen(2)
##time.sleep(5)
##zumi.change_screen(1)
##time.sleep(3)
##zumi.change_screen(2)
##time.sleep(1)
##zumi.change_emotion(14)
##
##
##time.sleep(1)
##zumi.led_control(0,10,0)
##time.sleep(1)
##zumi.led_control(10,0,10)
##time.sleep(1)
###zumi.led_control(0,10,0)
##
##zumi.led_pattern(2, 0.1)




##
##zumi.forward_dist(1,10)
##print("a")
##
##time.sleep(0.5)
##
##print("b")
##
##zumi.reverse_dist(1,10)
##
##print("c")



##################################################




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
   
##        count1 = zumi.is_obj_detected("cat")
##        print(count1)
        
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
 
