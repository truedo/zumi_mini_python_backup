#import Zumi_AI.zumi_AI
#from Zumi_AI.protocol import *
from Zumi_AI.zumi_AI import *
zumi = ZumiAI()
zumi.open(portname="COM637")


zumi.led_control(10, 0, 0)
time.sleep(0.5)
zumi.led_control(0, 10, 0)
time.sleep(0.5)

try:
    while True:
     
        time.sleep(0.1)
        
except KeyboardInterrupt:
    zumi.close()
    print("Done")
finally:
    zumi.close() # 연결 및 스트리밍 스레드 종료
    print("Program finished.")


