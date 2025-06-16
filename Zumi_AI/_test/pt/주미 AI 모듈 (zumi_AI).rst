주미 AI 모듈 (zumi_AI)
=========================

이 문서는 Zumi AI 로봇의 다양한 기능들을 설명합니다.
----------------------------------------------------



### 카메라 제어

주미의 카메라 스트림 및 좌우 반전을 제어하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.camera_LR_Flip
   :noindex:

.. automethod:: zumi_AI.ZumiAI.camera_stream_start
   :noindex:

---

### 연결 및 기본 제어

주미 로봇과의 연결 설정 및 모터, LED 등 기본적인 하드웨어 제어 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.connect
   :noindex:

.. automethod:: zumi_AI.ZumiAI.disconnect
   :noindex:

.. automethod:: zumi_AI.ZumiAI.control_motor
   :noindex:

.. automethod:: zumi_AI.ZumiAI.control_motor_time
   :noindex:

.. automethod:: zumi_AI.ZumiAI.led_control
   :noindex:

.. automethod:: zumi_AI.ZumiAI.led_pattern
   :noindex:

.. automethod:: zumi_AI.ZumiAI.play_sound
   :noindex:

.. automethod:: zumi_AI.ZumiAI.stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.set_calibration_motors
   :noindex:

---

### 텍스트 및 디스플레이 제어

주미의 화면에 텍스트를 출력하고 관리하며, 화면 모드나 표정을 변경하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.change_emotion
   :noindex:

.. automethod:: zumi_AI.ZumiAI.change_screen
   :noindex:

.. automethod:: zumi_AI.ZumiAI.display_text
   :noindex:

.. automethod:: zumi_AI.ZumiAI.display_text_add
   :noindex:

.. automethod:: zumi_AI.ZumiAI.display_text_clear
   :noindex:

.. automethod:: zumi_AI.ZumiAI.display_text_pos
   :noindex:

.. automethod:: zumi_AI.ZumiAI.display_text_set
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sendText
   :noindex:

---

### 얼굴 감지 기능

주미의 얼굴 감지 기능(인식, 윤곽선, 랜드마크 등)을 제어하고 데이터를 관리하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.face_contours_visible
   :noindex:

.. automethod:: zumi_AI.ZumiAI.face_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.face_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.face_detector_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.face_landmark_visible
   :noindex:

.. automethod:: zumi_AI.ZumiAI.face_train
   :noindex:

.. automethod:: zumi_AI.ZumiAI.delete_all_Face_data
   :noindex:

.. automethod:: zumi_AI.ZumiAI.delete_face_data
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_detected_face_confidence_score
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_detected_face_name
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_detected_face_result
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_face_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_face_landmark
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_face_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_face_detected
   :noindex:

---

### 제스처 감지 기능

주미의 제스처 감지 기능을 제어하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.gesture_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.gesture_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.gesture_detector_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_gesture_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_gesture_finger
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_gesture_recognize
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_gesture_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_gesture_detected
   :noindex:

---

### 주행 기능

주미의 이동(직진, 회전) 및 라인 팔로워 기능을 제어하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.forward_dist
   :noindex:

.. automethod:: zumi_AI.ZumiAI.forward_dist_quick
   :noindex:

.. automethod:: zumi_AI.ZumiAI.forward_infinite
   :noindex:

.. automethod:: zumi_AI.ZumiAI.left_turn
   :noindex:

.. automethod:: zumi_AI.ZumiAI.left_turn_quick
   :noindex:

.. automethod:: zumi_AI.ZumiAI.linefollower
   :noindex:

.. automethod:: zumi_AI.ZumiAI.linefollower_distance
   :noindex:

.. automethod:: zumi_AI.ZumiAI.linefollower_infinite
   :noindex:

.. automethod:: zumi_AI.ZumiAI.move_infinite
   :noindex:

.. automethod:: zumi_AI.ZumiAI.reverse_dist
   :noindex:

.. automethod:: zumi_AI.ZumiAI.reverse_dist_quick
   :noindex:

.. automethod:: zumi_AI.ZumiAI.reverse_infinite
   :noindex:

.. automethod:: zumi_AI.ZumiAI.right_turn
   :noindex:

.. automethod:: zumi_AI.ZumiAI.right_turn_quick
   :noindex:

.. automethod:: zumi_AI.ZumiAI.send_move_dist
   :noindex:

.. automethod:: zumi_AI.ZumiAI.send_turn
   :noindex:

---

### 센서 및 상태 확인

주미의 배터리, 버튼, IR 센서 등 다양한 센서 값을 읽거나 상태를 확인하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.get_battery
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_button
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_IR_sensor_all
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_IR_sensor_bottom
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_IR_sensor_front
   :noindex:

.. automethod:: zumi_AI.ZumiAI.go_sensor
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sensor_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sensor_visible
   :noindex:

---

### 마커 감지 기능

주미의 마커 감지 기능을 제어하고 관련 데이터를 가져오는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.marker_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.marker_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.marker_detector_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_marker_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_marker_id
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_marker_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_marker_detected
   :noindex:

.. automethod:: zumi_AI.ZumiAI.set_detect_marker
   :noindex:

---

### 객체 감지 기능

주미의 객체 감지 기능을 제어하고, 특정 객체(고양이, 정지 표지판, 신호등 등)의 정보를 가져오는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.get_detect_cat
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_detect_color
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_detect_face
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_obj_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_obj_confidence
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_obj_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_stop_sign_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_stop_sign_confidence
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_stop_sign_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_traffic_light_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_traffic_light_color
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_traffic_light_confidence
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_traffic_light_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_obj_detected
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_stop_sign_detected
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_traffic_light_detected
   :noindex:

.. automethod:: zumi_AI.ZumiAI.object_check_add_obj
   :noindex:

.. automethod:: zumi_AI.ZumiAI.object_check_all_add_obj
   :noindex:

.. automethod:: zumi_AI.ZumiAI.object_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.object_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.object_detector_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.set_detect_cat
   :noindex:

.. automethod:: zumi_AI.ZumiAI.set_detect_color
   :noindex:

.. automethod:: zumi_AI.ZumiAI.set_detect_face
   :noindex:


---

### 스케치 및 학습 기능

주미의 스케치 감지 및 학습 기능을 제어하고 관련 데이터를 관리하는 함수들입니다.

.. automethod:: zumi_AI.ZumiAI.delete_all_sketch_data
   :noindex:

.. automethod:: zumi_AI.ZumiAI.delete_sketch_data
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_sketch_center
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_sketch_confidence
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_sketch_result
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_sketch_size
   :noindex:

.. automethod:: zumi_AI.ZumiAI.get_teachable_result
   :noindex:

.. automethod:: zumi_AI.ZumiAI.is_sketch_detected
   :noindex:

.. automethod:: zumi_AI.ZumiAI.key_press_set
   :noindex:

.. automethod:: zumi_AI.ZumiAI.key_press_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.key_press_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sketch_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sketch_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sketch_detector_stop
   :noindex:

.. automethod:: zumi_AI.ZumiAI.sketch_train
   :noindex:

.. automethod:: zumi_AI.ZumiAI.teachable_detector_init
   :noindex:

.. automethod:: zumi_AI.ZumiAI.teachable_detector_start
   :noindex:

.. automethod:: zumi_AI.ZumiAI.teachable_detector_stop
   :noindex:

---