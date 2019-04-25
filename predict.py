# -*- coding: utf-8 -*-


from collections import Counter

import numpy as np
import scipy.sparse as sp
from pymongo import MongoClient
from sklearn.neighbors import NearestNeighbors

import globals as _g


def load_sparse_matrix():
    conn = MongoClient(host=_g.HOST, port=27017)

    db = conn['vectors']
    coll = db['vecs']
    n_dims = 1792
    # n_dims = 2048
    count = 0

    these_preds = []
    id_parts = []
    for doc in coll.find():
        doc_vec = doc["vec_part"]
        len_vec = len(doc_vec)
        id_part = [doc["id_part"] for i in range(len_vec)]

        id_parts = id_parts + id_part

        count = count + len_vec
        # these_preds =these_preds+doc_vec
        flat_list = [item for sublist in doc_vec for item in sublist]
        these_preds = these_preds + flat_list

    preds = sp.lil_matrix((count, n_dims))
    these_preds = np.array(these_preds)
    shp = (count, n_dims)

    preds[:, :] = these_preds.reshape(shp)

    x_coo = preds.tocoo()
    row = x_coo.row
    col = x_coo.col
    data = x_coo.data
    shape = x_coo.shape

    z = sp.coo_matrix((data, (row, col)), shape=shape)
    print("load sparse matrix")

    return z, id_parts





def load_predictor(vec):
    vecs, id_parts = load_sparse_matrix()
    knn = NearestNeighbors(metric='cosine', algorithm='brute')
    knn.fit(vecs)

    dist, indices = knn.kneighbors(vec.reshape(1, -1), n_neighbors=5)
    dist, indices = dist.flatten(), indices.flatten()

    # def similarity(n_neighbors=20):
    # return _similar(vec, knn, filenames, n_neighbors)
    print([(id_parts[indices[i]], dist[i]) for i in range(len(indices))])

    return Counter([(id_parts[indices[i]]) for i in range(len(indices))]).most_common(3)
