import tensorflow as tf
from Trainer import Trainer, parse_args
import os
from model import *


args = parse_args()
data_path = args["datapath"]
data_path='/Users/ryanzotti/Documents/Data/Self-Driving-Car/printer-paper/data'
epochs = args["epochs"]
s3_bucket = args['s3_bucket']
show_speed = args['show_speed']
s3_sync = args['s3_sync']

sess = tf.InteractiveSession(config=tf.ConfigProto())

x = tf.placeholder(tf.float32, shape=[None, 240, 320, 3], name='x')
y_ = tf.placeholder(tf.float32, shape=[None, 2], name='y_')
phase = tf.placeholder(tf.bool, name='phase')

conv1 = batch_norm_conv_layer('layer1',x, [6, 6, 3, 24], phase)
conv2 = batch_norm_conv_layer('layer2',conv1, [6, 6, 24, 24], phase)
conv3 = batch_norm_conv_layer('layer3',conv2, [6, 6, 24, 24], phase)
conv4 = batch_norm_conv_layer('layer4',conv3, [6, 6, 24, 24], phase)

h_pool4_flat = tf.reshape(conv4, [-1, 240 * 320 * 24])
h5 = batch_norm_fc_layer('layer8',h_pool4_flat, [240 * 320 * 24, 128], phase)
W_final = weight_variable('layer12',[128, 2])
b_final = bias_variable('layer12',[2])
logits = tf.add(tf.matmul(h5, W_final), b_final, name='logits')

# TODO: Fix this x.shape[0] bug
rmse = tf.sqrt(tf.reduce_mean(tf.squared_difference(logits, y_)))

train_step = tf.train.AdamOptimizer(1e-5,name='train_step').minimize(rmse)

'''
    https://github.com/tensorflow/tensorflow/blob/master/tensorflow/contrib/layers/python/layers/layers.py#L396
    From the official TensorFlow docs:

        Note: When is_training is True the moving_mean and moving_variance need to be
        updated, by default the update_ops are placed in `tf.GraphKeys.UPDATE_OPS` so
        they need to be added as a dependency to the `train_op`, example:

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
              train_op = optimizer.minimize(loss)

    https://www.tensorflow.org/api_docs/python/tf/Graph#control_dependencies
    Regarding tf.control_dependencies:

        with g.control_dependencies([a, b, c]):
          # `d` and `e` will only run after `a`, `b`, and `c` have executed.
          d = ...
          e = ...

'''
update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
with tf.control_dependencies(update_ops):
    train_step = tf.train.AdamOptimizer(1e-5).minimize(rmse)

model_file = os.path.dirname(os.path.realpath(__file__)) + '/' + os.path.basename(__file__)
trainer = Trainer(data_path=data_path,
                  model_file=model_file,
                  s3_bucket=s3_bucket,
                  epochs=epochs,
                  max_sample_records=100,
                  show_speed=show_speed,
                  s3_sync=s3_sync)
trainer.train(sess=sess, x=x, y_=y_,
              optimization=rmse,
              train_step=train_step,
              train_feed_dict={'phase:0': True},
              test_feed_dict={})
