import io
from PIL import Image
import numpy as np

RICKROLL_FILE = "./perm_contents/rickroll_4k.png"
RICKROLL_RATE = 0.1
PNG_HEADER = bytes.fromhex("89504E470D0A1A0A")

def check_png(file):
    if not file[:len(PNG_HEADER)]==PNG_HEADER:
        return False, "NOT_PNG_FILE"
    file_buffer = io.BytesIO(file)
    try:
        img = Image.open(file_buffer)
        img.close()
        file_buffer.close()
    except:
        if not img==None: img.close()
        file_buffer.close()
        return False, "BAD_PNG_FILE"
    return True, None

def apply_shitpost(file):
    original_img_buffer = io.BytesIO(file)
    original_img = Image.open(original_img_buffer)
    original_img_data = np.array(original_img)
    original_img.close()
    original_img_buffer.close()

    rickroll_original_img = Image.open(RICKROLL_FILE,"r")
    rickroll_resized_img = rickroll_original_img.resize((original_img_data.shape[1],original_img_data.shape[0]))
    rickroll_original_img.close()
    rickroll_img_data = np.array(rickroll_resized_img)
    rickroll_resized_img.close()
    
    original_img_data = original_img_data.astype(np.float64)
    rickroll_img_data = rickroll_img_data.astype(np.float64)
    if rickroll_img_data.shape[2]<original_img_data.shape[2]:
        rickroll_img_data = np.concatenate([rickroll_img_data,255*np.ones((rickroll_img_data.shape[0],rickroll_img_data.shape[1],1))],axis=2)
    new_img_data = (1-RICKROLL_RATE)*original_img_data + RICKROLL_RATE*rickroll_img_data
    new_img_data = new_img_data.astype(np.uint8)
    
    new_img = Image.fromarray(new_img_data)
    new_img_buffer = io.BytesIO()
    new_img.save(new_img_buffer,format="BMP")
    new_img.close()
    new_img_value = new_img_buffer.getvalue()
    new_img_buffer.close()
    return new_img_value
    