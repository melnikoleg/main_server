import glob
import os

import numpy as np
import scipy.sparse as sp
from keras.applications.mobilenetv2 import MobileNetV2
from keras.applications.mobilenetv2 import preprocess_input
from keras.engine import Model
from keras.preprocessing import image
from pymongo import MongoClient

from sparce import save_sparse_matrix,load_sparse_matrix

from keras import backend as K
K.tensorflow_backend._get_available_gpus()


conn = MongoClient(host='192.168.1.242', port=27017)


db = conn['vectors']
coll = db['vecs']



def vectorize_add(dir_name,id_part):

    model = MobileNetV2(input_shape=(224, 224, 3), include_top=False, pooling='avg')

    vec_arr =[]
    print(os.path.join(dir_name,str(id_part)))
    for top, dirs, files in os.walk(os.path.join(dir_name,str(id_part))):
        for nm in files:
            img = image.load_img(os.path.join(top, nm), target_size=(224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)
            pred = model.predict(x)

            listdata = pred.ravel().tolist()
            vec_arr.append(listdata)

    id_vec = coll.insert({"vec_part": vec_arr, "id_part": str(id_part)})
    vec_arr.clear()

    print('Finished')
    return id_vec








