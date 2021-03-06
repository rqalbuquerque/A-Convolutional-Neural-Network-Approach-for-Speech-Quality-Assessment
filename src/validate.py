"""Error generation of validation set.

"""
import re
import csv
import sys
import os

import numpy as np
import tensorflow as tf

import utils
import config
import input_data
import models


def main(argv):
    # Get flags
    [FLAGS, config_dir] = argv

    # To see all the logging messages
    tf.logging.set_verbosity(tf.logging.INFO)

    # Start a new TensorFlow session.
    sess = tf.InteractiveSession()

    # Begin by making sure we have the training data we need.
    model_settings = models.prepare_model_settings(
        FLAGS.enable_hist_summary,
        FLAGS.sample_rate,
        FLAGS.clip_duration_ms,
        FLAGS.window_size_ms,
        FLAGS.window_stride_ms,
        FLAGS.data_aug_algorithms,
        FLAGS.feature,
        FLAGS.n_coeffs,
        FLAGS.conv_layers,
        FLAGS.filter_width,
        FLAGS.filter_height,
        FLAGS.filter_count,
        FLAGS.stride,
        FLAGS.apply_batch_norm,
        FLAGS.activation,
        FLAGS.kernel_regularizer,
        FLAGS.apply_dropout,
        FLAGS.fc_layers,
        FLAGS.hidden_units)

    audio_processor = input_data.AudioProcessor(
        FLAGS.data_dir,
        FLAGS.validation_percentage,
        FLAGS.testing_percentage,
        model_settings)

    # print size of validation data
    tf.logging.info("***************** DataBase Length *****************")
    tf.logging.info("Validation length: " + str(audio_processor.set_size('validation')))

    # input
    fingerprint_input = tf.placeholder(
        tf.float32, [None, model_settings['fingerprint_size']], name='fingerprint_input')

    # model
    estimator, phase_train = models.create_model(
        fingerprint_input, model_settings, FLAGS.model_architecture)

    # Merge all the summaries and create file writers
    merged_summaries = tf.summary.merge_all()

    tf.global_variables_initializer().run()
    models.load_variables_from_checkpoint(sess, FLAGS.start_checkpoint)

    tf.logging.info('***************** Analysis *****************')
    tf.logging.info('Error Analysis on config: ' + config_dir)
    tf.logging.info('***************** ******** *****************')
    
    analysis_dir = config_dir + '/analysis'
    output_dir = analysis_dir + '/error'
    utils.create_dir(output_dir)

    with open(output_dir + '/validation_errors.csv', 'wb') as csvfile:
        names, gts, scores, errors = [], [], [], []
        fieldnames = ['Name', 'GT', 'Score', 'Error']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        set_size = audio_processor.set_size('validation')

        for i in range(0, set_size, FLAGS.batch_size):
            validation_names, validation_fingerprints, validation_ground_truth = (
                audio_processor.get_data(FLAGS.batch_size, i, 'validation', sess))

            validation_summary, validation_scores = sess.run(
                [
                    merged_summaries,
                    estimator
                ],
                feed_dict={
                    fingerprint_input: validation_fingerprints,
                    phase_train: False
                })

            names += validation_names
            gts += validation_ground_truth.flatten().tolist()
            scores += validation_scores.flatten().tolist()
            errors += (validation_ground_truth-validation_scores).flatten().tolist()
            tf.logging.info('Running on batch: ' + str(i))

        csv_writer.writeheader()
        for i in range(0, len(names)):
            csv_writer.writerow({'Name': names[i], 'GT': str(
                gts[i]), 'Score': str(scores[i]), 'Error': str(errors[i])})

    tf.logging.info('***************** ******** *****************')

    sess.close()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        config_dir = sys.argv[1]
        FLAGS, _unparsed = config.set(
            config.read(config_dir + '/config.json'))
        tf.app.run(main=main, argv=[FLAGS, config_dir])
    else:
        raise ValueError('Invalid number of args!')
