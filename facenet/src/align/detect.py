"""Performs face alignment and stores face thumbnails in the output directory."""

# MIT License
# 
# Copyright (c) 2016 David Sandberg
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from scipy import misc
import sys
import os
import argparse
import random
import align_dlib  # @UnresolvedImport
import dlib
import facenet
import cv2

import mxnet as mx
import pdb
from lightened_moon import lightened_moon_feature
import numpy as np

#Given an image, draw bounding boxes for all faces detected in the image
#For each face in that image, predict the attributes of that face

def main(args):
    symbol = lightened_moon_feature(num_classes=40, use_fuse=True)
    detector = align_dlib.AlignDlib(os.path.expanduser(args.dlib_face_predictor))
    landmarkIndices = align_dlib.AlignDlib.OUTER_EYES_AND_NOSE
    img = cv2.imread(args.input_img)
    cropped_face = cv2.imread(args.cropped_img)
    scale = float(args.face_size) / args.image_size
    devs = mx.cpu()

    '''
    aligned = detector.align(args.image_size, img, landmarkIndices=landmarkIndices, skipMulti=False, scale=scale)

    if aligned is None:
        print('Failed to align')
        return
    '''

    face_boxes = detector.getAllFaceBoundingBoxes(img)

    if len(face_boxes) == 0:
        print('cannot find faces')

    for box in face_boxes:
        #print(dlib.rectangle.left(box))
        pad = [0.25, 0.25, 0.25, 0.25]
        left = int(max(0, box.left() - box.width()*float(pad[0])))
        top = int(max(0, box.top() - box.height()*float(pad[1])))
        right = int(min(img.shape[1], box.right() + box.width()*float(pad[2])))
        bottom = int(min(img.shape[0], box.bottom()+box.height()*float(pad[3])))

        cv2.rectangle(img, (left, top), (right, bottom), (0,255,0),3)       
        
        # crop face area
        gray = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (128, 128))/255.0
        #cv2.imshow('gray', gray)
        #cv2.waitKey(0)
        temp_img = np.expand_dims(np.expand_dims(gray, axis=0), axis=0)
        # get pred
        _, arg_params, aux_params = mx.model.load_checkpoint(args.model_load_prefix, args.model_load_epoch)
        arg_params['data'] = mx.nd.array(temp_img, devs)
        exector = symbol.bind(devs, arg_params ,args_grad=None, grad_req="null", aux_states=aux_params)
        exector.forward(is_train=False)
        exector.outputs[0].wait_to_read()
        output = exector.outputs[0].asnumpy()
        print(output)
        text = ["5_o_Clock_Shadow","Arched_Eyebrows","Attractive","Bags_Under_Eyes","Bald", "Bangs","Big_Lips","Big_Nose",
                "Black_Hair","Blond_Hair","Blurry","Brown_Hair","Bushy_Eyebrows","Chubby","Double_Chin","Eyeglasses","Goatee",
                "Gray_Hair", "Heavy_Makeup","High_Cheekbones","Male","Mouth_Slightly_Open","Mustache","Narrow_Eyes","No_Beard",
                "Oval_Face","Pale_Skin","Pointy_Nose","Receding_Hairline","Rosy_Cheeks","Sideburns","Smiling","Straight_Hair",
                "Wavy_Hair","Wearing_Earrings","Wearing_Hat","Wearing_Lipstick","Wearing_Necklace","Wearing_Necktie","Young"]
        pred = np.ones(40)
        #TODO process face qualities
        yes_attributes = []
        index = 0

        for num in output[0]:
            if num > 0:
                yes_attributes.append(text[index])
            index+=1

        pad = 20
        for attr in yes_attributes:
            cv2.putText(img, attr, (right, top), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
            top = top + pad


    cv2.imshow('detected faces', img)
    cv2.waitKey(0)

def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    
    parser.add_argument('input_img', type=str, help='Target image.')
    parser.add_argument('cropped_img', type=str, help='Cropped face')
    parser.add_argument('--dlib_face_predictor', type=str,
        help='File containing the dlib face predictor.', default='../data/shape_predictor_68_face_landmarks.dat')
    parser.add_argument('--image_size', type=int,
        help='Image size (height, width) in pixels.', default=160)
    parser.add_argument('--face_size', type=int,
        help='Size of the face thumbnail (height, width) in pixels.', default=96)
    parser.add_argument('--use_center_crop', 
        help='Use the center crop of the original image after scaling the image using prealigned_scale.', action='store_true')
    parser.add_argument('--prealigned_dir', type=str,
        help='Replace image with a pre-aligned version when face detection fails.', default='')
    parser.add_argument('--prealigned_scale', type=float,
        help='The amount of scaling to apply to prealigned images before taking the center crop.', default=0.87)

    parser.add_argument('--size', type=int, default=128,
                        help='the image size of lfw aligned image, only support squre size')
    parser.add_argument('--opencv', type=str, default='~/Desktop/mxnet-face/model/opencv/cascade.xml',
                        help='the opencv model path')
    parser.add_argument('--pad', type=float, nargs='+',
                                 help="pad (left,top,right,bottom) for face detection region")
    parser.add_argument('--model-load-prefix', type=str, default='lightened_moon/lightened_moon_fuse',
                        help='the prefix of the model to load')
    parser.add_argument('--model-load-epoch', type=int, default=82,
                        help='load the model on an epoch using the model-load-prefix')
    return parser.parse_args(argv)

if __name__ == '__main__':
    main(parse_arguments(sys.argv[1:]))