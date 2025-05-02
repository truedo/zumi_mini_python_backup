import numpy as np
import pandas as pd
import gradio as gr
import os
from PIL import Image
import json


def image_generator(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            image_path = os.path.join(directory_path, filename)
            image = Image.open(image_path)
            image_array = np.array(image)
            yield filename,image_array

directory_path = "/content/data/"

# Create the generator
image_gen = image_generator(directory_path)


def record_input(fname:str, label:str):
  if label != "Pass":
    output = {"fname": fname, "label": label}
    with open("/content/output.txt", 'a') as f:
      json.dump(output, f)
      f.write("\n")
  fname, image = next(image_gen)
  return fname, image

def start():
  fname, image = next(image_gen)
  return fname, image


with gr.Blocks() as demo:
  start_btn = gr.Button("Start")
  img_block = gr.Image(visible = True, shape=(300,300))
  file_name = gr.Textbox(info="File name", visible = True)
  with gr.Row():
    dog_btn = gr.Button(value = "Dog", interactive=True, visible = True)
    cat_btn = gr.Button(value = "Cat",interactive=True, visible = True)
    pass_btn = gr.Button(value = "Pass",interactive=True, visible = True)

  dog_btn.click(fn = record_input, inputs = [file_name, dog_btn], outputs=[file_name,img_block])
  cat_btn.click(fn = record_input, inputs = [file_name, cat_btn], outputs=[file_name,img_block])
  pass_btn.click(fn = record_input, inputs = [file_name, pass_btn], outputs=[file_name,img_block])
  start_btn.click(fn = start, outputs = [file_name,img_block])
  
demo.queue()
demo.launch(share=True, debug=True)
