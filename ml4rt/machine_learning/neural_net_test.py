"""Unit tests for neural_net.py."""

import unittest
import numpy
from ml4rt.io import example_io
from ml4rt.machine_learning import neural_net

TOLERANCE = 1e-6

# The following constants are used to test _make_cnn_predictor_matrix,
# _make_dense_net_predictor_matrix, and _make_dense_net_target_matrix.
HEIGHTS_M_AGL = numpy.array([100, 500], dtype=float)
VALID_TIMES_UNIX_SEC = numpy.array([0, 300, 600, 1200], dtype=int)
STANDARD_ATMO_FLAGS = numpy.array([0, 1, 2, 3], dtype=int)

SCALAR_PREDICTOR_NAMES = [
    example_io.ZENITH_ANGLE_NAME, example_io.LATITUDE_NAME
]
ZENITH_ANGLES_RADIANS = numpy.array([0, 1, 2, 3], dtype=float)
LATITUDES_DEG_N = numpy.array([40.02, 40.02, 40.02, 40.02])
SCALAR_PREDICTOR_MATRIX = numpy.transpose(numpy.vstack(
    (ZENITH_ANGLES_RADIANS, LATITUDES_DEG_N)
))

VECTOR_PREDICTOR_NAMES = [
    example_io.TEMPERATURE_NAME, example_io.SPECIFIC_HUMIDITY_NAME
]
TEMPERATURE_MATRIX_KELVINS = numpy.array([
    [290, 295],
    [289, 294],
    [288, 293],
    [287, 292.5]
])
SPEC_HUMIDITY_MATRIX_KG_KG01 = numpy.array([
    [0.008, 0.009],
    [0.007, 0.008],
    [0.005, 0.006],
    [0.0075, 0.01]
])
VECTOR_PREDICTOR_MATRIX = numpy.stack(
    (TEMPERATURE_MATRIX_KELVINS, SPEC_HUMIDITY_MATRIX_KG_KG01), axis=-1
)

SCALAR_TARGET_NAMES = [example_io.SHORTWAVE_SURFACE_DOWN_FLUX_NAME]
SURFACE_DOWN_FLUXES_W_M02 = numpy.array([200, 200, 200, 200], dtype=float)
SCALAR_TARGET_MATRIX = numpy.reshape(
    SURFACE_DOWN_FLUXES_W_M02, (len(SURFACE_DOWN_FLUXES_W_M02), 1)
)

VECTOR_TARGET_NAMES = [
    example_io.SHORTWAVE_DOWN_FLUX_NAME, example_io.SHORTWAVE_UP_FLUX_NAME
]

DOWNWELLING_FLUX_MATRIX_W_M02 = numpy.array([
    [300, 200],
    [500, 300],
    [450, 450],
    [200, 100]
], dtype=float)

UPWELLING_FLUX_MATRIX_W_M02 = numpy.array([
    [150, 150],
    [200, 150],
    [300, 350],
    [400, 100]
], dtype=float)

VECTOR_TARGET_MATRIX = numpy.stack(
    (DOWNWELLING_FLUX_MATRIX_W_M02, UPWELLING_FLUX_MATRIX_W_M02), axis=-1
)

EXAMPLE_DICT = {
    example_io.SCALAR_PREDICTOR_NAMES_KEY: SCALAR_PREDICTOR_NAMES,
    example_io.SCALAR_PREDICTOR_VALS_KEY: SCALAR_PREDICTOR_MATRIX,
    example_io.VECTOR_PREDICTOR_NAMES_KEY: VECTOR_PREDICTOR_NAMES,
    example_io.VECTOR_PREDICTOR_VALS_KEY: VECTOR_PREDICTOR_MATRIX,
    example_io.SCALAR_TARGET_NAMES_KEY: SCALAR_TARGET_NAMES,
    example_io.SCALAR_TARGET_VALS_KEY: SCALAR_TARGET_MATRIX,
    example_io.VECTOR_TARGET_NAMES_KEY: VECTOR_TARGET_NAMES,
    example_io.VECTOR_TARGET_VALS_KEY: VECTOR_TARGET_MATRIX,
    example_io.HEIGHTS_KEY: HEIGHTS_M_AGL,
    example_io.VALID_TIMES_KEY: VALID_TIMES_UNIX_SEC,
    example_io.STANDARD_ATMO_FLAGS_KEY: STANDARD_ATMO_FLAGS
}

THIS_ZENITH_ANGLE_MATRIX = numpy.array([
    [0, 0],
    [1, 1],
    [2, 2],
    [3, 3]
], dtype=float)

THIS_LATITUDE_MATRIX = numpy.full((4, 2), 40.02)
THIS_SCALAR_PREDICTOR_MATRIX = numpy.stack(
    (THIS_ZENITH_ANGLE_MATRIX, THIS_LATITUDE_MATRIX), axis=-1
)
CNN_PREDICTOR_MATRIX = numpy.concatenate(
    (VECTOR_PREDICTOR_MATRIX, THIS_SCALAR_PREDICTOR_MATRIX), axis=-1
)

DENSE_NET_PREDICTOR_MATRIX = numpy.array([
    [290, 295, 0.008, 0.009, 0, 40.02],
    [289, 294, 0.007, 0.008, 1, 40.02],
    [288, 293, 0.005, 0.006, 2, 40.02],
    [287, 292.5, 0.0075, 0.01, 3, 40.02]
])

DENSE_NET_TARGET_MATRIX = numpy.array([
    [300, 200, 150, 150, 200],
    [500, 300, 200, 150, 200],
    [450, 450, 300, 350, 200],
    [200, 100, 400, 100, 200]
], dtype=float)


class NeuralNetTests(unittest.TestCase):
    """Each method is a unit test for neural_net.py."""

    def test_make_cnn_predictor_matrix(self):
        """Ensures correct output from _make_cnn_predictor_matrix."""

        this_matrix = neural_net._make_cnn_predictor_matrix(EXAMPLE_DICT)
        self.assertTrue(numpy.allclose(
            this_matrix, CNN_PREDICTOR_MATRIX, atol=TOLERANCE
        ))

    def test_make_dense_net_predictor_matrix(self):
        """Ensures correct output from _make_dense_net_predictor_matrix."""

        this_matrix = neural_net._make_dense_net_predictor_matrix(EXAMPLE_DICT)
        self.assertTrue(numpy.allclose(
            this_matrix, DENSE_NET_PREDICTOR_MATRIX, atol=TOLERANCE
        ))

    def test_make_dense_net_target_matrix(self):
        """Ensures correct output from _make_dense_net_target_matrix."""

        this_matrix = neural_net._make_dense_net_target_matrix(EXAMPLE_DICT)
        self.assertTrue(numpy.allclose(
            this_matrix, DENSE_NET_TARGET_MATRIX, atol=TOLERANCE
        ))


if __name__ == '__main__':
    unittest.main()