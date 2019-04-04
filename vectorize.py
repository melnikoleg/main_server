import os

import numpy as np
from keras import backend as K
from keras.applications.mobilenetv2 import preprocess_input
from keras.engine import Model
from keras.models import load_model
from keras.preprocessing import image
from pymongo import MongoClient

import globals as _g

# from keras.applications import ResNet50
# from keras.applications.resnet50 import preprocess_input

K.tensorflow_backend._get_available_gpus()

conn = MongoClient(host=_g.HOST, port=27017)
db = conn['vectors']
coll = db['vecs']


def vectorize_add(dir_name, id_part):
    print("Vectorise")
    K.clear_session()

    # model = MobileNetV2(input_shape=(224, 224, 3), include_top=False, pooling='max',alpha=1.4)
    keras_model_name = r"C:\Users\HOME\PycharmProjects\main_server\model_MIRO_M2_89.h5"
    base = load_model(keras_model_name)
    model = Model(inputs=base.input, outputs=base.get_layer(index=-2).output)

    vec_arr = []
    print(os.path.join(dir_name, str(id_part)))
    for top, dirs, files in os.walk(os.path.join(dir_name, str(id_part))):
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

# print(vectorize_add(r"C:\Users\HOME\PycharmProjects\main_server\temp","5C98F542410D6C1Dd02B400A"))
