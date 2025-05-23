#내부테스트

from zumi_AI.zumi_AI import *


zumi = ZumiAI()

#zumi.connect('ws://192.168.0.59/ws')

zumi.connect()



zumi.start_video_viewer()

zumi.FaceDetectorInit()
zumi.FaceDetectorStart()
zumi.FaceCapture("aa")

#zumi.sensorInit()
#zumi.sensorStart()
#zumi.sensorStop()

##
##zumi.GestureDetectorInit()
##zumi.GestureDetectorStart()
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



#time.sleep(1)
##
##try:
##    while True:
##        count = zumi.GetSketchCenterPoint("flower")
##        print(count)
##        
##        time.sleep(0.5)
##        
##except KeyboardInterrupt:
##
##    zumi.stop()
##    zumi.close()
##    print("Done")












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
 
