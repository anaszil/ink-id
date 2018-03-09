"""
Train an ink classifier and produce predicted output for a volume.
"""

import argparse
import datetime
import os
import time

from sklearn.metrics import precision_score, fbeta_score
import tensorflow as tf
import numpy as np

from inkid.volumes import VolumeSet
import inkid.model
import inkid.ops


def main():
    """Run the training and prediction process."""
    start_time = time.time()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', metavar='path', required=True,
                        help='path to volume data (slices directory)')
    parser.add_argument('--groundtruth', metavar='path', required=True,
                        help='path to ground truth image')
    parser.add_argument('--surfacemask', metavar='path', required=True,
                        help='path to surface mask image')
    parser.add_argument('--surfacedata', metavar='path', required=True,
                        help='path to surface data')
    parser.add_argument('--gridtestsquare', metavar='num', default=0, type=int,
                        help='index of grid test square for this k-fold run')
    parser.add_argument('--outputdir', metavar='path', default='out',
                        help='path to output directory')

    args = parser.parse_args()

    # Load default parameters
    params = inkid.ops.load_default_parameters()

    # Adjust some parameters from supplied arguments
    params['volumes'][0]['data_path'] = args.data
    params['volumes'][0]['ground_truth'] = args.groundtruth
    params['volumes'][0]['surface_mask'] = args.surfacemask
    params['volumes'][0]['surface_data'] = args.surfacedata
    params['grid_test_square'] = args.gridtestsquare
    params['output_path'] = os.path.join(
        args.outputdir,
        '3dcnn-predictions',
        datetime.datetime.today().strftime('%Y-%m-%d_%H.%M.%S')
    )

    volumes = VolumeSet(params)

    run_config = tf.estimator.RunConfig(
        save_summary_steps=100,
        save_checkpoints_steps=params['display_every_n_steps'],
        keep_checkpoint_max=None, # save all checkpoints
    )
    
    estimator = tf.estimator.Estimator(
        model_fn=inkid.model.model_fn_3dcnn,
        model_dir=params['output_path'],
        config=run_config,
        params={
            'drop_rate': params['drop_rate'],
            'subvolume_shape': params['subvolume_shape'],
            'batch_norm_momentum': params['batch_norm_momentum'],
            'filters': params['filters'],
            'learning_rate': params['learning_rate'],
        },
    )

    tensors_to_log = {'train_accuracy': 'train_accuracy'}
    logging_hook = tf.train.LoggingTensorHook(
        tensors=tensors_to_log, every_n_iter=100)
    tf.logging.set_verbosity(tf.logging.INFO)
    
    estimator.train(
        input_fn=lambda: volumes.training_input_fn(
            params['training_batch_size'],
        ),
        # steps=params['training_steps'],
        hooks=[logging_hook],
        saving_listeners=[
            inkid.model.EvalCheckpointSaverListener(
                estimator=estimator,
                input_fn=lambda: volumes.evaluation_input_fn(
                    params['evaluation_batch_size'],
                ),
            ),
        ],
    )


if __name__ == '__main__':
    main()
