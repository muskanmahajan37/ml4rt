"""Methods for building, training, and applying neural nets."""

import copy
import pickle
import os.path
import numpy
import keras
from gewittergefahr.gg_utils import file_system_utils
from gewittergefahr.gg_utils import error_checking
from gewittergefahr.deep_learning import architecture_utils
from ml4rt.io import example_io
from ml4rt.utils import normalization
from ml4rt.machine_learning import keras_metrics as custom_metrics
from ml4rt.machine_learning import keras_losses as custom_losses

PLATEAU_PATIENCE_EPOCHS = 3
PLATEAU_LEARNING_RATE_MULTIPLIER = 0.5
PLATEAU_COOLDOWN_EPOCHS = 0
EARLY_STOPPING_PATIENCE_EPOCHS = 15
LOSS_PATIENCE = 0.005

DEFAULT_L1_WEIGHT = 0.
DEFAULT_L2_WEIGHT = 0.001

DEFAULT_CONV_LAYER_CHANNEL_NUMS = numpy.array([80, 80, 80, 3], dtype=int)
DEFAULT_CONV_LAYER_DROPOUT_RATES = numpy.array([0.5, 0.5, 0.5, numpy.nan])
DEFAULT_CONV_LAYER_FILTER_SIZES = numpy.array([5, 5, 5, 5], dtype=int)
DEFAULT_DENSE_NEURON_NUMS_FOR_CNN = numpy.array([409, 29, 2], dtype=int)
DEFAULT_DENSE_DROPOUT_RATES_FOR_CNN = numpy.array([0.5, 0.5, numpy.nan])

DEFAULT_DENSE_NEURON_NUMS_FOR_DNN = numpy.array(
    [1000, 605, 366, 221], dtype=int
)
DEFAULT_DENSE_DROPOUT_RATES_FOR_DNN = numpy.array([0.5, 0.5, 0.5, numpy.nan])

DEFAULT_INNER_ACTIV_FUNCTION_NAME = architecture_utils.RELU_FUNCTION_STRING
DEFAULT_INNER_ACTIV_FUNCTION_ALPHA = 0.2
DEFAULT_OUTPUT_ACTIV_FUNCTION_NAME = architecture_utils.RELU_FUNCTION_STRING
DEFAULT_OUTPUT_ACTIV_FUNCTION_ALPHA = 0.

EXAMPLE_DIRECTORY_KEY = 'example_dir_name'
BATCH_SIZE_KEY = 'num_examples_per_batch'
SCALAR_PREDICTOR_NAMES_KEY = 'scalar_predictor_names'
VECTOR_PREDICTOR_NAMES_KEY = 'vector_predictor_names'
SCALAR_TARGET_NAMES_KEY = 'scalar_target_names'
VECTOR_TARGET_NAMES_KEY = 'vector_target_names'
HEIGHTS_KEY = 'heights_m_agl'
FIRST_TIME_KEY = 'first_time_unix_sec'
LAST_TIME_KEY = 'last_time_unix_sec'
NORMALIZATION_FILE_KEY = 'normalization_file_name'
PREDICTOR_NORM_TYPE_KEY = 'predictor_norm_type_string'
PREDICTOR_MIN_NORM_VALUE_KEY = 'predictor_min_norm_value'
PREDICTOR_MAX_NORM_VALUE_KEY = 'predictor_max_norm_value'
TARGET_NORM_TYPE_KEY = 'target_norm_type_string'
TARGET_MIN_NORM_VALUE_KEY = 'target_min_norm_value'
TARGET_MAX_NORM_VALUE_KEY = 'target_max_norm_value'

DEFAULT_GENERATOR_OPTION_DICT = {
    SCALAR_PREDICTOR_NAMES_KEY: example_io.SCALAR_PREDICTOR_NAMES,
    VECTOR_PREDICTOR_NAMES_KEY: example_io.VECTOR_PREDICTOR_NAMES,
    SCALAR_TARGET_NAMES_KEY: example_io.SCALAR_TARGET_NAMES,
    VECTOR_TARGET_NAMES_KEY: example_io.VECTOR_TARGET_NAMES,
    HEIGHTS_KEY: example_io.DEFAULT_HEIGHTS_M_AGL,
    PREDICTOR_NORM_TYPE_KEY: normalization.Z_SCORE_NORM_STRING,
    PREDICTOR_MIN_NORM_VALUE_KEY: None,
    PREDICTOR_MAX_NORM_VALUE_KEY: None,
    TARGET_NORM_TYPE_KEY: normalization.MINMAX_NORM_STRING,
    TARGET_MIN_NORM_VALUE_KEY: 0.,
    TARGET_MAX_NORM_VALUE_KEY: 1.
}

NUM_HEIGHTS_KEY = 'num_heights'
NUM_INPUT_CHANNELS_KEY = 'num_input_channels'
NUM_INPUTS_KEY = 'num_inputs'
CONV_LAYER_CHANNEL_NUMS_KEY = 'conv_layer_channel_nums'
CONV_LAYER_DROPOUT_RATES_KEY = 'conv_layer_dropout_rates'
CONV_LAYER_FILTER_SIZES_KEY = 'conv_layer_filter_sizes'
DENSE_LAYER_NEURON_NUMS_KEY = 'dense_layer_neuron_nums'
DENSE_LAYER_DROPOUT_RATES_KEY = 'dense_layer_dropout_rates'
INNER_ACTIV_FUNCTION_KEY = 'inner_activ_function_name'
INNER_ACTIV_FUNCTION_ALPHA_KEY = 'inner_activ_function_alpha'
OUTPUT_ACTIV_FUNCTION_KEY = 'output_activ_function_name'
OUTPUT_ACTIV_FUNCTION_ALPHA_KEY = 'output_activ_function_alpha'
L1_WEIGHT_KEY = 'l1_weight'
L2_WEIGHT_KEY = 'l2_weight'
USE_BATCH_NORM_KEY = 'use_batch_normalization'

DEFAULT_CNN_ARCH_OPTION_DICT = {
    CONV_LAYER_CHANNEL_NUMS_KEY: DEFAULT_CONV_LAYER_CHANNEL_NUMS,
    CONV_LAYER_DROPOUT_RATES_KEY: DEFAULT_CONV_LAYER_DROPOUT_RATES,
    CONV_LAYER_FILTER_SIZES_KEY: DEFAULT_CONV_LAYER_FILTER_SIZES,
    DENSE_LAYER_NEURON_NUMS_KEY: DEFAULT_DENSE_NEURON_NUMS_FOR_CNN,
    DENSE_LAYER_DROPOUT_RATES_KEY: DEFAULT_DENSE_DROPOUT_RATES_FOR_CNN,
    INNER_ACTIV_FUNCTION_KEY: DEFAULT_INNER_ACTIV_FUNCTION_NAME,
    INNER_ACTIV_FUNCTION_ALPHA_KEY: DEFAULT_INNER_ACTIV_FUNCTION_ALPHA,
    OUTPUT_ACTIV_FUNCTION_KEY: DEFAULT_OUTPUT_ACTIV_FUNCTION_NAME,
    OUTPUT_ACTIV_FUNCTION_ALPHA_KEY: DEFAULT_OUTPUT_ACTIV_FUNCTION_ALPHA,
    L1_WEIGHT_KEY: DEFAULT_L1_WEIGHT,
    L2_WEIGHT_KEY: DEFAULT_L2_WEIGHT,
    USE_BATCH_NORM_KEY: True
}

DEFAULT_DNN_ARCH_OPTION_DICT = {
    DENSE_LAYER_NEURON_NUMS_KEY: DEFAULT_DENSE_NEURON_NUMS_FOR_DNN,
    DENSE_LAYER_DROPOUT_RATES_KEY: DEFAULT_DENSE_DROPOUT_RATES_FOR_DNN,
    INNER_ACTIV_FUNCTION_KEY: DEFAULT_INNER_ACTIV_FUNCTION_NAME,
    INNER_ACTIV_FUNCTION_ALPHA_KEY: DEFAULT_INNER_ACTIV_FUNCTION_ALPHA,
    OUTPUT_ACTIV_FUNCTION_KEY: DEFAULT_OUTPUT_ACTIV_FUNCTION_NAME,
    OUTPUT_ACTIV_FUNCTION_ALPHA_KEY: DEFAULT_OUTPUT_ACTIV_FUNCTION_ALPHA,
    L1_WEIGHT_KEY: DEFAULT_L1_WEIGHT,
    L2_WEIGHT_KEY: DEFAULT_L2_WEIGHT,
    USE_BATCH_NORM_KEY: True
}

METRIC_FUNCTION_LIST = [
    custom_metrics.mean_bias, custom_metrics.mean_absolute_error,
    custom_metrics.mae_skill_score, custom_metrics.mean_squared_error,
    custom_metrics.mse_skill_score, custom_metrics.correlation
]

METRIC_FUNCTION_DICT = {
    'mean_bias': custom_metrics.mean_bias,
    'mean_absolute_error': custom_metrics.mean_absolute_error,
    'mae_skill_score': custom_metrics.mae_skill_score,
    'mean_squared_error': custom_metrics.mean_squared_error,
    'mse_skill_score': custom_metrics.mse_skill_score,
    'correlation': custom_metrics.correlation
}

NUM_EPOCHS_KEY = 'num_epochs'
NUM_TRAINING_BATCHES_KEY = 'num_training_batches_per_epoch'
TRAINING_OPTIONS_KEY = 'training_option_dict'
NUM_VALIDATION_BATCHES_KEY = 'num_validation_batches_per_epoch'
VALIDATION_OPTIONS_KEY = 'validation_option_dict'
IS_CNN_KEY = 'is_cnn'
CUSTOM_LOSS_KEY = 'custom_loss_dict'

METADATA_KEYS = [
    NUM_EPOCHS_KEY, NUM_TRAINING_BATCHES_KEY, TRAINING_OPTIONS_KEY,
    NUM_VALIDATION_BATCHES_KEY, VALIDATION_OPTIONS_KEY, IS_CNN_KEY,
    CUSTOM_LOSS_KEY
]

TOA_UP_FLUX_INDEX_KEY = 'toa_up_flux_index'
TOA_UP_FLUX_WEIGHT_KEY = 'toa_up_flux_weight'
SURFACE_DOWN_FLUX_INDEX_KEY = 'surface_down_flux_index'
SURFACE_DOWN_FLUX_WEIGHT_KEY = 'surface_down_flux_weight'
UP_FLUX_CHANNEL_INDEX_KEY = 'up_flux_channel_index'
DOWN_FLUX_CHANNEL_INDEX_KEY = 'down_flux_channel_index'
HIGHEST_UP_FLUX_INDEX_KEY = 'highest_up_flux_index'
LOWEST_DOWN_FLUX_INDEX_KEY = 'lowest_down_flux_index'
NET_FLUX_WEIGHT_KEY = 'net_flux_weight'


def _check_architecture_args(option_dict, is_cnn):
    """Error-checks input arguments for architecture.

    :param option_dict: See doc for `make_cnn` or `make_dense_net`.
    :return: option_dict: Same as input, except defaults may have been added.
    """

    error_checking.assert_is_boolean(is_cnn)
    orig_option_dict = option_dict.copy()

    if is_cnn:
        option_dict = DEFAULT_CNN_ARCH_OPTION_DICT.copy()
    else:
        option_dict = DEFAULT_DNN_ARCH_OPTION_DICT.copy()

    option_dict.update(orig_option_dict)

    if is_cnn:
        num_heights = option_dict[NUM_HEIGHTS_KEY]
        error_checking.assert_is_integer(num_heights)
        error_checking.assert_is_geq(num_heights, 10)

        num_input_channels = option_dict[NUM_INPUT_CHANNELS_KEY]
        error_checking.assert_is_integer(num_input_channels)
        error_checking.assert_is_geq(num_input_channels, 1)

        conv_layer_channel_nums = option_dict[CONV_LAYER_CHANNEL_NUMS_KEY]
        error_checking.assert_is_integer_numpy_array(conv_layer_channel_nums)
        error_checking.assert_is_numpy_array(
            conv_layer_channel_nums, num_dimensions=1
        )
        error_checking.assert_is_geq_numpy_array(conv_layer_channel_nums, 1)

        num_conv_layers = len(conv_layer_channel_nums)
        these_dimensions = numpy.array([num_conv_layers], dtype=int)

        conv_layer_dropout_rates = option_dict[CONV_LAYER_DROPOUT_RATES_KEY]
        error_checking.assert_is_numpy_array(
            conv_layer_dropout_rates, exact_dimensions=these_dimensions
        )
        error_checking.assert_is_leq_numpy_array(
            conv_layer_dropout_rates, 1., allow_nan=True
        )

        # TODO(thunderhoser): Also make sure filter sizes are odd?
        conv_layer_filter_sizes = option_dict[CONV_LAYER_FILTER_SIZES_KEY]
        error_checking.assert_is_integer_numpy_array(conv_layer_filter_sizes)
        error_checking.assert_is_numpy_array(
            conv_layer_filter_sizes, exact_dimensions=these_dimensions
        )
        error_checking.assert_is_geq_numpy_array(conv_layer_filter_sizes, 3)
    else:
        num_inputs = option_dict[NUM_INPUTS_KEY]
        error_checking.assert_is_integer(num_inputs)
        error_checking.assert_is_geq(num_inputs, 10)

    dense_layer_neuron_nums = option_dict[DENSE_LAYER_NEURON_NUMS_KEY]
    error_checking.assert_is_integer_numpy_array(dense_layer_neuron_nums)
    error_checking.assert_is_numpy_array(
        dense_layer_neuron_nums, num_dimensions=1
    )
    error_checking.assert_is_geq_numpy_array(dense_layer_neuron_nums, 1)

    num_dense_layers = len(dense_layer_neuron_nums)
    these_dimensions = numpy.array([num_dense_layers], dtype=int)

    dense_layer_dropout_rates = option_dict[DENSE_LAYER_DROPOUT_RATES_KEY]
    error_checking.assert_is_numpy_array(
        dense_layer_dropout_rates, exact_dimensions=these_dimensions
    )
    error_checking.assert_is_leq_numpy_array(
        dense_layer_dropout_rates, 1., allow_nan=True
    )

    l1_weight = option_dict[L1_WEIGHT_KEY]
    error_checking.assert_is_geq(l1_weight, 0.)

    l2_weight = option_dict[L2_WEIGHT_KEY]
    error_checking.assert_is_geq(l2_weight, 0.)

    use_batch_normalization = option_dict[USE_BATCH_NORM_KEY]
    error_checking.assert_is_boolean(use_batch_normalization)

    return option_dict


def _check_generator_args(option_dict):
    """Error-checks input arguments for generator.

    :param option_dict: See doc for `cnn_generator` or `dense_net_generator`.
    :return: option_dict: Same as input, except defaults may have been added.
    """

    orig_option_dict = option_dict.copy()
    option_dict = DEFAULT_GENERATOR_OPTION_DICT.copy()
    option_dict.update(orig_option_dict)

    error_checking.assert_is_integer(option_dict[BATCH_SIZE_KEY])
    error_checking.assert_is_geq(option_dict[BATCH_SIZE_KEY], 32)

    error_checking.assert_is_numpy_array(
        numpy.array(option_dict[SCALAR_PREDICTOR_NAMES_KEY]), num_dimensions=1
    )
    error_checking.assert_is_numpy_array(
        numpy.array(option_dict[VECTOR_PREDICTOR_NAMES_KEY]), num_dimensions=1
    )
    error_checking.assert_is_numpy_array(
        numpy.array(option_dict[SCALAR_TARGET_NAMES_KEY]), num_dimensions=1
    )
    error_checking.assert_is_numpy_array(
        numpy.array(option_dict[VECTOR_TARGET_NAMES_KEY]), num_dimensions=1
    )

    error_checking.assert_is_numpy_array(
        option_dict[HEIGHTS_KEY], num_dimensions=1
    )
    error_checking.assert_is_geq_numpy_array(option_dict[HEIGHTS_KEY], 0.)

    error_checking.assert_is_string(option_dict[PREDICTOR_NORM_TYPE_KEY])
    error_checking.assert_is_string(option_dict[TARGET_NORM_TYPE_KEY])

    return option_dict


def _check_inference_args(predictor_matrix, num_examples_per_batch, verbose):
    """Error-checks arguments for `apply_cnn` or `apply_dense_net`.

    :param predictor_matrix: See doc for `apply_cnn` or `apply_dense_net`.
    :param num_examples_per_batch: Batch size.
    :param verbose: Boolean flag.  If True, will print progress messages during
        inference.
    :return: num_examples_per_batch: Batch size (may be different than input).
    """

    error_checking.assert_is_numpy_array_without_nan(predictor_matrix)
    num_examples = predictor_matrix.shape[0]

    if num_examples_per_batch is None:
        num_examples_per_batch = num_examples + 0
    else:
        error_checking.assert_is_integer(num_examples_per_batch)
        error_checking.assert_is_geq(num_examples_per_batch, 100)

    num_examples_per_batch = min([num_examples_per_batch, num_examples])
    error_checking.assert_is_boolean(verbose)

    return num_examples_per_batch


def _write_metadata(
        pickle_file_name, num_epochs, num_training_batches_per_epoch,
        training_option_dict, num_validation_batches_per_epoch,
        validation_option_dict, is_cnn, custom_loss_dict):
    """Writes metadata to Pickle file.

    :param pickle_file_name: Path to output file.
    :param num_epochs: See doc for `train_neural_net`.
    :param num_training_batches_per_epoch: Same.
    :param training_option_dict: Same.
    :param num_validation_batches_per_epoch: Same.
    :param validation_option_dict: Same.
    :param is_cnn: Same.
    :param custom_loss_dict: Same.
    """

    metadata_dict = {
        NUM_EPOCHS_KEY: num_epochs,
        NUM_TRAINING_BATCHES_KEY: num_training_batches_per_epoch,
        TRAINING_OPTIONS_KEY: training_option_dict,
        NUM_VALIDATION_BATCHES_KEY: num_validation_batches_per_epoch,
        VALIDATION_OPTIONS_KEY: validation_option_dict,
        IS_CNN_KEY: is_cnn,
        CUSTOM_LOSS_KEY: custom_loss_dict
    }

    file_system_utils.mkdir_recursive_if_necessary(file_name=pickle_file_name)

    pickle_file_handle = open(pickle_file_name, 'wb')
    pickle.dump(metadata_dict, pickle_file_handle)
    pickle_file_handle.close()


def _read_file_for_generator(
        example_file_name, num_examples_to_keep, for_inference,
        first_time_unix_sec, last_time_unix_sec, field_names, heights_m_agl,
        training_example_dict, predictor_norm_type_string,
        predictor_min_norm_value, predictor_max_norm_value,
        target_norm_type_string, target_min_norm_value, target_max_norm_value,
        first_example_to_keep=None):
    """Reads one file for generator.

    :param example_file_name: Path to input file (will be read by
        `example_io.read_file`).
    :param num_examples_to_keep: Number of examples to keep.
    :param for_inference: Boolean flag.  If True, data are being used for
        inference stage (applying trained model to new data).  If False, data
        are being used for training or monitoring (on-the-fly validation).
    :param first_time_unix_sec: See doc for `cnn_generator` or
        `dense_net_generator`.
    :param last_time_unix_sec: Same.
    :param field_names: 1-D list of fields to keep.
    :param heights_m_agl: 1-D numpy array of heights to keep (metres above
        ground level).
    :param training_example_dict: Dictionary with training examples (in format
        specified by `example_io.read_file`), which will be used for
        normalization.
    :param predictor_norm_type_string: Same.
    :param predictor_min_norm_value: Same.
    :param predictor_max_norm_value: Same.
    :param target_norm_type_string: Same.
    :param target_min_norm_value: Same.
    :param target_max_norm_value: Same.
    :param first_example_to_keep: Index of first example to keep.  If specified,
        this method will return examples i through i + N - 1, where
        i = `first_example_to_keep` and N = `num_examples_to_keep`.  If None,
        this method will return N random examples.
    :return: example_dict: See doc for `example_io.read_file`.
    :return: example_id_strings: 1-D list of IDs created by
        `example_io.create_example_ids`.  If `for_inference == False`, this is
        None.
    """

    print('\nReading data from: "{0:s}"...'.format(example_file_name))
    example_dict = example_io.read_file(example_file_name)

    example_dict = example_io.reduce_sample_size(
        example_dict=example_dict, num_examples_to_keep=num_examples_to_keep,
        first_example_to_keep=first_example_to_keep
    )
    example_dict = example_io.subset_by_time(
        example_dict=example_dict,
        first_time_unix_sec=first_time_unix_sec,
        last_time_unix_sec=last_time_unix_sec
    )
    example_dict = example_io.subset_by_field(
        example_dict=example_dict, field_names=field_names
    )
    example_dict = example_io.subset_by_height(
        example_dict=example_dict, heights_m_agl=heights_m_agl
    )

    print('Applying {0:s} normalization to predictors...'.format(
        predictor_norm_type_string.upper()
    ))
    example_dict = normalization.normalize_data(
        new_example_dict=example_dict,
        training_example_dict=training_example_dict,
        normalization_type_string=predictor_norm_type_string,
        min_normalized_value=predictor_min_norm_value,
        max_normalized_value=predictor_max_norm_value,
        separate_heights=True,
        apply_to_predictors=True, apply_to_targets=False
    )

    print('Applying {0:s} normalization to targets...'.format(
        target_norm_type_string.upper()
    ))
    example_dict = normalization.normalize_data(
        new_example_dict=example_dict,
        training_example_dict=training_example_dict,
        normalization_type_string=target_norm_type_string,
        min_normalized_value=target_min_norm_value,
        max_normalized_value=target_max_norm_value,
        separate_heights=True,
        apply_to_predictors=False, apply_to_targets=True
    )

    if for_inference:
        example_id_strings = example_io.create_example_ids(example_dict)
    else:
        example_id_strings = None

    return example_dict, example_id_strings


def _get_custom_loss_function(custom_loss_dict, for_cnn):
    """Creates custom loss function.

    TOA = top of atmosphere

    :param custom_loss_dict: Dictionary with the following keys.
    custom_loss_dict['toa_up_flux_index']: Variable index (in scalar output
        matrix) for TOA upwelling flux.
    custom_loss_dict['toa_up_flux_weight']: Weight used to penalize difference
        between TOA upwelling flux and upwelling flux at max height in profile.
    custom_loss_dict['surface_down_flux_index']: Variable index (in scalar
        output matrix) for surface downwelling flux.
    custom_loss_dict['surface_down_flux_weight']: Weight used to penalize
        difference between surface downwelling flux and downwelling flux at
        lowest height in profile.
    custom_loss_dict['net_flux_weight']: Weight used to penalize difference
        between actual and predicted net flux (surface downwelling minus TOA
        upwelling).

    If `for_cnn == True`, expect the following keys.

    custom_loss_dict['up_flux_channel_index']: Channel index (in vector target
        matrix) for upwelling flux.
    custom_loss_dict['down_flux_channel_index']: Channel index (in vector target
        matrix) for downwelling flux.

    If `for_cnn == False`, expect the following keys.

    custom_loss_dict['highest_up_flux_index']: Variable index (in scalar output
        matrix) for upwelling flux at max height in profile.
    custom_loss_dict['lowest_down_flux_index']: Variable index (in scalar output
        matrix) for downwelling flux at lowest height in profile.

    :param for_cnn: Boolean flag.  If True, loss function is for a CNN.  If
        False, loss function is for a dense net.
    :return: loss_function: The function itself.
    """

    error_checking.assert_is_boolean(for_cnn)

    toa_up_flux_index = custom_loss_dict[TOA_UP_FLUX_INDEX_KEY]
    toa_up_flux_weight = custom_loss_dict[TOA_UP_FLUX_WEIGHT_KEY]
    surface_down_flux_index = custom_loss_dict[SURFACE_DOWN_FLUX_INDEX_KEY]
    surface_down_flux_weight = (
        custom_loss_dict[SURFACE_DOWN_FLUX_WEIGHT_KEY]
    )
    net_flux_weight = custom_loss_dict[NET_FLUX_WEIGHT_KEY]

    error_checking.assert_is_integer(toa_up_flux_index)
    error_checking.assert_is_geq(toa_up_flux_index, 0)
    error_checking.assert_is_integer(surface_down_flux_index)
    error_checking.assert_is_geq(surface_down_flux_index, 0)

    if for_cnn:
        up_flux_channel_index = custom_loss_dict[UP_FLUX_CHANNEL_INDEX_KEY]
        down_flux_channel_index = custom_loss_dict[DOWN_FLUX_CHANNEL_INDEX_KEY]

        error_checking.assert_is_integer(up_flux_channel_index)
        error_checking.assert_is_geq(up_flux_channel_index, 0)
        error_checking.assert_is_integer(down_flux_channel_index)
        error_checking.assert_is_geq(down_flux_channel_index, 0)

        return custom_losses.constrained_mse(
            toa_up_flux_index=toa_up_flux_index + 2,
            toa_up_flux_weight=toa_up_flux_weight,
            surface_down_flux_index=surface_down_flux_index + 2,
            surface_down_flux_weight=surface_down_flux_weight,
            highest_up_flux_index=0, lowest_down_flux_index=1,
            net_flux_weight=net_flux_weight, for_cnn=True
        )

    highest_up_flux_index = custom_loss_dict[HIGHEST_UP_FLUX_INDEX_KEY]
    lowest_down_flux_index = custom_loss_dict[LOWEST_DOWN_FLUX_INDEX_KEY]

    error_checking.assert_is_integer(highest_up_flux_index)
    error_checking.assert_is_geq(highest_up_flux_index, 0)
    error_checking.assert_is_integer(lowest_down_flux_index)
    error_checking.assert_is_geq(lowest_down_flux_index, 0)

    return custom_losses.constrained_mse(
        toa_up_flux_index=toa_up_flux_index,
        toa_up_flux_weight=toa_up_flux_weight,
        surface_down_flux_index=surface_down_flux_index,
        surface_down_flux_weight=surface_down_flux_weight,
        highest_up_flux_index=highest_up_flux_index,
        lowest_down_flux_index=lowest_down_flux_index,
        net_flux_weight=net_flux_weight, for_cnn=False
    )


def predictors_dict_to_numpy(example_dict, for_cnn):
    """Converts predictors from dictionary to numpy array.

    :param example_dict: Dictionary of examples (in the format returned by
        `example_io.read_file`).
    :param for_cnn: Boolean flag.  If True, will return format required by CNN.
        If False, will return format required by dense neural net.
    :return: predictor_matrix: See output doc for `cnn_generator` or
        `dense_net_generator`.
    """

    error_checking.assert_is_boolean(for_cnn)

    if for_cnn:
        num_heights = len(example_dict[example_io.HEIGHTS_KEY])

        scalar_predictor_matrix = (
            example_dict[example_io.SCALAR_PREDICTOR_VALS_KEY]
        )
        scalar_predictor_matrix = numpy.expand_dims(
            scalar_predictor_matrix, axis=1
        )
        scalar_predictor_matrix = numpy.repeat(
            scalar_predictor_matrix, repeats=num_heights, axis=1
        )

        return numpy.concatenate((
            example_dict[example_io.VECTOR_PREDICTOR_VALS_KEY],
            scalar_predictor_matrix
        ), axis=-1)

    vector_predictor_matrix = example_dict[example_io.VECTOR_PREDICTOR_VALS_KEY]
    num_examples = vector_predictor_matrix.shape[0]
    num_heights = vector_predictor_matrix.shape[1]
    num_fields = vector_predictor_matrix.shape[2]

    vector_predictor_matrix = numpy.reshape(
        vector_predictor_matrix, (num_examples, num_heights * num_fields),
        order='F'
    )

    return numpy.concatenate((
        vector_predictor_matrix,
        example_dict[example_io.SCALAR_PREDICTOR_VALS_KEY]
    ), axis=-1)


def predictors_numpy_to_dict(predictor_matrix, example_dict, for_cnn):
    """Converts predictors from numpy array to dictionary.

    This method is the inverse of `predictors_dict_to_numpy`.

    :param predictor_matrix: numpy array created by `predictors_dict_to_numpy`.
    :param example_dict: Dictionary with the following keys.  See doc for
        `example_io.read_file` for details on each key.
    example_dict['scalar_predictor_names']
    example_dict['vector_predictor_names']
    example_dict['heights_m_agl']

    :param for_cnn: Boolean flag.  If True, will assume that `predictor_matrix`
        contains predictors in format required by CNN.  If False, will assume
        that it contains predictors in format required by dense neural net.

    :return: example_dict: Dictionary with the following keys.  See doc for
        `example_io.read_file` for details on each key.
    example_dict['scalar_predictor_matrix']
    example_dict['vector_predictor_matrix']
    """

    error_checking.assert_is_numpy_array_without_nan(predictor_matrix)
    error_checking.assert_is_boolean(for_cnn)

    num_scalar_predictors = len(
        example_dict[example_io.SCALAR_PREDICTOR_NAMES_KEY]
    )

    if for_cnn:
        error_checking.assert_is_numpy_array(predictor_matrix, num_dimensions=3)

        scalar_predictor_matrix = (
            predictor_matrix[:, 0, -num_scalar_predictors:]
        )
        vector_predictor_matrix = predictor_matrix[..., :-num_scalar_predictors]

        return {
            example_io.SCALAR_PREDICTOR_VALS_KEY: scalar_predictor_matrix,
            example_io.VECTOR_PREDICTOR_VALS_KEY: vector_predictor_matrix
        }

    error_checking.assert_is_numpy_array(predictor_matrix, num_dimensions=2)

    scalar_predictor_matrix = predictor_matrix[:, -num_scalar_predictors:]
    vector_predictor_matrix = predictor_matrix[:, :-num_scalar_predictors]

    num_heights = len(example_dict[example_io.HEIGHTS_KEY])
    num_vector_predictors = len(
        example_dict[example_io.VECTOR_PREDICTOR_NAMES_KEY]
    )
    num_examples = vector_predictor_matrix.shape[0]

    vector_predictor_matrix = numpy.reshape(
        vector_predictor_matrix,
        (num_examples, num_heights, num_vector_predictors),
        order='F'
    )

    return {
        example_io.SCALAR_PREDICTOR_VALS_KEY: scalar_predictor_matrix,
        example_io.VECTOR_PREDICTOR_VALS_KEY: vector_predictor_matrix
    }


def targets_dict_to_numpy(example_dict, for_cnn, use_custom_cnn_loss):
    """Converts targets from dictionary to numpy array.

    :param example_dict: Dictionary of examples (in the format returned by
        `example_io.read_file`).
    :param for_cnn: Boolean flag.  If True, will return format required by CNN.
        If False, will return format required by dense neural net.
    :param use_custom_cnn_loss: Boolean flag.  If True, using custom loss for
        CNN.
    :return: target_matrices: If `for_cnn == True`, same as output from
        `cnn_generator`.  If `for_cnn == False`, same as output from
        `dense_net_generator` but in a one-element list.
    """

    error_checking.assert_is_boolean(for_cnn)
    if not for_cnn:
        use_custom_cnn_loss = False
    error_checking.assert_is_boolean(use_custom_cnn_loss)

    if for_cnn:
        if not use_custom_cnn_loss:
            return [
                example_dict[example_io.VECTOR_TARGET_VALS_KEY],
                example_dict[example_io.SCALAR_TARGET_VALS_KEY]
            ]

        up_flux_channel_index = (
            example_dict[example_io.VECTOR_TARGET_NAMES_KEY].index(
                example_io.SHORTWAVE_UP_FLUX_NAME
            )
        )
        down_flux_channel_index = (
            example_dict[example_io.VECTOR_TARGET_NAMES_KEY].index(
                example_io.SHORTWAVE_DOWN_FLUX_NAME
            )
        )

        vector_target_matrix = example_dict[example_io.VECTOR_TARGET_VALS_KEY]
        scalar_target_matrix = example_dict[example_io.SCALAR_TARGET_VALS_KEY]

        this_vector_target_matrix = numpy.stack((
            vector_target_matrix[:, -1, up_flux_channel_index],
            vector_target_matrix[:, 0, down_flux_channel_index],
        ), axis=-1)

        scalar_target_matrix = numpy.concatenate((
            this_vector_target_matrix, scalar_target_matrix
        ), axis=-1)

        return [vector_target_matrix, scalar_target_matrix]

    vector_target_matrix = example_dict[example_io.VECTOR_TARGET_VALS_KEY]
    num_examples = vector_target_matrix.shape[0]
    num_heights = vector_target_matrix.shape[1]
    num_fields = vector_target_matrix.shape[2]

    vector_target_matrix = numpy.reshape(
        vector_target_matrix, (num_examples, num_heights * num_fields),
        order='F'
    )

    target_matrix = numpy.concatenate((
        vector_target_matrix,
        example_dict[example_io.SCALAR_TARGET_VALS_KEY]
    ), axis=-1)

    return [target_matrix]


def targets_numpy_to_dict(target_matrices, example_dict, for_cnn):
    """Converts targets from numpy array to dictionary.

    This method is the inverse of `targets_dict_to_numpy`.

    :param target_matrices: List created by `targets_dict_to_numpy`.
    :param example_dict: Dictionary with the following keys.  See doc for
        `example_io.read_file` for details on each key.
    example_dict['scalar_target_names']
    example_dict['vector_target_names']
    example_dict['heights_m_agl']

    :param for_cnn: Boolean flag.  If True, will assume that `target_matrices`
        contains targets in format required by CNN.  If False, will assume
        that it contains targets in format required by dense neural net.

    :return: example_dict: Dictionary with the following keys.  See doc for
        `example_io.read_file` for details on each key.
    example_dict['scalar_target_matrix']
    example_dict['vector_target_matrix']
    """

    error_checking.assert_is_boolean(for_cnn)

    if for_cnn:
        vector_target_matrix = target_matrices[0]
        scalar_target_matrix = target_matrices[1]

        error_checking.assert_is_numpy_array_without_nan(vector_target_matrix)
        error_checking.assert_is_numpy_array(
            vector_target_matrix, num_dimensions=3
        )

        error_checking.assert_is_numpy_array_without_nan(scalar_target_matrix)
        error_checking.assert_is_numpy_array(
            scalar_target_matrix, num_dimensions=2
        )

        return {
            example_io.SCALAR_TARGET_VALS_KEY: scalar_target_matrix,
            example_io.VECTOR_TARGET_VALS_KEY: vector_target_matrix
        }

    target_matrix = target_matrices[0]
    num_scalar_targets = len(example_dict[example_io.SCALAR_TARGET_NAMES_KEY])

    scalar_target_matrix = target_matrix[:, -num_scalar_targets:]
    vector_target_matrix = target_matrix[:, :-num_scalar_targets]

    num_heights = len(example_dict[example_io.HEIGHTS_KEY])
    num_vector_targets = len(
        example_dict[example_io.VECTOR_TARGET_NAMES_KEY]
    )
    num_examples = vector_target_matrix.shape[0]

    vector_target_matrix = numpy.reshape(
        vector_target_matrix, (num_examples, num_heights, num_vector_targets),
        order='F'
    )

    return {
        example_io.SCALAR_TARGET_VALS_KEY: scalar_target_matrix,
        example_io.VECTOR_TARGET_VALS_KEY: vector_target_matrix
    }


def make_cnn(option_dict, custom_loss_dict=None):
    """Makes CNN (convolutional neural net).

    This method only sets up the architecture, loss function, and optimizer,
    then compiles the model.  This method does *not* train the model.

    C = number of convolutional layers
    D = number of dense layers

    :param option_dict: Dictionary with the following keys.
    option_dict['num_heights']: Number of height levels.
    option_dict['num_input_channels']: Number of input channels.
    option_dict['conv_layer_channel_nums']: length-C numpy array with number of
        channels (filters) produced by each conv layer.  The last value in the
        array, conv_layer_channel_nums[-1], is the number of output channels
        (profiles to be predicted).
    option_dict['conv_layer_dropout_rates']: length-C numpy array with dropout
        rate for each conv layer.  Use NaN if you do not want dropout for a
        particular layer.
    option_dict['conv_layer_filter_sizes']: length-C numpy array with filter
        size (number of heights) for each conv layer.
    option_dict['dense_layer_neuron_nums']: length-D numpy array with number of
        neurons (features) produced by each dense layer.  The last value in the
        array, dense_layer_neuron_nums[-1], is the number of output scalars (to
        be predicted).
    option_dict['dense_layer_dropout_rates']: length-D numpy array with dropout
        rate for each dense layer.  Use NaN if you do not want dropout for a
        particular layer.
    option_dict['inner_activ_function_name']: Name of activation function for
        all inner (non-output) layers.  Must be accepted by
        `architecture_utils.check_activation_function`.
    option_dict['inner_activ_function_alpha']: Alpha (slope parameter) for
        activation function for all inner layers.  Applies only to ReLU and eLU.
    option_dict['output_activ_function_name']: Same as
        `inner_activ_function_name` but for output layers (profiles and
        scalars).
    option_dict['output_activ_function_alpha']: Same as
        `inner_activ_function_alpha` but for output layers (profiles and
        scalars).
    option_dict['l1_weight']: Weight for L_1 regularization.
    option_dict['l2_weight']: Weight for L_2 regularization.
    option_dict['use_batch_normalization']: Boolean flag.  If True, will use
        batch normalization after each inner (non-output) layer.

    :param custom_loss_dict: See doc for `_get_custom_loss_function`.  If you do
        not want a custom loss function, make this None.
    :return: model_object: Untrained instance of `keras.models.Model`.
    """

    # TODO(thunderhoser): Allow for no dense layers.

    option_dict = _check_architecture_args(option_dict=option_dict, is_cnn=True)

    use_custom_loss = custom_loss_dict is not None

    if use_custom_loss:
        dense_loss_function = _get_custom_loss_function(
            custom_loss_dict=custom_loss_dict, for_cnn=True
        )
    else:
        dense_loss_function = None

    num_heights = option_dict[NUM_HEIGHTS_KEY]
    num_input_channels = option_dict[NUM_INPUT_CHANNELS_KEY]
    conv_layer_channel_nums = option_dict[CONV_LAYER_CHANNEL_NUMS_KEY]
    conv_layer_dropout_rates = option_dict[CONV_LAYER_DROPOUT_RATES_KEY]
    conv_layer_filter_sizes = option_dict[CONV_LAYER_FILTER_SIZES_KEY]
    dense_layer_neuron_nums = option_dict[DENSE_LAYER_NEURON_NUMS_KEY]
    dense_layer_dropout_rates = option_dict[DENSE_LAYER_DROPOUT_RATES_KEY]
    inner_activ_function_name = option_dict[INNER_ACTIV_FUNCTION_KEY]
    inner_activ_function_alpha = option_dict[INNER_ACTIV_FUNCTION_ALPHA_KEY]
    output_activ_function_name = option_dict[OUTPUT_ACTIV_FUNCTION_KEY]
    output_activ_function_alpha = option_dict[OUTPUT_ACTIV_FUNCTION_ALPHA_KEY]
    l1_weight = option_dict[L1_WEIGHT_KEY]
    l2_weight = option_dict[L2_WEIGHT_KEY]
    use_batch_normalization = option_dict[USE_BATCH_NORM_KEY]

    input_layer_object = keras.layers.Input(
        shape=(num_heights, num_input_channels)
    )
    regularizer_object = architecture_utils.get_weight_regularizer(
        l1_weight=l1_weight, l2_weight=l2_weight
    )

    num_conv_layers = len(conv_layer_channel_nums)
    conv_output_layer_object = None
    dense_input_layer_object = None

    for i in range(num_conv_layers):
        if conv_output_layer_object is None:
            this_input_layer_object = input_layer_object
        else:
            this_input_layer_object = conv_output_layer_object

        if i == num_conv_layers - 1:
            dense_input_layer_object = conv_output_layer_object

        conv_output_layer_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=conv_layer_filter_sizes[i], num_rows_per_stride=1,
            num_filters=conv_layer_channel_nums[i],
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        if i == num_conv_layers - 1:
            conv_output_layer_object = architecture_utils.get_activation_layer(
                activation_function_string=output_activ_function_name,
                alpha_for_relu=output_activ_function_alpha,
                alpha_for_elu=output_activ_function_alpha,
                layer_name='conv_output'
            )(conv_output_layer_object)
        else:
            conv_output_layer_object = architecture_utils.get_activation_layer(
                activation_function_string=inner_activ_function_name,
                alpha_for_relu=inner_activ_function_alpha,
                alpha_for_elu=inner_activ_function_alpha
            )(conv_output_layer_object)

        if conv_layer_dropout_rates[i] > 0:
            conv_output_layer_object = architecture_utils.get_dropout_layer(
                dropout_fraction=conv_layer_dropout_rates[i]
            )(conv_output_layer_object)

        if use_batch_normalization and i != num_conv_layers - 1:
            conv_output_layer_object = (
                architecture_utils.get_batch_norm_layer()(
                    conv_output_layer_object
                )
            )

    num_dense_layers = len(dense_layer_neuron_nums)
    dense_output_layer_object = architecture_utils.get_flattening_layer()(
        dense_input_layer_object
    )

    for i in range(num_dense_layers):
        dense_output_layer_object = architecture_utils.get_dense_layer(
            num_output_units=dense_layer_neuron_nums[i]
        )(dense_output_layer_object)

        if i == num_dense_layers - 1:
            dense_output_layer_object = architecture_utils.get_activation_layer(
                activation_function_string=output_activ_function_name,
                alpha_for_relu=output_activ_function_alpha,
                alpha_for_elu=output_activ_function_alpha,
                layer_name=None if use_custom_loss else 'dense_output'
            )(dense_output_layer_object)
        else:
            dense_output_layer_object = architecture_utils.get_activation_layer(
                activation_function_string=inner_activ_function_name,
                alpha_for_relu=inner_activ_function_alpha,
                alpha_for_elu=inner_activ_function_alpha
            )(dense_output_layer_object)

        if dense_layer_dropout_rates[i] > 0:
            dense_output_layer_object = architecture_utils.get_dropout_layer(
                dropout_fraction=dense_layer_dropout_rates[i]
            )(dense_output_layer_object)

        if use_batch_normalization and i != num_dense_layers - 1:
            dense_output_layer_object = (
                architecture_utils.get_batch_norm_layer()(
                    dense_output_layer_object
                )
            )

    if use_custom_loss:
        k = custom_loss_dict[UP_FLUX_CHANNEL_INDEX_KEY] + 0

        highest_up_flux_layer_object = keras.layers.Lambda(
            lambda x: x[:, -1, k:(k + 1)]
        )(conv_output_layer_object)

        k = custom_loss_dict[DOWN_FLUX_CHANNEL_INDEX_KEY] + 0

        lowest_down_flux_layer_object = keras.layers.Lambda(
            lambda x: x[:, -0, k:(k + 1)]
        )(conv_output_layer_object)

        this_list = [
            highest_up_flux_layer_object, lowest_down_flux_layer_object,
            dense_output_layer_object
        ]

        dense_output_layer_object = keras.layers.Concatenate(
            axis=-1, name='dense_output'
        )(this_list)

    model_object = keras.models.Model(
        inputs=input_layer_object,
        outputs=[conv_output_layer_object, dense_output_layer_object]
    )

    if use_custom_loss:
        loss_dict = {
            'conv_output': keras.losses.mse,
            'dense_output': dense_loss_function
        }

        model_object.compile(
            loss=loss_dict, optimizer=keras.optimizers.Adam(),
            metrics=METRIC_FUNCTION_LIST
        )
    else:
        model_object.compile(
            loss=keras.losses.mse, optimizer=keras.optimizers.Adam(),
            metrics=METRIC_FUNCTION_LIST
        )

    model_object.summary()
    return model_object


def make_dense_net(option_dict, custom_loss_dict):
    """Makes dense (fully connected) neural net.

    :param option_dict: Dictionary with the following keys.
    option_dict['num_inputs']: Number of input variables (predictors).
    option_dict['dense_layer_neuron_nums']: See doc for `make_cnn`.
    option_dict['dense_layer_dropout_rates']: Same.
    option_dict['inner_activ_function_name']: Same.
    option_dict['inner_activ_function_alpha']: Same.
    option_dict['output_activ_function_name']: Same.
    option_dict['output_activ_function_alpha']: Same.
    option_dict['l1_weight']: Same.
    option_dict['l2_weight']: Same.
    option_dict['use_batch_normalization']: Same.

    :param custom_loss_dict: See doc for `_get_custom_loss_function`.  If you do
        not want a custom loss function, make this None.

    :return: model_object: See doc for `make_cnn`.
    """

    option_dict = _check_architecture_args(
        option_dict=option_dict, is_cnn=False
    )

    use_custom_loss = custom_loss_dict is not None

    if use_custom_loss:
        loss_function = _get_custom_loss_function(
            custom_loss_dict=custom_loss_dict, for_cnn=False
        )
    else:
        loss_function = keras.losses.mse

    num_inputs = option_dict[NUM_INPUTS_KEY]
    dense_layer_neuron_nums = option_dict[DENSE_LAYER_NEURON_NUMS_KEY]
    dense_layer_dropout_rates = option_dict[DENSE_LAYER_DROPOUT_RATES_KEY]
    inner_activ_function_name = option_dict[INNER_ACTIV_FUNCTION_KEY]
    inner_activ_function_alpha = option_dict[INNER_ACTIV_FUNCTION_ALPHA_KEY]
    output_activ_function_name = option_dict[OUTPUT_ACTIV_FUNCTION_KEY]
    output_activ_function_alpha = option_dict[OUTPUT_ACTIV_FUNCTION_ALPHA_KEY]
    l1_weight = option_dict[L1_WEIGHT_KEY]
    l2_weight = option_dict[L2_WEIGHT_KEY]
    use_batch_normalization = option_dict[USE_BATCH_NORM_KEY]

    input_layer_object = keras.layers.Input(shape=(num_inputs,))
    regularizer_object = architecture_utils.get_weight_regularizer(
        l1_weight=l1_weight, l2_weight=l2_weight
    )

    num_dense_layers = len(dense_layer_neuron_nums)
    layer_object = None

    for i in range(num_dense_layers):
        if layer_object is None:
            this_input_layer_object = input_layer_object
        else:
            this_input_layer_object = layer_object

        layer_object = architecture_utils.get_dense_layer(
            num_output_units=dense_layer_neuron_nums[i],
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        if i == num_dense_layers - 1:
            layer_object = architecture_utils.get_activation_layer(
                activation_function_string=output_activ_function_name,
                alpha_for_relu=output_activ_function_alpha,
                alpha_for_elu=output_activ_function_alpha
            )(layer_object)
        else:
            layer_object = architecture_utils.get_activation_layer(
                activation_function_string=inner_activ_function_name,
                alpha_for_relu=inner_activ_function_alpha,
                alpha_for_elu=inner_activ_function_alpha
            )(layer_object)

        if dense_layer_dropout_rates[i] > 0:
            layer_object = architecture_utils.get_dropout_layer(
                dropout_fraction=dense_layer_dropout_rates[i]
            )(layer_object)

        if use_batch_normalization and i != num_dense_layers - 1:
            layer_object = architecture_utils.get_batch_norm_layer()(
                layer_object
            )

    model_object = keras.models.Model(
        inputs=input_layer_object, outputs=layer_object
    )

    model_object.compile(
        loss=loss_function, optimizer=keras.optimizers.Adam(),
        metrics=METRIC_FUNCTION_LIST
    )

    model_object.summary()
    return model_object


def make_u_net(option_dict):
    """Makes U-net.

    :param option_dict: Dictionary with the following keys.
    option_dict['num_heights']: See doc for `make_cnn`.
    option_dict['num_input_channels']: Same.
    option_dict['inner_activ_function_name']: Same.
    option_dict['inner_activ_function_alpha']: Same.
    option_dict['output_activ_function_name']: Same.
    option_dict['output_activ_function_alpha']: Same.
    option_dict['l1_weight']: Same.
    option_dict['l2_weight']: Same.
    option_dict['use_batch_normalization']: Same.

    :return: model_object: Instance of `keras.models.Model`, with the
        aforementioned architecture.
    """

    # TODO(thunderhoser): Check input args.

    num_heights = option_dict[NUM_HEIGHTS_KEY]
    num_input_channels = option_dict[NUM_INPUT_CHANNELS_KEY]
    inner_activ_function_name = option_dict[INNER_ACTIV_FUNCTION_KEY]
    inner_activ_function_alpha = option_dict[INNER_ACTIV_FUNCTION_ALPHA_KEY]
    output_activ_function_name = option_dict[OUTPUT_ACTIV_FUNCTION_KEY]
    output_activ_function_alpha = option_dict[OUTPUT_ACTIV_FUNCTION_ALPHA_KEY]
    l1_weight = option_dict[L1_WEIGHT_KEY]
    l2_weight = option_dict[L2_WEIGHT_KEY]
    use_batch_normalization = option_dict[USE_BATCH_NORM_KEY]

    input_layer_object = keras.layers.Input(
        shape=(num_heights, num_input_channels)
    )
    regularizer_object = architecture_utils.get_weight_regularizer(
        l1_weight=l1_weight, l2_weight=l2_weight
    )

    conv_layer1_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = input_layer_object
        else:
            this_input_layer_object = conv_layer1_object

        conv_layer1_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=64,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        conv_layer1_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(conv_layer1_object)

        if use_batch_normalization:
            conv_layer1_object = architecture_utils.get_batch_norm_layer()(
                conv_layer1_object
            )

    pooling_layer1_object = architecture_utils.get_1d_pooling_layer(
        num_rows_in_window=2, num_rows_per_stride=2,
        pooling_type_string=architecture_utils.MAX_POOLING_STRING
    )(conv_layer1_object)

    conv_layer2_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = pooling_layer1_object
        else:
            this_input_layer_object = conv_layer2_object

        conv_layer2_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=128,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        conv_layer2_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(conv_layer2_object)

        if use_batch_normalization:
            conv_layer2_object = architecture_utils.get_batch_norm_layer()(
                conv_layer2_object
            )

    pooling_layer2_object = architecture_utils.get_1d_pooling_layer(
        num_rows_in_window=2, num_rows_per_stride=2,
        pooling_type_string=architecture_utils.MAX_POOLING_STRING
    )(conv_layer2_object)

    conv_layer3_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = pooling_layer2_object
        else:
            this_input_layer_object = conv_layer3_object

        conv_layer3_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=256,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        conv_layer3_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(conv_layer3_object)

        if use_batch_normalization:
            conv_layer3_object = architecture_utils.get_batch_norm_layer()(
                conv_layer3_object
            )

    pooling_layer3_object = architecture_utils.get_1d_pooling_layer(
        num_rows_in_window=2, num_rows_per_stride=2,
        pooling_type_string=architecture_utils.MAX_POOLING_STRING
    )(conv_layer3_object)

    conv_layer4_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = pooling_layer3_object
        else:
            this_input_layer_object = conv_layer4_object

        conv_layer4_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=512,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        conv_layer4_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(conv_layer4_object)

        conv_layer4_object = architecture_utils.get_dropout_layer(
            dropout_fraction=0.5
        )(conv_layer4_object)

        if use_batch_normalization:
            conv_layer4_object = architecture_utils.get_batch_norm_layer()(
                conv_layer4_object
            )

    pooling_layer4_object = architecture_utils.get_1d_pooling_layer(
        num_rows_in_window=2, num_rows_per_stride=2,
        pooling_type_string=architecture_utils.MAX_POOLING_STRING
    )(conv_layer4_object)

    conv_layer5_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = pooling_layer4_object
        else:
            this_input_layer_object = conv_layer5_object

        conv_layer5_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=1024,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        conv_layer5_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(conv_layer5_object)

        conv_layer5_object = architecture_utils.get_dropout_layer(
            dropout_fraction=0.5
        )(conv_layer5_object)

        if use_batch_normalization:
            conv_layer5_object = architecture_utils.get_batch_norm_layer()(
                conv_layer5_object
            )

    this_layer_object = keras.layers.UpSampling1D(size=(2,))

    upconv_layer4_object = architecture_utils.get_1d_conv_layer(
        num_kernel_rows=2, num_rows_per_stride=1, num_filters=512,
        padding_type_string=architecture_utils.YES_PADDING_STRING,
        weight_regularizer=regularizer_object
    )(this_layer_object)(conv_layer5_object)

    merged_layer4_object = keras.layers.merge(
        [conv_layer4_object, upconv_layer4_object],
        mode='concat', concat_axis=-1
    )

    second_conv_layer4_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = merged_layer4_object
        else:
            this_input_layer_object = second_conv_layer4_object

        second_conv_layer4_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=512,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        second_conv_layer4_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(second_conv_layer4_object)

        if use_batch_normalization:
            second_conv_layer4_object = (
                architecture_utils.get_batch_norm_layer()(
                    second_conv_layer4_object
                )
            )

    this_layer_object = keras.layers.UpSampling1D(size=(2,))

    upconv_layer3_object = architecture_utils.get_1d_conv_layer(
        num_kernel_rows=2, num_rows_per_stride=1, num_filters=256,
        padding_type_string=architecture_utils.YES_PADDING_STRING,
        weight_regularizer=regularizer_object
    )(this_layer_object)(second_conv_layer4_object)

    merged_layer3_object = keras.layers.merge(
        [conv_layer3_object, upconv_layer3_object],
        mode='concat', concat_axis=-1
    )

    second_conv_layer3_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = merged_layer3_object
        else:
            this_input_layer_object = second_conv_layer3_object

        second_conv_layer3_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=256,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        second_conv_layer3_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(second_conv_layer3_object)

        if use_batch_normalization:
            second_conv_layer3_object = (
                architecture_utils.get_batch_norm_layer()(
                    second_conv_layer3_object
                )
            )

    this_layer_object = keras.layers.UpSampling1D(size=(2,))

    upconv_layer2_object = architecture_utils.get_1d_conv_layer(
        num_kernel_rows=2, num_rows_per_stride=1, num_filters=128,
        padding_type_string=architecture_utils.YES_PADDING_STRING,
        weight_regularizer=regularizer_object
    )(this_layer_object)(second_conv_layer3_object)

    merged_layer2_object = keras.layers.merge(
        [conv_layer2_object, upconv_layer2_object],
        mode='concat', concat_axis=-1
    )

    second_conv_layer2_object = None

    for i in range(2):
        if i == 0:
            this_input_layer_object = merged_layer2_object
        else:
            this_input_layer_object = second_conv_layer2_object

        second_conv_layer2_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1, num_filters=128,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        second_conv_layer2_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(second_conv_layer2_object)

        if use_batch_normalization:
            second_conv_layer2_object = (
                architecture_utils.get_batch_norm_layer()(
                    second_conv_layer2_object
                )
            )

    this_layer_object = keras.layers.UpSampling1D(size=(2,))

    upconv_layer1_object = architecture_utils.get_1d_conv_layer(
        num_kernel_rows=2, num_rows_per_stride=1, num_filters=64,
        padding_type_string=architecture_utils.YES_PADDING_STRING,
        weight_regularizer=regularizer_object
    )(this_layer_object)(second_conv_layer2_object)

    merged_layer1_object = keras.layers.merge(
        [conv_layer1_object, upconv_layer1_object],
        mode='concat', concat_axis=-1
    )

    second_conv_layer1_object = None

    for i in range(3):
        if i == 0:
            this_input_layer_object = merged_layer1_object
        else:
            this_input_layer_object = second_conv_layer1_object

        second_conv_layer1_object = architecture_utils.get_1d_conv_layer(
            num_kernel_rows=3, num_rows_per_stride=1,
            num_filters=6 if i == 2 else 3,
            padding_type_string=architecture_utils.YES_PADDING_STRING,
            weight_regularizer=regularizer_object
        )(this_input_layer_object)

        second_conv_layer1_object = architecture_utils.get_activation_layer(
            activation_function_string=inner_activ_function_name,
            alpha_for_relu=inner_activ_function_alpha,
            alpha_for_elu=inner_activ_function_alpha
        )(second_conv_layer1_object)

        if use_batch_normalization:
            second_conv_layer1_object = (
                architecture_utils.get_batch_norm_layer()(
                    second_conv_layer1_object
                )
            )

    second_conv_layer1_object = architecture_utils.get_1d_conv_layer(
        num_kernel_rows=1, num_rows_per_stride=1, num_filters=3,
        padding_type_string=architecture_utils.YES_PADDING_STRING,
        weight_regularizer=regularizer_object
    )(second_conv_layer1_object)

    second_conv_layer1_object = architecture_utils.get_activation_layer(
        activation_function_string=output_activ_function_name,
        alpha_for_relu=output_activ_function_alpha,
        alpha_for_elu=output_activ_function_alpha
    )(second_conv_layer1_object)

    model_object = keras.models.Model(
        input=input_layer_object, output=second_conv_layer1_object
    )

    model_object.compile(
        loss=keras.losses.mse, optimizer=keras.optimizers.Adam(),
        metrics=METRIC_FUNCTION_LIST
    )

    model_object.summary()
    return model_object


def cnn_generator(option_dict, for_inference, use_custom_loss):
    """Generates examples for CNN.

    E = number of examples per batch (batch size)
    H = number of heights
    P = number of predictor variables (channels)
    T_v = number of vector target variables (channels)
    T_s = number of scalar target variables

    :param option_dict: Dictionary with the following keys.
    option_dict['example_dir_name']: Name of directory with example files.
        Files therein will be found by `example_io.find_file` and read by
        `example_io.read_file`.
    option_dict['num_examples_per_batch']: Batch size.
    option_dict['predictor_names']: 1-D list with names of predictor variables
        (valid names listed in example_io.py).
    option_dict['target_names']: Same but for target variables.
    option_dict['first_time_unix_sec']: Start time (will not generate examples
        before this time).
    option_dict['last_time_unix_sec']: End time (will not generate examples after
        this time).
    option_dict['normalization_file_name']: File with training examples to use
        for normalization (will be read by `example_io.read_file`).
    option_dict['predictor_norm_type_string']: Normalization type for predictors
        (must be accepted by `normalization._check_normalization_type`).
    option_dict['predictor_min_norm_value']: Minimum normalized value for
        predictors (used only if normalization type is min-max).
    option_dict['predictor_max_norm_value']: Same but max value.
    option_dict['target_norm_type_string']: Normalization type for targets (must
        be accepted by `normalization._check_normalization_type`).
    option_dict['target_min_norm_value']: Minimum normalized value for targets
        (used only if normalization type is min-max).
    option_dict['target_max_norm_value']: Same but max value.

    :param for_inference: Boolean flag.  If True, generator is being used for
        inference stage (applying trained model to new data).  If False,
        generator is being used for training or monitoring (on-the-fly
        validation).
    :param use_custom_loss: Boolean flag.  If True, using custom loss function.

    If `for_inference == False`, this method does not return
    `example_id_strings`.

    :return: predictor_matrix: E-by-H-by-P numpy array of predictor values.
    :return: target_list: List with 2 items.
    target_list[0] = vector_target_matrix: numpy array (E x H x T_v) of target
        values.
    target_list[1] = scalar_target_matrix: numpy array (E x T_s) of target
        values.

    :return: example_id_strings: length-E list of example IDs created by
        `example_io.create_example_ids`.
    """

    option_dict = _check_generator_args(option_dict)
    error_checking.assert_is_boolean(for_inference)
    error_checking.assert_is_boolean(use_custom_loss)

    example_dir_name = option_dict[EXAMPLE_DIRECTORY_KEY]
    num_examples_per_batch = option_dict[BATCH_SIZE_KEY]
    scalar_predictor_names = option_dict[SCALAR_PREDICTOR_NAMES_KEY]
    vector_predictor_names = option_dict[VECTOR_PREDICTOR_NAMES_KEY]
    scalar_target_names = option_dict[SCALAR_TARGET_NAMES_KEY]
    vector_target_names = option_dict[VECTOR_TARGET_NAMES_KEY]
    heights_m_agl = option_dict[HEIGHTS_KEY]
    first_time_unix_sec = option_dict[FIRST_TIME_KEY]
    last_time_unix_sec = option_dict[LAST_TIME_KEY]

    all_field_names = (
        scalar_predictor_names + vector_predictor_names +
        scalar_target_names + vector_target_names
    )

    normalization_file_name = option_dict[NORMALIZATION_FILE_KEY]
    predictor_norm_type_string = option_dict[PREDICTOR_NORM_TYPE_KEY]
    predictor_min_norm_value = option_dict[PREDICTOR_MIN_NORM_VALUE_KEY]
    predictor_max_norm_value = option_dict[PREDICTOR_MAX_NORM_VALUE_KEY]
    target_norm_type_string = option_dict[TARGET_NORM_TYPE_KEY]
    target_min_norm_value = option_dict[TARGET_MIN_NORM_VALUE_KEY]
    target_max_norm_value = option_dict[TARGET_MAX_NORM_VALUE_KEY]

    print((
        'Reading training examples (for normalization) from: "{0:s}"...'
    ).format(
        normalization_file_name
    ))

    training_example_dict = example_io.read_file(normalization_file_name)

    example_file_names = example_io.find_many_files(
        example_dir_name=example_dir_name,
        first_time_unix_sec=first_time_unix_sec,
        last_time_unix_sec=last_time_unix_sec,
        raise_error_if_any_missing=False
    )

    file_index = 0

    if for_inference:
        example_index = 0
    else:
        example_index = None

    while True:
        if for_inference and file_index >= len(example_file_names):
            raise StopIteration

        num_examples_in_memory = 0
        predictor_matrix = None
        vector_target_matrix = None
        scalar_target_matrix = None
        example_id_strings = []

        while num_examples_in_memory < num_examples_per_batch:
            if file_index == len(example_file_names):
                if for_inference:
                    if predictor_matrix is None:
                        raise StopIteration

                    break

                file_index = 0

            this_example_dict, these_id_strings = _read_file_for_generator(
                example_file_name=example_file_names[file_index],
                num_examples_to_keep=
                num_examples_per_batch - num_examples_in_memory,
                for_inference=for_inference,
                first_time_unix_sec=first_time_unix_sec,
                last_time_unix_sec=last_time_unix_sec,
                field_names=all_field_names, heights_m_agl=heights_m_agl,
                training_example_dict=training_example_dict,
                predictor_norm_type_string=predictor_norm_type_string,
                predictor_min_norm_value=predictor_min_norm_value,
                predictor_max_norm_value=predictor_max_norm_value,
                target_norm_type_string=target_norm_type_string,
                target_min_norm_value=target_min_norm_value,
                target_max_norm_value=target_max_norm_value,
                first_example_to_keep=example_index
            )

            if for_inference:
                this_num_examples = len(
                    this_example_dict[example_io.VALID_TIMES_KEY]
                )

                if this_num_examples == 0:
                    file_index += 1
                    example_index = 0
                else:
                    example_index += this_num_examples

                example_id_strings += these_id_strings
            else:
                file_index += 1

            this_predictor_matrix = predictors_dict_to_numpy(
                example_dict=this_example_dict, for_cnn=True
            )
            this_list = targets_dict_to_numpy(
                example_dict=this_example_dict, for_cnn=True,
                use_custom_cnn_loss=use_custom_loss
            )
            this_vector_target_matrix = this_list[0]
            this_scalar_target_matrix = this_list[1]

            if predictor_matrix is None:
                predictor_matrix = this_predictor_matrix + 0.
                vector_target_matrix = this_vector_target_matrix + 0.
                scalar_target_matrix = this_scalar_target_matrix + 0.
            else:
                predictor_matrix = numpy.concatenate(
                    (predictor_matrix, this_predictor_matrix), axis=0
                )
                vector_target_matrix = numpy.concatenate(
                    (vector_target_matrix, this_vector_target_matrix), axis=0
                )
                scalar_target_matrix = numpy.concatenate(
                    (scalar_target_matrix, this_scalar_target_matrix), axis=0
                )

            num_examples_in_memory = predictor_matrix.shape[0]

        predictor_matrix = predictor_matrix.astype('float32')
        vector_target_matrix = vector_target_matrix.astype('float32')
        scalar_target_matrix = scalar_target_matrix.astype('float32')

        if for_inference:
            yield (
                predictor_matrix,
                [vector_target_matrix, scalar_target_matrix],
                example_id_strings
            )
        else:
            yield (
                predictor_matrix,
                [vector_target_matrix, scalar_target_matrix]
            )


def dense_net_generator(option_dict, for_inference):
    """Generates examples for dense neural net.

    E = number of examples per batch (batch size)
    P = number of predictor variables
    T = number of target variables

    :param option_dict: See doc for `cnn_generator`.
    :param for_inference: Boolean flag.  If True, generator is being used for
        inference stage (applying trained model to new data).  If False,
        generator is being used for training or monitoring (on-the-fly
        validation).

    If `for_inference == False`, this method does not return
    `example_id_strings`.

    :return: predictor_matrix: E-by-P numpy array of predictor values.
    :return: target_matrix: E-by-T numpy array of target values.
    :return: example_id_strings: length-E list of example IDs created by
        `example_io.create_example_ids`.
    """

    option_dict = _check_generator_args(option_dict)
    error_checking.assert_is_boolean(for_inference)

    example_dir_name = option_dict[EXAMPLE_DIRECTORY_KEY]
    num_examples_per_batch = option_dict[BATCH_SIZE_KEY]
    scalar_predictor_names = option_dict[SCALAR_PREDICTOR_NAMES_KEY]
    vector_predictor_names = option_dict[VECTOR_PREDICTOR_NAMES_KEY]
    scalar_target_names = option_dict[SCALAR_TARGET_NAMES_KEY]
    vector_target_names = option_dict[VECTOR_TARGET_NAMES_KEY]
    heights_m_agl = option_dict[HEIGHTS_KEY]
    first_time_unix_sec = option_dict[FIRST_TIME_KEY]
    last_time_unix_sec = option_dict[LAST_TIME_KEY]

    all_field_names = (
        scalar_predictor_names + vector_predictor_names +
        scalar_target_names + vector_target_names
    )

    normalization_file_name = option_dict[NORMALIZATION_FILE_KEY]
    predictor_norm_type_string = option_dict[PREDICTOR_NORM_TYPE_KEY]
    predictor_min_norm_value = option_dict[PREDICTOR_MIN_NORM_VALUE_KEY]
    predictor_max_norm_value = option_dict[PREDICTOR_MAX_NORM_VALUE_KEY]
    target_norm_type_string = option_dict[TARGET_NORM_TYPE_KEY]
    target_min_norm_value = option_dict[TARGET_MIN_NORM_VALUE_KEY]
    target_max_norm_value = option_dict[TARGET_MAX_NORM_VALUE_KEY]

    print((
        'Reading training examples (for normalization) from: "{0:s}"...'
    ).format(
        normalization_file_name
    ))

    training_example_dict = example_io.read_file(normalization_file_name)

    example_file_names = example_io.find_many_files(
        example_dir_name=example_dir_name,
        first_time_unix_sec=first_time_unix_sec,
        last_time_unix_sec=last_time_unix_sec,
        raise_error_if_any_missing=False
    )

    file_index = 0

    if for_inference:
        example_index = 0
    else:
        example_index = None

    while True:
        if for_inference and file_index >= len(example_file_names):
            raise StopIteration

        num_examples_in_memory = 0
        predictor_matrix = None
        target_matrix = None
        example_id_strings = []

        while num_examples_in_memory < num_examples_per_batch:
            if file_index == len(example_file_names):
                if for_inference:
                    if predictor_matrix is None:
                        raise StopIteration

                    break

                file_index = 0

            this_example_dict, these_id_strings = _read_file_for_generator(
                example_file_name=example_file_names[file_index],
                num_examples_to_keep=
                num_examples_per_batch - num_examples_in_memory,
                for_inference=for_inference,
                first_time_unix_sec=first_time_unix_sec,
                last_time_unix_sec=last_time_unix_sec,
                field_names=all_field_names, heights_m_agl=heights_m_agl,
                training_example_dict=training_example_dict,
                predictor_norm_type_string=predictor_norm_type_string,
                predictor_min_norm_value=predictor_min_norm_value,
                predictor_max_norm_value=predictor_max_norm_value,
                target_norm_type_string=target_norm_type_string,
                target_min_norm_value=target_min_norm_value,
                target_max_norm_value=target_max_norm_value,
                first_example_to_keep=example_index
            )

            if for_inference:
                this_num_examples = len(
                    this_example_dict[example_io.VALID_TIMES_KEY]
                )

                if this_num_examples == 0:
                    file_index += 1
                    example_index = 0
                else:
                    example_index += this_num_examples

                example_id_strings += these_id_strings
            else:
                file_index += 1

            this_predictor_matrix = predictors_dict_to_numpy(
                example_dict=this_example_dict, for_cnn=False
            )
            this_target_matrix = targets_dict_to_numpy(
                example_dict=this_example_dict, for_cnn=False,
                use_custom_cnn_loss=False
            )[0]

            if predictor_matrix is None:
                predictor_matrix = this_predictor_matrix + 0.
                target_matrix = this_target_matrix + 0.
            else:
                predictor_matrix = numpy.concatenate(
                    (predictor_matrix, this_predictor_matrix), axis=0
                )
                target_matrix = numpy.concatenate(
                    (target_matrix, this_target_matrix), axis=0
                )

            num_examples_in_memory = predictor_matrix.shape[0]

        if for_inference:
            yield (
                predictor_matrix.astype('float32'),
                target_matrix.astype('float32'),
                example_id_strings
            )
        else:
            yield (
                predictor_matrix.astype('float32'),
                target_matrix.astype('float32')
            )


def train_neural_net(
        model_object, output_dir_name, num_epochs,
        num_training_batches_per_epoch, training_option_dict,
        num_validation_batches_per_epoch, validation_option_dict, is_cnn,
        custom_loss_dict):
    """Trains neural net (either CNN or dense net).

    :param model_object: Untrained neural net (instance of `keras.models.Model`
        or `keras.models.Sequential`).
    :param output_dir_name: Path to output directory (model and training history
        will be saved here).
    :param num_epochs: Number of training epochs.
    :param num_training_batches_per_epoch: Number of training batches per epoch.
    :param training_option_dict: See doc for `cnn_generator` or
        `dense_net_generator`.  This dictionary will be used for training
        options.
    :param num_validation_batches_per_epoch: Number of validation batches per
        epoch.
    :param validation_option_dict: See doc for `cnn_generator` or
        `dense_net_generator`.  For validation only, the following values will
        replace corresponding values in `training_option_dict`:
    validation_option_dict['example_dir_name']
    validation_option_dict['num_examples_per_batch']
    validation_option_dict['first_time_unix_sec']
    validation_option_dict['last_time_unix_sec']

    :param is_cnn: Boolean flag.  If True, will assume that `model_object` is a
        CNN.  If False, will assume that it is a dense net.
    :param custom_loss_dict: See doc for `_get_custom_loss_function`.  If the
        neural net does not have a custom loss function, make this None.
    """

    file_system_utils.mkdir_recursive_if_necessary(
        directory_name=output_dir_name
    )
    error_checking.assert_is_integer(num_epochs)
    # error_checking.assert_is_geq(num_epochs, 10)
    error_checking.assert_is_geq(num_epochs, 2)
    error_checking.assert_is_integer(num_training_batches_per_epoch)
    error_checking.assert_is_geq(num_training_batches_per_epoch, 10)
    error_checking.assert_is_integer(num_validation_batches_per_epoch)
    error_checking.assert_is_geq(num_validation_batches_per_epoch, 10)
    error_checking.assert_is_boolean(is_cnn)

    training_option_dict = _check_generator_args(training_option_dict)

    validation_keys_to_keep = [
        EXAMPLE_DIRECTORY_KEY, BATCH_SIZE_KEY, FIRST_TIME_KEY, LAST_TIME_KEY
    ]

    for this_key in list(training_option_dict.keys()):
        if this_key in validation_keys_to_keep:
            continue

        validation_option_dict[this_key] = training_option_dict[this_key]

    validation_option_dict = _check_generator_args(validation_option_dict)

    history_object = keras.callbacks.CSVLogger(
        filename='{0:s}/history.csv'.format(output_dir_name),
        separator=',', append=False
    )

    checkpoint_object = keras.callbacks.ModelCheckpoint(
        filepath='{0:s}/model.h5'.format(output_dir_name),
        monitor='val_loss', verbose=1, save_best_only=True,
        save_weights_only=False, mode='min', period=1
    )

    early_stopping_object = keras.callbacks.EarlyStopping(
        monitor='val_loss', min_delta=LOSS_PATIENCE,
        patience=EARLY_STOPPING_PATIENCE_EPOCHS, verbose=1, mode='min'
    )

    plateau_object = keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=PLATEAU_LEARNING_RATE_MULTIPLIER,
        patience=PLATEAU_PATIENCE_EPOCHS, verbose=1, mode='min',
        min_delta=LOSS_PATIENCE, cooldown=PLATEAU_COOLDOWN_EPOCHS
    )

    list_of_callback_objects = [
        history_object, checkpoint_object, early_stopping_object, plateau_object
    ]

    metafile_name = find_metafile(output_dir_name, raise_error_if_missing=False)
    print('Writing metadata to: "{0:s}"...'.format(metafile_name))

    _write_metadata(
        pickle_file_name=metafile_name, num_epochs=num_epochs,
        num_training_batches_per_epoch=num_training_batches_per_epoch,
        training_option_dict=training_option_dict,
        num_validation_batches_per_epoch=num_validation_batches_per_epoch,
        validation_option_dict=validation_option_dict, is_cnn=is_cnn,
        custom_loss_dict=custom_loss_dict
    )

    if is_cnn:
        training_generator = cnn_generator(
            option_dict=training_option_dict, for_inference=False,
            use_custom_loss=custom_loss_dict is not None
        )
        validation_generator = cnn_generator(
            option_dict=validation_option_dict, for_inference=False,
            use_custom_loss=custom_loss_dict is not None
        )
    else:
        training_generator = dense_net_generator(
            option_dict=training_option_dict, for_inference=False
        )
        validation_generator = dense_net_generator(
            option_dict=validation_option_dict, for_inference=False
        )

    model_object.fit_generator(
        generator=training_generator,
        steps_per_epoch=num_training_batches_per_epoch, epochs=num_epochs,
        verbose=1, callbacks=list_of_callback_objects,
        validation_data=validation_generator,
        validation_steps=num_validation_batches_per_epoch
    )


def apply_cnn(
        model_object, predictor_matrix, num_examples_per_batch,
        used_custom_loss, verbose=False):
    """Applies trained CNN to data.

    E = number of examples per batch (batch size)
    H = number of heights
    T_v = number of vector target variables (channels)
    T_s = number of scalar target variables

    :param model_object: Trained CNN (instance of `keras.models.Model` or
        `keras.models.Sequential`).
    :param predictor_matrix: See output doc for `cnn_generator`.
    :param num_examples_per_batch: Batch size.
    :param used_custom_loss: Boolean flag.  If True, custom loss function was
        used in training.
    :param verbose: Boolean flag.  If True, will print progress messages.
    :return: vector_prediction_matrix: numpy array (E x H x T_v) of predicted
        values.
    :return: scalar_prediction_matrix: numpy array (E x T_s) of predicted
        values.
    """

    error_checking.assert_is_boolean(used_custom_loss)

    num_examples_per_batch = _check_inference_args(
        predictor_matrix=predictor_matrix,
        num_examples_per_batch=num_examples_per_batch, verbose=verbose
    )

    num_examples = predictor_matrix.shape[0]
    vector_prediction_matrix = None
    scalar_prediction_matrix = None

    for i in range(0, num_examples, num_examples_per_batch):
        this_first_index = i
        this_last_index = min(
            [i + num_examples_per_batch - 1, num_examples - 1]
        )

        these_indices = numpy.linspace(
            this_first_index, this_last_index,
            num=this_last_index - this_first_index + 1, dtype=int
        )

        if verbose:
            print('Applying CNN to examples {0:d}-{1:d} of {2:d}...'.format(
                this_first_index + 1, this_last_index + 1, num_examples
            ))

        these_outputs = model_object.predict(
            predictor_matrix[these_indices, ...], batch_size=len(these_indices)
        )

        if vector_prediction_matrix is None:
            vector_prediction_matrix = these_outputs[0] + 0.
            scalar_prediction_matrix = these_outputs[1] + 0.
        else:
            vector_prediction_matrix = numpy.concatenate(
                (vector_prediction_matrix, these_outputs[0]), axis=0
            )
            scalar_prediction_matrix = numpy.concatenate(
                (scalar_prediction_matrix, these_outputs[1]), axis=0
            )

    if verbose:
        print('Have applied CNN to all {0:d} examples!'.format(num_examples))

    if used_custom_loss:
        scalar_prediction_matrix = scalar_prediction_matrix[:, 2:]

    return vector_prediction_matrix, scalar_prediction_matrix


def apply_dense_net(
        model_object, predictor_matrix, num_examples_per_batch, verbose=False):
    """Applies dense net to data.

    E = number of examples per batch (batch size)
    T = number of target variables

    :param model_object: Trained dense net (instance of `keras.models.Model` or
        `keras.models.Sequential`).
    :param predictor_matrix: See output doc for `dense_net_generator`.
    :param num_examples_per_batch: Batch size.
    :param verbose: Boolean flag.  If True, will print progress messages.
    :return: prediction_matrix: E-by-T numpy array of predicted values.
    """

    num_examples_per_batch = _check_inference_args(
        predictor_matrix=predictor_matrix,
        num_examples_per_batch=num_examples_per_batch, verbose=verbose
    )

    num_examples = predictor_matrix.shape[0]
    prediction_matrix = None

    for i in range(0, num_examples, num_examples_per_batch):
        this_first_index = i
        this_last_index = min(
            [i + num_examples_per_batch - 1, num_examples - 1]
        )

        these_indices = numpy.linspace(
            this_first_index, this_last_index,
            num=this_last_index - this_first_index + 1, dtype=int
        )

        if verbose:
            print((
                'Applying dense net to examples {0:d}-{1:d} of {2:d}...'
            ).format(
                this_first_index + 1, this_last_index + 1, num_examples
            ))

        this_prediction_matrix = model_object.predict(
            predictor_matrix[these_indices, ...], batch_size=len(these_indices)
        )

        if prediction_matrix is None:
            prediction_matrix = this_prediction_matrix + 0.
        else:
            prediction_matrix = numpy.concatenate(
                (prediction_matrix, this_prediction_matrix), axis=0
            )

    if verbose:
        print('Have applied dense net to all {0:d} examples!'.format(
            num_examples
        ))

    return prediction_matrix


def read_model(hdf5_file_name):
    """Reads model from HDF5 file.

    :param hdf5_file_name: Path to input file.
    :return: model_object: Instance of `keras.models.Model` or
        `keras.models.Sequential`.
    """

    error_checking.assert_file_exists(hdf5_file_name)

    try:
        return keras.models.load_model(
            hdf5_file_name, custom_objects=METRIC_FUNCTION_DICT
        )
    except ValueError:
        pass

    metafile_name = find_metafile(
        model_dir_name=os.path.split(hdf5_file_name)[0],
        raise_error_if_missing=True
    )

    metadata_dict = read_metadata(metafile_name)
    dense_loss_function = _get_custom_loss_function(
        custom_loss_dict=metadata_dict[CUSTOM_LOSS_KEY],
        for_cnn=metadata_dict[IS_CNN_KEY]
    )

    this_dict = copy.deepcopy(METRIC_FUNCTION_DICT)
    this_dict['loss'] = dense_loss_function

    return keras.models.load_model(hdf5_file_name, custom_objects=this_dict)


def find_metafile(model_dir_name, raise_error_if_missing=True):
    """Finds metafile for neural net.

    :param model_dir_name: Name of model directory.
    :param raise_error_if_missing: Boolean flag.  If file is missing and
        `raise_error_if_missing == True`, will throw error.  If file is missing
        and `raise_error_if_missing == False`, will return *expected* file path.
    :return: metafile_name: Path to metafile.
    """

    error_checking.assert_is_string(model_dir_name)
    error_checking.assert_is_boolean(raise_error_if_missing)

    metafile_name = '{0:s}/model_metadata.p'.format(model_dir_name)

    if raise_error_if_missing and not os.path.isfile(metafile_name):
        error_string = 'Cannot find file.  Expected at: "{0:s}"'.format(
            metafile_name
        )
        raise ValueError(error_string)

    return metafile_name


def read_metadata(pickle_file_name):
    """Reads metadata for neural net from Pickle file.

    :param pickle_file_name: Path to input file.
    :return: metadata_dict: Dictionary with the following keys.
    metadata_dict['num_epochs']: See doc for `train_neural_net`.
    metadata_dict['num_training_batches_per_epoch']: Same.
    metadata_dict['training_option_dict']: Same.
    metadata_dict['num_validation_batches_per_epoch']: Same.
    metadata_dict['validation_option_dict']: Same.
    metadata_dict['is_cnn']: Same.
    """

    error_checking.assert_file_exists(pickle_file_name)

    pickle_file_handle = open(pickle_file_name, 'rb')
    metadata_dict = pickle.load(pickle_file_handle)
    pickle_file_handle.close()

    if CUSTOM_LOSS_KEY not in metadata_dict:
        metadata_dict[CUSTOM_LOSS_KEY] = None

    missing_keys = list(set(METADATA_KEYS) - set(metadata_dict.keys()))
    if len(missing_keys) == 0:
        return metadata_dict

    error_string = (
        '\n{0:s}\nKeys listed above were expected, but not found, in file '
        '"{1:s}".'
    ).format(str(missing_keys), pickle_file_name)

    raise ValueError(error_string)
