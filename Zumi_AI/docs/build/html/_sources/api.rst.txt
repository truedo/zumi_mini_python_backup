ZumiAI API 개요
==================

이 문서는 ZumiAI 라이브러리의 모든 주요 메서드를 요약하여 보여줍니다.
ZumiAI와 상호작용하는 데 필요한 핵심 기능들을 한눈에 파악할 수 있도록 분류되어 있습니다.

.. raw:: html

   <div style="background-color: #f0f8ff; padding: 10px; border-left: 4px solid #007acc; margin-bottom: 15px; font-size: 14px;">
     <strong>※ 지원 여부 안내</strong><br>
     함수별 <strong>지원 여부</strong>는 <u>연결 방식</u>에 따른 동작 가능 여부를 나타냅니다.<br>
     🔌 <strong>동글 연결</strong> : USB 동글을 사용하여 Zumi AI에 연결한 경우<br>
     🌐 <strong>IP 연결</strong> : 사용자가 IP 주소를 직접 입력하여 Zumi AI에 연결한 경우<br><br>
     일부 함수는 특정 연결 방식에서만 동작합니다. 각 함수 설명의 지원 정보를 참고하세요.
   </div>

------------------------------------------------------

.. raw:: html

   <strong>기본 연결 방식</strong><br>
   Zumi AI를 사용하기 위한 기본적인 연결 방법은 아래와 같습니다.<br>
   이 코드를 통해 Zumi AI 객체를 초기화하고 연결을 설정할 수 있습니다.<br>

   <div style="background-color: #f0fff7; padding: 15px; border-left: 5px solid #00cc52; margin-bottom: 20px; font-size: 16px; line-height: 1.6;">

   from zumi_AI.zumi_AI import *<br>
   zumiAI = ZumiAI()<br>
   zumiAI.connect()<br>
   </div>

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
     1) 연결 제어
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>


.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/connection
   :template: function.rst

   connect
   disconnect

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   2) 주행 및 움직임 제어
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/movement
   :template: function.rst

   stop

   control_motor
   control_motor_time

   forward_dist
   reverse_dist
   send_move_dist

   forward_dist_quick
   reverse_dist_quick
   send_move_dist_quick

   left_turn
   right_turn
   send_turn

   left_turn_quick
   right_turn_quick
   send_turn_quick

   forward_infinite
   reverse_infinite
   move_infinite

   linefollower_distance
   linefollower_infinite
   linefollower

   go_sensor
   set_calibration_motors

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   3) 감정 및 소리
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/emotion_sound
   :template: function.rst

   change_emotion
   play_sound

   led_control
   led_pattern

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   4) 화면 제어
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/camera_display
   :template: function.rst

   change_screen
   display_text
   display_text_add
   display_text_clear
   display_text_pos
   display_text_set
   #sendText

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   5) 기타 센서 및 시스템 정보
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/sensors_system_info
   :template: function.rst

   get_IR_sensor_all
   get_IR_sensor_front
   get_IR_sensor_bottom

   get_battery
   get_button

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   6) 키보드 인터럽트 제어
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/keyboard
   :template: function.rst

   key_press_set
   key_press_start
   key_press_stop

------------------------------------------------------



.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   7) 기본 카메라 인식 기능
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: green; font-weight: bold;">✅ 동글 연결 지원</span> |
     <span style="color: red; font-weight: bold;">❌ IP 연결 미지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/basic_camera
   :template: function.rst

   set_zumi_face_detection
   set_zumi_cat_detection
   set_zumi_color_detection
   set_zumi_marker_detection

   is_zumi_face_detected
   get_zumi_face_center

   is_zumi_cat_detected
   get_zumi_cat_center

   get_zumi_color_id
   get_zumi_color_center

   get_zumi_marker_id
   get_zumi_marker_center

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   8) 카메라 스트리밍
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/camera_streaming
   :template: function.rst

   camera_stream_start
   camera_LR_Flip

   sensor_start
   sensor_visible
   frame_rate_visible

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   9) 얼굴 인식
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/face_recognition
   :template: function.rst

   face_detector_init
   face_detector_start
   face_detector_stop

   face_landmark_visible
   face_contours_visible

   is_face_detected
   get_face_center
   get_face_size
   get_face_landmark

   face_train
   delete_face_data
   delete_all_Face_data

   get_detected_face_result
   get_detected_face_name
   get_detected_face_confidence_score

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   10) 마커 인식
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>


.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/marker_recognition
   :template: function.rst

   marker_detector_init
   marker_detector_start
   marker_detector_stop

   is_marker_detected
   get_marker_id
   get_marker_center
   get_marker_size

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   12) 제스처 인식
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>


.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/gesture_recognition
   :template: function.rst

   gesture_detector_init
   gesture_detector_start
   gesture_detector_stop

   is_gesture_detected
   get_gesture_center
   get_gesture_size

   get_gesture_finger
   get_gesture_recognize

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   11) 스케치 인식
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>


.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/sketch_recognition
   :template: function.rst

   sketch_detector_init
   sketch_detector_start
   sketch_detector_stop

   is_sketch_detected
   get_sketch_center
   get_sketch_size

   sketch_train
   delete_sketch_data
   delete_all_sketch_data

   get_sketch_result
   get_sketch_name
   get_sketch_confidence

------------------------------------------------------

.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   13) 객체 인식(신호등, 정지 표지판)
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>

.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/traffic_sign_recognition
   :template: function.rst

   object_detector_init
   object_detector_start
   object_detector_stop

   is_obj_detected
   get_obj_size
   get_obj_center
   get_obj_confidence

   get_traffic_light_color

   object_check_add_obj
   object_check_all_add_obj
   object_check_del_obj
   object_check_all_del_obj

------------------------------------------------------


.. raw:: html

   <div style="font-weight: bold; color: blue; font-size: 16px; margin-top: 10px;">
   14) 사용자 학습 모델 (Teachable Machine)
   </div>

   <div style="font-size: 13px; margin-left: 10px;">
     <span style="color: red; font-weight: bold;">❌ 동글 연결 미지원</span> |
     <span style="color: green; font-weight: bold;">✅ IP 연결 지원</span>
   </div><br>


.. currentmodule:: zumi_AI.ZumiAI
.. autosummary::
   :toctree: _autosummary_generated/teachable_machine
   :template: function.rst

   teachable_detector_init
   teachable_detector_start
   teachable_detector_stop
   get_teachable_result

