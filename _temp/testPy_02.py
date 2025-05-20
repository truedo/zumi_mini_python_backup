from zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.connect()

#zumi.set_calibration_motors() 
zumi.control_motor(2,40,1,40)



#zumi.forward_dist()
#time.sleep(3)
#zumi.reverse_dist()

#zumi.forward_dist()

#zumi.send_turn(3,720,1)
#time.sleep(5)
#zumi.left_turn(3,90)
#time.sleep(3)
#zumi.right_turn(3,90)



#zumi.move_infinite(20,1)

time.sleep(2)

zumi.stop()
