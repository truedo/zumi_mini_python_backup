import cv2
from pupil_apriltags import Detector

image = cv2.imread('25h9_cap_01.jpg')
#image = cv2.imread('25h9_img2.png')

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


#detector = Detector(families='tag25h9')

detector = Detector(families='tag25h9',
                       nthreads=1.5,
                       quad_decimate=2.0,
                       quad_sigma=0.0,
                       refine_edges=2,
                       decode_sharpening=0,
                       debug=1)

#detector = Detector(families='tag36h11')
tags = detector.detect(gray)





for tag in tags:
    corners = tag.corners.astype(int)
    cv2.polylines(image, [corners], isClosed=True, color=(0, 255, 0), thickness=2)
    center = tuple(map(int, tag.center))
    cv2.circle(image, center, 5, (0, 0, 255), -1)
    cv2.putText(image, f"ID: {tag.tag_id}", center, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

cv2.imshow("AprilTag Detection", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
