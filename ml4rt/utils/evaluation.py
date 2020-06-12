"""Methods for model evaluation."""

import numpy
from gewittergefahr.gg_utils import histograms
from gewittergefahr.gg_utils import error_checking
from ml4rt.io import example_io
from ml4rt.machine_learning import neural_net

DEFAULT_NUM_RELIABILITY_BINS = 20
DEFAULT_MAX_BIN_EDGE_PERCENTILE = 99.

SCALAR_TARGET_STDEV_KEY = 'scalar_target_stdevs'
SCALAR_PREDICTION_STDEV_KEY = 'scalar_prediction_stdevs'
VECTOR_TARGET_STDEV_KEY = 'vector_target_stdevs'
VECTOR_PREDICTION_STDEV_KEY = 'vector_prediction_stdevs'
SCALAR_MSE_KEY = 'scalar_mse_values'
SCALAR_MSE_SKILL_KEY = 'scalar_mse_skill_scores'
VECTOR_MSE_KEY = 'vector_mse_matrix'
VECTOR_MSE_SKILL_KEY = 'vector_mse_ss_matrix'
SCALAR_MAE_KEY = 'scalar_mae_values'
SCALAR_MAE_SKILL_KEY = 'scalar_mae_skill_scores'
VECTOR_MAE_KEY = 'vector_mae_matrix'
VECTOR_MAE_SKILL_KEY = 'vector_mae_ss_matrix'
SCALAR_BIAS_KEY = 'scalar_biases'
VECTOR_BIAS_KEY = 'vector_bias_matrix'
SCALAR_CORRELATION_KEY = 'scalar_correlations'
SCALAR_CORRELATION_SKILL_KEY = 'scalar_correlation_skill_scores'
VECTOR_CORRELATION_KEY = 'vector_correlation_matrix'
VECTOR_CORRELATION_SKILL_KEY = 'vector_correlation_ss_matrix'
SCALAR_RELIABILITY_X_KEY = 'scalar_reliability_x_matrix'
SCALAR_RELIABILITY_Y_KEY = 'scalar_reliability_y_matrix'
SCALAR_RELIABILITY_COUNT_KEY = 'scalar_reliability_count_matrix'
VECTOR_RELIABILITY_X_KEY = 'vector_reliability_x_matrix'
VECTOR_RELIABILITY_Y_KEY = 'vector_reliability_y_matrix'
VECTOR_RELIABILITY_COUNT_KEY = 'vector_reliability_count_matrix'


def _check_args(
        scalar_target_matrix, scalar_prediction_matrix,
        mean_training_example_dict, is_cnn, vector_target_matrix=None,
        vector_prediction_matrix=None):
    """Error-checks input args for methods called `get_*_all_variables`.

    :param scalar_target_matrix: See doc for `get_*_all_variables`.
    :param scalar_prediction_matrix: Same.
    :param mean_training_example_dict: Same.
    :param is_cnn: Same.
    :param vector_target_matrix: Same.
    :param vector_prediction_matrix: Same.
    """

    error_checking.assert_is_boolean(is_cnn)
    error_checking.assert_is_numpy_array_without_nan(scalar_target_matrix)

    if is_cnn:
        num_scalar_targets = (
            mean_training_example_dict[example_io.SCALAR_TARGET_NAMES_KEY]
        )
    else:
        scalar_prediction_matrix_climo = (
            neural_net.make_dense_net_target_matrix(mean_training_example_dict)
        )
        num_scalar_targets = scalar_prediction_matrix_climo.shape[-1]

    num_examples = scalar_target_matrix.shape[0]
    these_expected_dim = numpy.array(
        [num_examples, num_scalar_targets], dtype=int
    )
    error_checking.assert_is_numpy_array(
        scalar_target_matrix, exact_dimensions=these_expected_dim
    )

    error_checking.assert_is_numpy_array_without_nan(scalar_prediction_matrix)
    error_checking.assert_is_numpy_array(
        scalar_prediction_matrix, exact_dimensions=these_expected_dim
    )

    if is_cnn:
        num_vector_targets = (
            mean_training_example_dict[example_io.VECTOR_TARGET_NAMES_KEY]
        )

        error_checking.assert_is_numpy_array_without_nan(vector_target_matrix)
        error_checking.assert_is_numpy_array(
            vector_target_matrix, num_dimensions=3
        )

        num_heights = vector_target_matrix.shape[1]
        these_expected_dim = numpy.array(
            [num_examples, num_heights, num_vector_targets], dtype=int
        )
        error_checking.assert_is_numpy_array(
            vector_target_matrix, exact_dimensions=these_expected_dim
        )

        error_checking.assert_is_numpy_array_without_nan(
            vector_prediction_matrix
        )
        error_checking.assert_is_numpy_array(
            vector_prediction_matrix, exact_dimensions=these_expected_dim
        )


def _get_mse_one_scalar(target_values, predicted_values):
    """Computes mean squared error (MSE) for one scalar target variable.

    E = number of examples

    :param target_values: length-E numpy array of target (actual) values.
    :param predicted_values: length-E numpy array of predicted values.
    :return: mean_squared_error: Self-explanatory.
    """

    return numpy.mean((target_values - predicted_values) ** 2)


def _get_mse_ss_one_scalar(target_values, predicted_values,
                           mean_training_target_value):
    """Computes MSE skill score for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :param mean_training_target_value: Mean target value over all training
        examples.
    :return: mse_skill_score: Self-explanatory.
    """

    mse_actual = _get_mse_one_scalar(
        target_values=target_values, predicted_values=predicted_values
    )
    mse_climo = _get_mse_one_scalar(
        target_values=target_values, predicted_values=mean_training_target_value
    )

    return (mse_climo - mse_actual) / mse_climo


def _get_mae_one_scalar(target_values, predicted_values):
    """Computes mean absolute error (MAE) for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :return: mean_absolute_error: Self-explanatory.
    """

    return numpy.mean(numpy.abs(target_values - predicted_values))


def _get_mae_ss_one_scalar(target_values, predicted_values,
                           mean_training_target_value):
    """Computes MAE skill score for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :param mean_training_target_value: See doc for `_get_mse_ss_one_scalar`.
    :return: mae_skill_score: Self-explanatory.
    """

    mae_actual = _get_mae_one_scalar(
        target_values=target_values, predicted_values=predicted_values
    )
    mae_climo = _get_mae_one_scalar(
        target_values=target_values, predicted_values=mean_training_target_value
    )

    return (mae_climo - mae_actual) / mae_climo


def _get_bias_one_scalar(target_values, predicted_values):
    """Computes bias (mean signed error) for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :return: bias: Self-explanatory.
    """

    return numpy.mean(predicted_values - target_values)


def _get_correlation_one_scalar(target_values, predicted_values):
    """Computes Pearson correlation for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :return: correlation: Self-explanatory.
    """

    numerator = numpy.sum(
        (target_values - numpy.mean(target_values)) *
        (predicted_values - numpy.mean(predicted_values))
    )
    sum_squared_target_diffs = numpy.sum(
        (target_values - numpy.mean(target_values)) ** 2
    )
    sum_squared_prediction_diffs = numpy.sum(
        (predicted_values - numpy.mean(predicted_values)) ** 2
    )

    correlation = (
        numerator /
        numpy.sqrt(sum_squared_target_diffs * sum_squared_prediction_diffs)
    )

    print(correlation)
    print(numpy.corrcoef(target_values, predicted_values)[0, 1])

    return correlation


def _get_correlation_ss_one_scalar(target_values, predicted_values,
                                   mean_training_target_value):
    """Computes Pearson-correlation skill score for one scalar target variable.

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :param mean_training_target_value: See doc for `_get_mse_ss_one_scalar`.
    :return: correlation_skill_score: Self-explanatory.
    """

    correlation_actual = _get_correlation_one_scalar(
        target_values=target_values, predicted_values=predicted_values
    )
    correlation_climo = _get_correlation_one_scalar(
        target_values=target_values, predicted_values=mean_training_target_value
    )

    return (correlation_climo - correlation_actual) / correlation_climo


def _get_rel_curve_one_scalar(target_values, predicted_values, num_bins,
                              max_bin_edge):
    """Computes reliability curve for one scalar target variable.

    B = number of bins

    :param target_values: See doc for `_get_mse_one_scalar`.
    :param predicted_values: Same.
    :param num_bins: Number of bins (points in curve).
    :param max_bin_edge: Value at upper edge of last bin.
    :return: mean_predictions: length-B numpy array of x-coordinates.
    :return: mean_observations: length-B numpy array of y-coordinates.
    :return: example_counts: length-B numpy array with num examples in each bin.
    """

    bin_index_by_example = histograms.create_histogram(
        input_values=predicted_values, num_bins=num_bins, min_value=0.,
        max_value=max_bin_edge
    )[0]

    mean_predictions = numpy.full(num_bins, numpy.nan)
    mean_observations = numpy.full(num_bins, numpy.nan)
    example_counts = numpy.full(num_bins, -1, dtype=int)

    for i in range(num_bins):
        these_example_indices = numpy.where(bin_index_by_example == i)[0]

        example_counts[i] = len(these_example_indices)
        mean_predictions[i] = numpy.mean(
            predicted_values[these_example_indices]
        )
        mean_observations[i] = numpy.mean(target_values[these_example_indices])

    return mean_predictions, mean_observations, example_counts


def get_scores_all_variables(
        scalar_target_matrix, scalar_prediction_matrix,
        mean_training_example_dict, is_cnn,
        get_mse=True, get_mae=True, get_bias=True, get_correlation=True,
        get_reliability_curve=True,
        num_reliability_bins=DEFAULT_NUM_RELIABILITY_BINS,
        max_bin_edge_percentile=DEFAULT_MAX_BIN_EDGE_PERCENTILE,
        vector_target_matrix=None, vector_prediction_matrix=None):
    """Computes desired scores for all target variables.

    E = number of examples
    H = number of heights
    T_s = number of scalar targets
    T_v = number of vector targets
    B = number of bins for reliability curve

    :param scalar_target_matrix: numpy array (E x T_s) of target (actual)
        values.
    :param scalar_prediction_matrix: numpy array (E x T_s) of predicted values.
    :param mean_training_example_dict: See doc for... something.
    :param is_cnn: Boolean flag.  If True, evaluating CNN.  If False, evaluating
        CNN.
    :param get_mse: Boolean flag.  If True, will compute MSE and MSE skill score
        for each scalar target variable.
    :param get_mae: Boolean flag.  If True, will compute MAE and MAE skill score
        for each scalar target variable.
    :param get_bias: Boolean flag.  If True, will compute bias for each scalar
        target variable.
    :param get_correlation: Boolean flag.  If True, will compute correlation and
        correlation skill score for each scalar target variable.
    :param get_reliability_curve: Boolean flag.  If True, will compute points in
        reliability curve for each scalar target variable.
    :param num_reliability_bins: [used only if `get_reliability_curve == True`]
        Number of bins for each reliability curve.
    :param max_bin_edge_percentile:
        [used only if `get_reliability_curve == True`]
        Used to find upper edge of last bin for reliability curves.  For each
        scalar target variable y, the upper edge of the last bin will be the
        [q]th percentile of y-values, where q = `max_bin_edge_percentile`.
    :param vector_target_matrix: [used only if `is_cnn == True`]
        numpy array (E x H x T_v) of target (actual) values.
    :param vector_prediction_matrix: [used only if `is_cnn == True`]
        numpy array (E x H x T_v) of predicted values.

    :return: evaluation_dict: Dictionary with the following keys (some may be
        missing, depending on input args).
    evaluation_dict['scalar_target_stdevs']: numpy array (length T_s) of
        standard deviations for actual values.
    evaluation_dict['scalar_prediction_stdevs']: numpy array (length T_s) of
        standard deviations for predicted values.
    evaluation_dict['vector_target_stdev_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of standard deviations for actual values.
    evaluation_dict['vector_prediction_stdev_matrix']:
        [None if `is_cnn == False`]
        numpy array (H x T_v) of standard deviations for predicted values.
    evaluation_dict['scalar_mse_values']: numpy array (length T_s) of mean
        squared errors.
    evaluation_dict['scalar_mse_skill_scores']: numpy array (length T_s) of MSE
        skill scores.
    evaluation_dict['vector_mse_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of mean squared errors.
    evaluation_dict['vector_mse_ss_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of MSE skill scores.
    evaluation_dict['scalar_mae_values']: numpy array (length T_s) of mean
        absolute errors.
    evaluation_dict['scalar_mae_skill_scores']: numpy array (length T_s) of MAE
        skill scores.
    evaluation_dict['vector_mae_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of mean absolute errors.
    evaluation_dict['vector_mae_ss_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of MAE skill scores.
    evaluation_dict['scalar_biases']: numpy array (length T_s) of biases.
    evaluation_dict['vector_bias_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of biases.
    evaluation_dict['scalar_correlations']: numpy array (length T_s) of
        correlations.
    evaluation_dict['scalar_correlation_skill_scores']: numpy array (length T_s)
        of correlation skill scores.
    evaluation_dict['vector_correlation_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of correlations.
    evaluation_dict['vector_correlation_ss_matrix']: [None if `is_cnn == False`]
        numpy array (H x T_v) of correlation skill scores.
    evaluation_dict['scalar_reliability_x_matrix']: numpy array (T_s x B) of
        x-coordinates for reliability curves.
    evaluation_dict['scalar_reliability_y_matrix']: Same but for y-coordinates.
    evaluation_dict['scalar_reliability_count_matrix']: Same but for example
        counts.
    evaluation_dict['vector_reliability_x_matrix']: numpy array (H x T_v x B) of
        x-coordinates for reliability curves.
    evaluation_dict['vector_reliability_y_matrix']: Same but for y-coordinates.
    evaluation_dict['vector_reliability_count_matrix']: Same but for example
        counts.
    """

    # TODO(thunderhoser): Fix documentation for `mean_training_example_dict`.

    _check_args(
        scalar_target_matrix=scalar_target_matrix,
        scalar_prediction_matrix=scalar_prediction_matrix,
        mean_training_example_dict=mean_training_example_dict, is_cnn=is_cnn,
        vector_target_matrix=vector_target_matrix,
        vector_prediction_matrix=vector_prediction_matrix
    )

    error_checking.assert_is_boolean(get_mse)
    error_checking.assert_is_boolean(get_mae)
    error_checking.assert_is_boolean(get_bias)
    error_checking.assert_is_boolean(get_correlation)
    error_checking.assert_is_boolean(get_reliability_curve)

    if get_reliability_curve:
        error_checking.assert_is_integer(num_reliability_bins)
        error_checking.assert_is_geq(num_reliability_bins, 10)
        error_checking.assert_is_leq(num_reliability_bins, 1000)
        error_checking.assert_is_geq(max_bin_edge_percentile, 90.)
        error_checking.assert_is_leq(max_bin_edge_percentile, 100.)

    if is_cnn:
        scalar_prediction_matrix_climo = (
            mean_training_example_dict[example_io.SCALAR_TARGET_VALS_KEY]
        )
    else:
        scalar_prediction_matrix_climo = (
            neural_net.make_dense_net_target_matrix(mean_training_example_dict)
        )

    evaluation_dict = {
        SCALAR_TARGET_STDEV_KEY:
            numpy.std(scalar_target_matrix, axis=0, ddof=1),
        SCALAR_PREDICTION_STDEV_KEY:
            numpy.std(scalar_prediction_matrix, axis=0, ddof=1)
    }

    if is_cnn:
        num_heights = vector_target_matrix.shape[1]
        num_vector_targets = vector_target_matrix.shape[2]

        evaluation_dict[VECTOR_TARGET_STDEV_KEY] = numpy.std(
            vector_target_matrix, axis=0, ddof=1
        )
        evaluation_dict[VECTOR_PREDICTION_STDEV_KEY] = numpy.std(
            vector_prediction_matrix, axis=0, ddof=1
        )

    num_scalar_targets = scalar_prediction_matrix_climo.shape[1]

    if get_mse:
        scalar_mse_values = numpy.full(num_scalar_targets, numpy.nan)
        scalar_mse_skill_scores = numpy.full(num_scalar_targets, numpy.nan)

        for k in num_scalar_targets:
            scalar_mse_values[k] = _get_mse_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k]
            )

            scalar_mse_skill_scores[k] = _get_mse_ss_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k],
                mean_training_target_value=scalar_prediction_matrix_climo[0, k]
            )

        evaluation_dict[SCALAR_MSE_KEY] = scalar_mse_values
        evaluation_dict[SCALAR_MSE_SKILL_KEY] = scalar_mse_skill_scores

        if is_cnn:
            vector_mse_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )
            vector_mse_ss_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )

            for j in range(num_heights):
                for k in range(num_vector_targets):
                    vector_mse_matrix[j, k] = _get_mse_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k]
                    )

                    this_climo_value = mean_training_example_dict[
                        example_io.VECTOR_TARGET_VALS_KEY
                    ][0, j, k]

                    vector_mse_ss_matrix[j, k] = _get_mse_ss_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k],
                        mean_training_target_value=this_climo_value
                    )

            evaluation_dict[VECTOR_MSE_KEY] = vector_mse_matrix
            evaluation_dict[VECTOR_MSE_SKILL_KEY] = vector_mse_ss_matrix

    if get_mae:
        scalar_mae_values = numpy.full(num_scalar_targets, numpy.nan)
        scalar_mae_skill_scores = numpy.full(num_scalar_targets, numpy.nan)

        for k in num_scalar_targets:
            scalar_mae_values[k] = _get_mae_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k]
            )

            scalar_mae_skill_scores[k] = _get_mae_ss_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k],
                mean_training_target_value=scalar_prediction_matrix_climo[0, k]
            )

        evaluation_dict[SCALAR_MAE_KEY] = scalar_mae_values
        evaluation_dict[SCALAR_MAE_SKILL_KEY] = scalar_mae_skill_scores

        if is_cnn:
            vector_mae_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )
            vector_mae_ss_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )

            for j in range(num_heights):
                for k in range(num_vector_targets):
                    vector_mae_matrix[j, k] = _get_mae_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k]
                    )

                    this_climo_value = mean_training_example_dict[
                        example_io.VECTOR_TARGET_VALS_KEY
                    ][0, j, k]

                    vector_mae_ss_matrix[j, k] = _get_mae_ss_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k],
                        mean_training_target_value=this_climo_value
                    )

            evaluation_dict[VECTOR_MAE_KEY] = vector_mae_matrix
            evaluation_dict[VECTOR_MAE_SKILL_KEY] = vector_mae_ss_matrix

    if get_bias:
        scalar_biases = numpy.full(num_scalar_targets, numpy.nan)

        for k in num_scalar_targets:
            scalar_biases[k] = _get_bias_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k]
            )

        evaluation_dict[SCALAR_BIAS_KEY] = scalar_biases

        if is_cnn:
            vector_bias_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )

            for j in range(num_heights):
                for k in range(num_vector_targets):
                    vector_bias_matrix[j, k] = _get_bias_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k]
                    )

            evaluation_dict[VECTOR_BIAS_KEY] = vector_bias_matrix

    if get_correlation:
        scalar_correlations = numpy.full(num_scalar_targets, numpy.nan)
        scalar_correlation_skill_scores = numpy.full(
            num_scalar_targets, numpy.nan
        )

        for k in num_scalar_targets:
            scalar_correlations[k] = _get_correlation_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k]
            )

            scalar_correlation_skill_scores[k] = _get_correlation_ss_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k],
                mean_training_target_value=scalar_prediction_matrix_climo[0, k]
            )

        evaluation_dict[SCALAR_CORRELATION_KEY] = scalar_correlations
        evaluation_dict[SCALAR_CORRELATION_SKILL_KEY] = (
            scalar_correlation_skill_scores
        )

        if is_cnn:
            vector_correlation_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )
            vector_correlation_ss_matrix = numpy.full(
                (num_heights, num_vector_targets), numpy.nan
            )

            for j in range(num_heights):
                for k in range(num_vector_targets):
                    vector_correlation_matrix[j, k] = (
                        _get_correlation_one_scalar(
                            target_values=vector_target_matrix[:, j, k],
                            predicted_values=vector_prediction_matrix[:, j, k]
                        )
                    )

                    this_climo_value = mean_training_example_dict[
                        example_io.VECTOR_TARGET_VALS_KEY
                    ][0, j, k]

                    vector_correlation_ss_matrix[j, k] = (
                        _get_correlation_ss_one_scalar(
                            target_values=vector_target_matrix[:, j, k],
                            predicted_values=vector_prediction_matrix[:, j, k],
                            mean_training_target_value=this_climo_value
                        )
                    )

            evaluation_dict[VECTOR_CORRELATION_KEY] = vector_correlation_matrix
            evaluation_dict[VECTOR_CORRELATION_SKILL_KEY] = (
                vector_correlation_ss_matrix
            )

    if get_reliability_curve:
        these_dim = (num_scalar_targets, num_reliability_bins)
        scalar_reliability_x_matrix = numpy.full(these_dim, numpy.nan)
        scalar_reliability_y_matrix = numpy.full(these_dim, numpy.nan)
        scalar_reliability_count_matrix = numpy.full(these_dim, -1, dtype=int)

        for k in num_scalar_targets:
            these_x, these_y, these_counts = _get_rel_curve_one_scalar(
                target_values=scalar_target_matrix[:, k],
                predicted_values=scalar_prediction_matrix[:, k],
                num_bins=num_reliability_bins,
                max_bin_edge=numpy.percentile(
                    scalar_prediction_matrix[:, k], max_bin_edge_percentile
                )
            )

            scalar_reliability_x_matrix[k, :] = these_x
            scalar_reliability_y_matrix[k, :] = these_y
            scalar_reliability_count_matrix[k, :] = these_counts

        evaluation_dict[SCALAR_RELIABILITY_X_KEY] = scalar_reliability_x_matrix
        evaluation_dict[SCALAR_RELIABILITY_Y_KEY] = scalar_reliability_y_matrix
        evaluation_dict[SCALAR_RELIABILITY_COUNT_KEY] = (
            scalar_reliability_count_matrix
        )

        if is_cnn:
            these_dim = (num_heights, num_vector_targets, num_reliability_bins)
            vector_reliability_x_matrix = numpy.full(these_dim, numpy.nan)
            vector_reliability_y_matrix = numpy.full(these_dim, numpy.nan)
            vector_reliability_count_matrix = numpy.full(
                these_dim, -1, dtype=int
            )

            for j in range(num_heights):
                for k in range(num_vector_targets):
                    these_x, these_y, these_counts = _get_rel_curve_one_scalar(
                        target_values=vector_target_matrix[:, j, k],
                        predicted_values=vector_prediction_matrix[:, j, k],
                        num_bins=num_reliability_bins,
                        max_bin_edge=numpy.percentile(
                            vector_prediction_matrix[:, j, k],
                            max_bin_edge_percentile
                        )
                    )

                    vector_reliability_x_matrix[j, k, :] = these_x
                    vector_reliability_y_matrix[j, k, :] = these_y
                    vector_reliability_count_matrix[j, k, :] = these_counts

            evaluation_dict[VECTOR_RELIABILITY_X_KEY] = (
                vector_reliability_x_matrix
            )
            evaluation_dict[VECTOR_RELIABILITY_Y_KEY] = (
                vector_reliability_y_matrix
            )
            evaluation_dict[VECTOR_RELIABILITY_COUNT_KEY] = (
                vector_reliability_count_matrix
            )

    return evaluation_dict
