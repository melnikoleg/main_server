import glob
import json
import os
import numpy as np
from bson import json_util
from flask import Flask, request, redirect, url_for
from pymongo import MongoClient
import subprocess
import gridfs
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask import jsonify
import threading

from werkzeug.utils import secure_filename

UPLOAD_FOLDER = ''

ALLOWED_EXTENSIONS = {'pdf', 'stl', 'PDF', 'STL', 'jpg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app = Flask(__name__)

conn = MongoClient(host='192.168.1.242', port=27017)
db = conn['Parts']
coll = db['Part']

fs = gridfs.GridFS(db)
fss = gridfs.GridFSBucket(db)


def thread(func):
    def wrapper(*args, **kwargs):
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.run()

    return wrapper()


def render_and_vect(path, id_part):
    try:

        subprocess.call(
            ["C:/Program Files/Blender Foundation/Blender/blender.exe", "phong_2.blend", "--background", "--python",
             "phong_2.py", "--", path, "F:/PROG/tmp46/"])
        # os.remove(path)
        import vectorize

        #id_vec = vectorize.vectorize_add(dir_name="F:/PROG/tmp46/",id_part=id_part)
        id_vec = vectorize.vectorize_add(dir_name="temp/",id_part=id_part)
        return id_vec

    except Exception as e:
        print(str(e))



@thread
@app.route('/image', methods=['POST'])
def recognize():
    try:
        data = request.json

        from predict import load_predictor
        num_data = np.array(data)
        #new_data = num_data + num_data
        # 2.183826
        #print(new_data)
        result = load_predictor(data)
        print(str(result))

        doc = coll.find_one(result)
        print(doc)

        return 'ok'

    except Exception as e:
        print(str(e))
        return dumps({'error': str(e)})


@thread
@app.route('/image_test', methods=['POST'])
def test():
    try:
        data = request.json
        # print(data)

        doc = coll.find_one(ObjectId("5c7d5698410d6c147835defe"))

        draw_img_preview = fss.open_download_stream(ObjectId(str(doc['draw_id_img_preview'])))
        # draw_img = fss.open_download_stream(ObjectId(str(doc['draw_id_img'])))

        json_data = {"predict_result": [{
            'draw_img_preview': draw_img_preview.read(),
            'draw_img_id': doc['draw_id_img'],
            'Name': doc['Name'],
            'Designation': doc['Designation'], }
        ]}

        print(json_util.dumps(json_data))
        return json_util.dumps(json_data)

    except Exception as e:
        print(str(e))
        return dumps({'error': str(e)})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@thread
@app.route('/get_image', methods=['POST'])
def fullImage():
    try:
        data = request.json
        print(data)
        print(data["id"])

        draw_img = fss.open_download_stream(ObjectId(str(data["id"])))
        # data ={"full_image":}
        respond = json_util.dumps(draw_img.read())
        print(respond)

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
                          })

    path_to_model = save_to_disk(file_model, model_id,str(id_doc))
    print(path_to_model)

    id_vec = render_and_vect(path_to_model, id_doc)

    coll.update({"_id" :ObjectId(id_doc) },{"$set" : {"id_vec":id_vec}})

    return "OK"


@app.route('/show_db', methods=['GET'])
def show_db():
    new_dict = dict(zip(range(coll.count()), coll.find()))

    documents = [doc for doc in coll.find()]
    return json_util.dumps({'cursor': documents})


app.run(host='0.0.0.0')
