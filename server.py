import glob
import json
import os
import shutil
import subprocess
import threading
import time

import cv2
import gridfs
import numpy as np
from bson import json_util
from bson.objectid import ObjectId
from flask import Flask, request
from keras import backend as K
from pymongo import MongoClient
from skimage.measure import compare_ssim

import globals as _g

K.tensorflow_backend._get_available_gpus()

from predict import load_predictor, load_sparse_matrix

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = _g.UPLOAD_FOLDER

app = Flask(__name__)

conn = MongoClient(host=_g.HOST, port=27017)

db = conn['Parts']
coll = db['Part']

fs = gridfs.GridFS(db)
fss = gridfs.GridFSBucket(db)

VEC = np.zeros(1792)


def delete_similar_images(dir_name, id_part):
    files = glob.glob(os.path.join(dir_name, str(id_part), "*.jpg"))

    for a_file in files:
        print(a_file)
        imageA = cv2.imread(str(a_file))
        grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
        files.remove(a_file)
        for b_file in files:
            imageB = cv2.imread(b_file)
            grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
            (score, diff) = compare_ssim(grayA, grayB, full=True)
            print(score)
            if score > 0.85:
                os.remove(b_file)
                files.remove(b_file)


def blur_all(dir_name, id_part):
    files = glob.glob(os.path.join(dir_name, str(id_part), "*.jpg"))
    for file in files:
        img = cv2.imread(file)
        img = cv2.blur(img, (5, 5), 2)
        cv2.imwrite(file, img)


def thread(func):
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.run()

    return wrapper()


def render_and_vect(path_to_model, id_part):

    try:
        start_time = time.time()

        subprocess.call(
            ["C:/Program Files/Blender Foundation/Blender/blender.exe", "phong_3.blend", "--background", "--python",
             "phong_2.py", "--", path_to_model, "temp/"])
        # os.remove(path)

        delete_similar_images(dir_name="temp/", id_part=id_part)
        blur_all(dir_name="temp/", id_part=id_part)
        os.remove(path_to_model)
        print("--- %s seconds ---" % (time.time() - start_time))
        import vectorize
        # id_vec = vectorize.vectorize_add(dir_name="F:/PROG/tmp46/",id_part=id_part)
        id_vec = vectorize.vectorize_add(dir_name="temp/", id_part=id_part)
        print("--- %s seconds ---" % (time.time() - start_time))
        shutil.rmtree(os.path.join("temp/", str(id_part)))
        return id_vec

    except Exception as e:
        print(str(e))


@thread
@app.route('/recognise_image', methods=['POST'])
def recognise_image():
    try:
        start_time = time.time()
        data = request.json
        vec = np.array(data)
        new_data = vec
        # new_data = VEC +vec
        # 2.183826

        result = load_predictor(new_data)
        print(result)
        json_parts = []
        for i in result:
            doc = coll.find_one(ObjectId(i[0]))
            draw_img_preview = fss.open_download_stream(ObjectId(str(doc['draw_id_img_preview'])))
            json_part = {
                'draw_img_preview': draw_img_preview.read(),
                'draw_img_id': doc['draw_id_img'],
                'Name': doc['Name'],
                'Designation': doc['Designation'], }
            json_parts.append(json_part)

        json_data = {"predict_result": json_parts}
        print("--- %s seconds ---" % (time.time() - start_time))
        # print(json_util.dumps(json_data))
        return json_util.dumps(json_data)

    except Exception as e:
        print(str(e))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in _g.ALLOWED_EXTENSIONS


@thread
@app.route('/get_image', methods=['POST'])
def fullImage():
    try:
        data = request.json
        print(data)
        print(data["id"])

        draw_img = fss.open_download_stream(ObjectId(str(data["id"])))
        # data ={"full_image":}
        information = "text"
        respond = json_util.dumps(dict({"image": draw_img.read(), "information": information}))

        # print(respond)

        return respond

    except Exception as e:
        print(str(e))


@app.route('/add_part', methods=['POST'])
def add_part():

    def upload_to_gridfs(file):

        if file and allowed_file(file.filename):
            file_id = fss.upload_from_stream(file.filename, file)

            return file_id

        return None

    def save_to_disk(file_model, model_id, part_id):
        if file_model and allowed_file(file_model.filename):
            # filename = secure_filename(file.filename)
            # file.save(os.path.join('models', model_id+str('.stl')))
            path = os.path.join('models', str(part_id) + '.stl')
            with open(path, 'wb') as file:
                fss.download_to_stream(ObjectId(str(model_id)), file)

            return path

    posted_data = json.load(request.files['data'])

    file_model = request.files['file_model']
    print(file_model.filename)
    file_draw = request.files['file_draw']
    draw_img = request.files['draw_img']
    draw_img_preview = request.files['draw_img_preview']

    model_id = upload_to_gridfs(file_model)

    draw_id = upload_to_gridfs(file_draw)

    draw_id_img = upload_to_gridfs(draw_img)
    draw_id_img_preview = upload_to_gridfs(draw_img_preview)

    id_doc = coll.insert({'Name': str(posted_data['name']),
                          'Designation': posted_data['designation'],
                          '3d_model': str(model_id),
                          'Draw_img': str(draw_id),
                          'draw_id_img': str(draw_id_img),
                          'draw_id_img_preview': str(draw_id_img_preview),
                          'information': str()
                          })

    path_to_model = save_to_disk(file_model, model_id, str(id_doc))
    print(path_to_model)

    id_vec = render_and_vect(path_to_model, id_doc)

    coll.update({"_id": ObjectId(id_doc)}, {"$set": {"id_vec": id_vec}})

    load_sparse_matrix()

    return "OK"


@app.route('/show_db', methods=['GET'])
def show_db():
    new_dict = dict(zip(range(coll.count()), coll.find()))

    documents = [doc for doc in coll.find()]
    return json_util.dumps({'cursor': documents})


@app.route('/delete', methods=['POST'])
def delete():
    delete_id = request.json
    delete_id = delete_id['id']
    doc = coll.find_one({'_id': ObjectId(delete_id)})
    fs.delete(doc['3d_model'])
    fs.delete(doc['Draw_img'])
    fs.delete(doc['draw_id_img'])
    fs.delete(doc['draw_id_img_preview'])
    vec_coll = db['vectors']
    vec_coll.remove(doc['id_vec'])
    coll.remove(ObjectId(delete_id))


app.run(host='0.0.0.0')
