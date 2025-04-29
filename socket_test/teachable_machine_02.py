
from tensorflow.keras.models import load_model
from PIL import Image, ImageOps, ImageDraw, ImageFont
import numpy as np

import cv2

image_path = "dataset_20250428_174945.jpg"

def main():
    from tensorflow.keras.models import load_model
    import numpy as np
    from PIL import Image

    model = load_model('keras_model.h5')

    # 이미지 불러오기
    img = Image.open(image_path).resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # 예측
    predictions = model.predict(img_array)
    print(predictions)

if __name__ == "__main__":
    main()
