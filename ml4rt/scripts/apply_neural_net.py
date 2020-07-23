"""Applies trained neural net in inference mode."""

import copy
import os.path
import argparse
import numpy
from gewittergefahr.gg_utils import time_conversion
from ml4rt.io import example_io
from ml4rt.io import prediction_io
from ml4rt.utils import normalization
from ml4rt.machine_learning import neural_net

# TODO(thunderhoser): Modularize the gross code in this script.

SEPARATOR_STRING = '\n\n' + '*' * 50 + '\n\n'

TIME_FORMAT = '%Y-%m-%d-%H%M%S'
NUM_EXAMPLES_PER_BATCH = 5000
TARGET_VALUE_KEYS = [
    example_io.SCALAR_TARGET_VALS_KEY, example_io.VECTOR_TARGET_VALS_KEY
]

MODEL_FILE_ARG_NAME = 'input_model_file_name'
EXAMPLE_DIR_ARG_NAME = 'input_example_dir_name'
FIRST_TIME_ARG_NAME = 'first_time_string'
LAST_TIME_ARG_NAME = 'last_time_string'
OUTPUT_FILE_ARG_NAME = 'output_file_name'

MODEL_FILE_HELP_STRING = (
    'Path to trained model.  Will be read by `neural_net.read_model`.'
)
EXAMPLE_DIR_HELP_STRING = (
    'Name of directory with data examples.  Files therein will be found by '
    '`example_io.find_file` and read by `example_io.read_file`.'
)
TIME_HELP_STRING = (
    'Time (format "yyyy-mm-dd-HHMMSS").  The neural net will be applied only to'
    ' examples from `{0:s}` to `{1:s}`.'
).format(FIRST_TIME_ARG_NAME, LAST_TIME_ARG_NAME)

OUTPUT_FILE_HELP_STRING = (
    'Path to output file (will be written by `prediction_io.write_file`).'
)

INPUT_ARG_PARSER = argparse.ArgumentParser()
INPUT_ARG_PARSER.add_argument(
    '--' + MODEL_FILE_ARG_NAME, type=str, required=True,
    help=MODEL_FILE_HELP_STRING
)
INPUT_ARG_PARSER.add_argument(
    '--' + EXAMPLE_DIR_ARG_NAME, type=str, required=True,
    help=EXAMPLE_DIR_HELP_STRING
)
INPUT_ARG_PARSER.add_argument(
    '--' + FIRST_TIME_ARG_NAME, type=str, required=True, help=TIME_HELP_STRING
)
INPUT_ARG_PARSER.add_argument(
    '--' + LAST_TIME_ARG_NAME, type=str, required=True, help=TIME_HELP_STRING
)
INPUT_ARG_PARSER.add_argument(
    '--' + OUTPUT_FILE_ARG_NAME, type=str, required=True,
    help=OUTPUT_FILE_HELP_STRING
)


def _get_unnormalized_pressure(model_metadata_dict, example_id_strings):
    """Returns profiles of unnormalized pressure.

    E = number of examples
    H = number of heights

    :param model_metadata_dict: Dictionary read by `neural_net.read_metafile`.
    :param example_id_strings: length-E list of example IDs.
    :return: pressure_matrix_pascals: E-by-H numpy array of pressures.
    """

    generator_option_dict = copy.deepcopy(
        model_metadata_dict[neural_net.TRAINING_OPTIONS_KEY]
    )

    generator_option_dict[neural_net.SCALAR_PREDICTOR_NAMES_KEY] = [
        example_io.LATITUDE_NAME, example_io.LONGITUDE_NAME,
        example_io.ZENITH_ANGLE_NAME
    ]
    generator_option_dict[neural_net.VECTOR_PREDICTOR_NAMES_KEY] = [
        example_io.PRESSURE_NAME
    ]
    generator_option_dict[neural_net.PREDICTOR_NORM_TYPE_KEY] = None
    generator_option_dict[neural_net.BATCH_SIZE_KEY] = NUM_EXAMPLES_PER_BATCH

    generator = neural_net.data_generator_specific_examples(
        option_dict=generator_option_dict,
        net_type_string=model_metadata_dict[neural_net.NET_TYPE_KEY],
        example_id_strings=example_id_strings
    )

    dummy_example_dict = {
        example_io.SCALAR_PREDICTOR_NAMES_KEY:
            generator_option_dict[neural_net.SCALAR_PREDICTOR_NAMES_KEY],
        example_io.VECTOR_PREDICTOR_NAMES_KEY:
            generator_option_dict[neural_net.VECTOR_PREDICTOR_NAMES_KEY],
        example_io.HEIGHTS_KEY: generator_option_dict[neural_net.HEIGHTS_KEY]
    }

    pressure_matrix_pascals = None

    while True:
        try:
            this_predictor_matrix = next(generator)[0]
        except (RuntimeError, StopIteration):
            break

        this_example_dict = neural_net.predictors_numpy_to_dict(
            predictor_matrix=this_predictor_matrix,
            example_dict=dummy_example_dict,
            net_type_string=model_metadata_dict[neural_net.NET_TYPE_KEY]
        )
        this_pressure_matrix_pascals = (
            this_example_dict[example_io.VECTOR_PREDICTOR_VALS_KEY][..., 0]
        )

        if pressure_matrix_pascals is None:
            pressure_matrix_pascals = this_pressure_matrix_pascals + 0.
        else:
            pressure_matrix_pascals = numpy.concatenate(
                (pressure_matrix_pascals, this_pressure_matrix_pascals), axis=0
            )

    return pressure_matrix_pascals


def _get_predicted_heating_rates(
        prediction_example_dict, pressure_matrix_pascals, model_metadata_dict):
    """Computes predicted heating rates from predicted flux-increment profiles.

    :param prediction_example_dict: Dictionary with predictions.  For a list of
        keys, see doc for `example_io.read_file`.
    :param pressure_matrix_pascals: See doc for `_get_unnormalized_pressure`.
    :param model_metadata_dict: Same.
    :return: prediction_example_dict: Same but with heating rates.
    """

    num_examples = pressure_matrix_pascals.shape[0]
    generator_option_dict = copy.deepcopy(
        model_metadata_dict[neural_net.TRAINING_OPTIONS_KEY]
    )

    this_dict = {
        example_io.VECTOR_PREDICTOR_NAMES_KEY: [example_io.PRESSURE_NAME],
        example_io.VECTOR_PREDICTOR_VALS_KEY:
            numpy.expand_dims(pressure_matrix_pascals, axis=-1),
        example_io.SCALAR_PREDICTOR_NAMES_KEY: [],
        example_io.SCALAR_PREDICTOR_VALS_KEY: numpy.full((num_examples, 0), 0.),
        example_io.VALID_TIMES_KEY: numpy.full(num_examples, 0, dtype=int)
    }
    prediction_example_dict.update(this_dict)

    prediction_example_dict = (
        example_io.fluxes_increments_to_actual(prediction_example_dict)
    )
    down_flux_inc_matrix_w_m02_pa01 = example_io.get_field_from_dict(
        example_dict=prediction_example_dict,
        field_name=example_io.SHORTWAVE_DOWN_FLUX_INC_NAME
    )
    down_flux_matrix_w_m02 = example_io.get_field_from_dict(
        example_dict=prediction_example_dict,
        field_name=example_io.SHORTWAVE_DOWN_FLUX_NAME
    )

    print(down_flux_inc_matrix_w_m02_pa01[0, ...])
    print(down_flux_matrix_w_m02[0, ...])
    print(pressure_matrix_pascals[0, ...])

    prediction_example_dict = example_io.fluxes_to_heating_rate(
        prediction_example_dict
    )

    target_names = (
        generator_option_dict[neural_net.VECTOR_TARGET_NAMES_KEY] +
        generator_option_dict[neural_net.SCALAR_TARGET_NAMES_KEY]
    )
    return example_io.subset_by_field(
        example_dict=prediction_example_dict, field_names=target_names
    )


def _targets_numpy_to_dict(
        scalar_target_matrix, vector_target_matrix, model_metadata_dict):
    """Converts either actual or predicted target values to dictionary.

    This method is a wrapper for `neural_net.targets_numpy_to_dict`.

    :param scalar_target_matrix: numpy array with scalar outputs (either
        predicted or actual target values).
    :param vector_target_matrix: Same but with vector outputs.
    :param model_metadata_dict: Dictionary read by `neural_net.read_metafile`.
    :return: example_dict: Equivalent dictionary, with keys listed in doc for
        `example_io.read_file`.
    """

    net_type_string = model_metadata_dict[neural_net.NET_TYPE_KEY]
    generator_option_dict = copy.deepcopy(
        model_metadata_dict[neural_net.TRAINING_OPTIONS_KEY]
    )
    add_heating_rate = generator_option_dict[neural_net.OMIT_HEATING_RATE_KEY]

    if add_heating_rate and net_type_string in [
            neural_net.CNN_TYPE_STRING, neural_net.U_NET_TYPE_STRING
    ]:
        vector_target_names = (
            generator_option_dict[neural_net.VECTOR_TARGET_NAMES_KEY]
        )

        if vector_target_matrix.shape[-1] == len(vector_target_names) - 1:
            heating_rate_index = vector_target_names.index(
                example_io.SHORTWAVE_HEATING_RATE_NAME
            )
            vector_target_matrix = numpy.insert(
                vector_target_matrix, obj=heating_rate_index, values=0., axis=-1
            )

    if net_type_string == neural_net.CNN_TYPE_STRING:
        target_matrices = [vector_target_matrix]

        if scalar_target_matrix is not None:
            target_matrices.append(scalar_target_matrix)

    elif net_type_string == neural_net.U_NET_TYPE_STRING:
        target_matrices = [vector_target_matrix]
    else:
        target_matrices = [scalar_target_matrix]

    example_dict = {
        example_io.VECTOR_TARGET_NAMES_KEY:
            generator_option_dict[neural_net.VECTOR_TARGET_NAMES_KEY],
        example_io.SCALAR_TARGET_NAMES_KEY:
            generator_option_dict[neural_net.SCALAR_TARGET_NAMES_KEY],
        example_io.HEIGHTS_KEY:
            generator_option_dict[neural_net.HEIGHTS_KEY]
    }

    new_example_dict = neural_net.targets_numpy_to_dict(
        target_matrices=target_matrices,
        example_dict=example_dict, net_type_string=net_type_string
    )
    for this_key in TARGET_VALUE_KEYS:
        example_dict[this_key] = new_example_dict[this_key]

    return example_dict


def _run(model_file_name, example_dir_name, first_time_string, last_time_string,
         output_file_name):
    """Applies trained neural net in inference mode.

    This is effectively the main method.

    :param model_file_name: See documentation at top of file.
    :param example_dir_name: Same.
    :param first_time_string: Same.
    :param last_time_string: Same.
    :param output_file_name: Same.
    """

    first_time_unix_sec = time_conversion.string_to_unix_sec(
        first_time_string, TIME_FORMAT
    )
    last_time_unix_sec = time_conversion.string_to_unix_sec(
        last_time_string, TIME_FORMAT
    )

    print('Reading model from: "{0:s}"...'.format(model_file_name))
    model_object = neural_net.read_model(model_file_name)

    metafile_name = neural_net.find_metafile(
        model_dir_name=os.path.split(model_file_name)[0],
        raise_error_if_missing=True
    )

    print('Reading metadata from: "{0:s}"...'.format(metafile_name))
    metadata_dict = neural_net.read_metafile(metafile_name)

    is_loss_constrained_mse = neural_net.determine_if_loss_constrained_mse(
        metadata_dict[neural_net.LOSS_FUNCTION_KEY]
    )

    generator_option_dict = copy.deepcopy(
        metadata_dict[neural_net.TRAINING_OPTIONS_KEY]
    )
    generator_option_dict[neural_net.EXAMPLE_DIRECTORY_KEY] = example_dir_name
    generator_option_dict[neural_net.BATCH_SIZE_KEY] = NUM_EXAMPLES_PER_BATCH
    generator_option_dict[neural_net.FIRST_TIME_KEY] = first_time_unix_sec
    generator_option_dict[neural_net.LAST_TIME_KEY] = last_time_unix_sec

    target_norm_type_string = copy.deepcopy(
        generator_option_dict[neural_net.TARGET_NORM_TYPE_KEY]
    )

    # target_norm_type_string = copy.deepcopy(
    #     generator_option_dict[neural_net.TARGET_NORM_TYPE_KEY]
    # )
    # generator_option_dict[neural_net.TARGET_NORM_TYPE_KEY] = None
    net_type_string = metadata_dict[neural_net.NET_TYPE_KEY]

    generator = neural_net.data_generator(
        option_dict=generator_option_dict, for_inference=True,
        net_type_string=net_type_string, is_loss_constrained_mse=False
    )
    print(SEPARATOR_STRING)

    scalar_target_matrix = None
    scalar_prediction_matrix = None
    vector_target_matrix = None
    vector_prediction_matrix = None
    example_id_strings = []

    while True:
        this_scalar_target_matrix = None
        this_scalar_prediction_matrix = None
        this_vector_target_matrix = None
        this_vector_prediction_matrix = None

        try:
            this_predictor_matrix, this_target_array, these_id_strings = (
                next(generator)
            )
        except (RuntimeError, StopIteration):
            break

        this_prediction_array = neural_net.apply_model(
            model_object=model_object, predictor_matrix=this_predictor_matrix,
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            net_type_string=net_type_string,
            is_loss_constrained_mse=is_loss_constrained_mse, verbose=True
        )
        print(SEPARATOR_STRING)

        example_id_strings += these_id_strings

        if net_type_string == neural_net.CNN_TYPE_STRING:
            this_vector_target_matrix = this_target_array[0]
            this_vector_prediction_matrix = this_prediction_array[0]

            if len(this_target_array) == 2:
                this_scalar_target_matrix = this_target_array[1]
                this_scalar_prediction_matrix = this_prediction_array[1]

        elif net_type_string == neural_net.DENSE_NET_TYPE_STRING:
            this_scalar_target_matrix = this_target_array
            this_scalar_prediction_matrix = this_prediction_array[0]
        else:
            this_vector_target_matrix = this_target_array
            this_vector_prediction_matrix = this_prediction_array[0]

        if this_scalar_target_matrix is not None:
            if scalar_target_matrix is None:
                scalar_target_matrix = this_scalar_target_matrix + 0.
                scalar_prediction_matrix = this_scalar_prediction_matrix + 0.
            else:
                scalar_target_matrix = numpy.concatenate(
                    (scalar_target_matrix, this_scalar_target_matrix), axis=0
                )
                scalar_prediction_matrix = numpy.concatenate(
                    (scalar_prediction_matrix, this_scalar_prediction_matrix),
                    axis=0
                )

        if this_vector_target_matrix is not None:
            if vector_target_matrix is None:
                vector_target_matrix = this_vector_target_matrix + 0.
                vector_prediction_matrix = this_vector_prediction_matrix + 0.
            else:
                vector_target_matrix = numpy.concatenate(
                    (vector_target_matrix, this_vector_target_matrix), axis=0
                )
                vector_prediction_matrix = numpy.concatenate(
                    (vector_prediction_matrix, this_vector_prediction_matrix),
                    axis=0
                )

    target_example_dict = _targets_numpy_to_dict(
        scalar_target_matrix=scalar_target_matrix,
        vector_target_matrix=vector_target_matrix,
        model_metadata_dict=metadata_dict
    )

    prediction_example_dict = _targets_numpy_to_dict(
        scalar_target_matrix=scalar_prediction_matrix,
        vector_target_matrix=vector_prediction_matrix,
        model_metadata_dict=metadata_dict
    )

    normalization_file_name = (
        generator_option_dict[neural_net.NORMALIZATION_FILE_KEY]
    )
    print((
        'Reading training examples (for normalization) from: "{0:s}"...'
    ).format(
        normalization_file_name
    ))
    training_example_dict = example_io.read_file(normalization_file_name)

    if target_norm_type_string is not None:
        print('Denormalizing predicted values...')

        num_examples = len(example_id_strings)
        num_heights = len(prediction_example_dict[example_io.HEIGHTS_KEY])

        this_dict = {
            example_io.VECTOR_PREDICTOR_NAMES_KEY: [],
            example_io.VECTOR_PREDICTOR_VALS_KEY:
                numpy.full((num_examples, num_heights, 0), 0.),
            example_io.SCALAR_PREDICTOR_NAMES_KEY: [],
            example_io.SCALAR_PREDICTOR_VALS_KEY:
                numpy.full((num_examples, 0), 0.)
        }
        prediction_example_dict.update(this_dict)

        prediction_example_dict = normalization.denormalize_data(
            new_example_dict=prediction_example_dict,
            training_example_dict=training_example_dict,
            normalization_type_string=target_norm_type_string,
            min_normalized_value=
            generator_option_dict[neural_net.TARGET_MIN_NORM_VALUE_KEY],
            max_normalized_value=
            generator_option_dict[neural_net.TARGET_MAX_NORM_VALUE_KEY],
            separate_heights=True, apply_to_predictors=False,
            apply_to_targets=True
        )

        target_example_dict.update(this_dict)

        target_example_dict = normalization.denormalize_data(
            new_example_dict=target_example_dict,
            training_example_dict=training_example_dict,
            normalization_type_string=target_norm_type_string,
            min_normalized_value=
            generator_option_dict[neural_net.TARGET_MIN_NORM_VALUE_KEY],
            max_normalized_value=
            generator_option_dict[neural_net.TARGET_MAX_NORM_VALUE_KEY],
            separate_heights=True, apply_to_predictors=False,
            apply_to_targets=True
        )

        down_flux_inc_matrix_w_m02_pa01 = example_io.get_field_from_dict(
            example_dict=target_example_dict,
            field_name=example_io.SHORTWAVE_DOWN_FLUX_INC_NAME
        )

        print(example_id_strings[0])
        print(down_flux_inc_matrix_w_m02_pa01[0, :])

    add_heating_rate = generator_option_dict[neural_net.OMIT_HEATING_RATE_KEY]

    if add_heating_rate:
        pressure_matrix_pascals = _get_unnormalized_pressure(
            model_metadata_dict=metadata_dict,
            example_id_strings=example_id_strings
        )

        prediction_example_dict = _get_predicted_heating_rates(
            prediction_example_dict=prediction_example_dict,
            pressure_matrix_pascals=pressure_matrix_pascals,
            model_metadata_dict=metadata_dict
        )

    print('Writing target (actual) and predicted values to: "{0:s}"...'.format(
        output_file_name
    ))
    prediction_io.write_file(
        netcdf_file_name=output_file_name,
        scalar_target_matrix=
        target_example_dict[example_io.SCALAR_TARGET_VALS_KEY],
        vector_target_matrix=
        target_example_dict[example_io.VECTOR_TARGET_VALS_KEY],
        scalar_prediction_matrix=
        prediction_example_dict[example_io.SCALAR_TARGET_VALS_KEY],
        vector_prediction_matrix=
        prediction_example_dict[example_io.VECTOR_TARGET_VALS_KEY],
        example_id_strings=example_id_strings, model_file_name=model_file_name
    )


if __name__ == '__main__':
    INPUT_ARG_OBJECT = INPUT_ARG_PARSER.parse_args()

    _run(
        model_file_name=getattr(INPUT_ARG_OBJECT, MODEL_FILE_ARG_NAME),
        example_dir_name=getattr(INPUT_ARG_OBJECT, EXAMPLE_DIR_ARG_NAME),
        first_time_string=getattr(INPUT_ARG_OBJECT, FIRST_TIME_ARG_NAME),
        last_time_string=getattr(INPUT_ARG_OBJECT, LAST_TIME_ARG_NAME),
        output_file_name=getattr(INPUT_ARG_OBJECT, OUTPUT_FILE_ARG_NAME)
    )
