import bpy
import os.path
import math
import sys
import random
C = bpy.context
D = bpy.data
scene = D.scenes['Scene']

# cameras: a list of camera positions
# a camera position is defined by two parameters: (theta, phi),
# where we fix the "r" of (r, theta, phi) in spherical coordinate system.

# 5 orientations: front, right, back, left, top
#cameras = [(60, 0), (60, 90), (60, 180), (60, 270),(0, 0)]

# 12 orientations around the object with 30-deg elevation
#cameras = [(60, i) for i in range(0, 360, 30)]

cameras = [(0, 0), (0, 90),  (0, 120), (0, 180),(0, 210), (0, 270)]
render_setting = scene.render

# output image size = (W, H)
w = 224
h = 224
render_setting.resolution_x = w
render_setting.resolution_y = h


def main():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:]

    if len(argv) != 2:
        print('phong.py args: <3d mesh path> <image dir>')
        exit(-1)

    model = argv[0]
    image_dir = argv[1]


    init_camera()
    fix_camera_to_origin()

    do_model(model, image_dir)

def init_camera():
    cam = D.objects['Camera']
    # select the camera object
    scene.objects.active = cam
    cam.select = True

    # set the rendering mode to orthogonal and scale
    #C.object.data.type = 'ORTHO'
    #C.object.data.ortho_scale = 2.
    C.object.data.type = 'PERSP'


def fix_camera_to_origin():
    origin_name = 'Origin'

    # create origin
    try:
        origin = D.objects[origin_name]
    except KeyError:
        bpy.ops.object.empty_add(type='SPHERE')
        D.objects['Empty'].name = origin_name
        origin = D.objects[origin_name]

    origin.location = (0, 0, 0)

    cam = D.objects['Camera']
    scene.objects.active = cam
    cam.select = True

    if 'Track To' not in cam.constraints:
        bpy.ops.object.constraint_add(type='TRACK_TO')

    cam.constraints['Track To'].target = origin
    cam.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    cam.constraints['Track To'].up_axis = 'UP_Y'


def do_model(path, image_dir):
    name = load_model(path)
    center_model(name)
    normalize_model(name)
    image_subdir = os.path.join(image_dir)
    pos = [0, 90]
    for j in pos:
        for i, c in enumerate(cameras):
            D.objects[name].rotation_euler = (math.radians(j), math.radians(c[0]), math.radians(c[1]))
            #move_camera(c)
            render()
            save(image_subdir, name, i,j)

    delete_model(name)


def load_model(path):
    d = os.path.dirname(path)
    ext = path.split('.')[-1]

    name = os.path.basename(path).split('.')[0]
    # handle weird object naming by Blender for stl files
    if ext == 'stl':
        name = name.title().replace('_', ' ')

    if name not in D.objects:
        # print('loading :' + name)
        if ext == 'stl':
            bpy.ops.import_mesh.stl(filepath=path, directory=d,
                                    filter_glob='*.stl')
        else:
            print('Currently .{} file type is not supported.'.format(ext))
            exit(-1)
    return name


def delete_model(name):
    for ob in scene.objects:
        if ob.type == 'MESH' and ob.name.startswith(name):
            ob.select = True
        else:
            ob.select = False
    bpy.ops.object.delete()


def center_model(name):
    #bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN')
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    bpy.ops.object.modifier_add(type='EDGE_SPLIT')
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier="EdgeSplit")
    bpy.ops.object.shade_smooth()
    D.objects[name].location = (0, 0, 0)


def normalize_model(name):
    obj = D.objects[name]
    dim = obj.dimensions
    print('original dim:' + str(dim))
    if max(dim) > 0:
        dim = dim / max(dim)
    obj.dimensions = dim*3

    print('new dim:' + str(dim))


def move_camera(coord):
    def deg2rad(deg):
        return deg * math.pi / 180.

    r = 3.
    theta, phi = deg2rad(coord[0]), deg2rad(coord[1])
    loc_x = r * math.sin(theta) * math.cos(phi)
    loc_y = r * math.sin(theta) * math.sin(phi)
    loc_z = r * math.cos(theta)

    D.objects['Camera'].location = (loc_x, loc_y, loc_z)


def render():
    bpy.ops.render.render()


def save(image_dir, name, i, j=None):
    # path = os.path.join(image_dir + "/train/" + name, name + str(i) + "_" + str(j) + '.jpg')
    path = os.path.join("{}{}/{}{}{}".format(image_dir, name, str(i), str(j), '.jpg'))
    D.images['Render Result'].save_render(filepath=path)
    print('save to ' + path)


if __name__ == '__main__':
    main()
