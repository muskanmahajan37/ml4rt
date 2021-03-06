"""IO methods for RRTM (Rapid Radiative-transfer Model) files."""

import copy
import os.path
import warnings
import numpy
import netCDF4
from gewittergefahr.gg_utils import time_conversion
from gewittergefahr.gg_utils import moisture_conversions as moisture_conv
from gewittergefahr.gg_utils import longitude_conversion as longitude_conv
from gewittergefahr.gg_utils import error_checking
from ml4rt.utils import example_utils

MIN_BAD_VALUE = 1e30

KM_TO_METRES = 1000.
DEG_TO_RADIANS = numpy.pi / 180

VALID_TIMES_KEY = 'time'
HEIGHTS_KEY = 'height'
STANDARD_ATMO_FLAGS_KEY = 'stdatmos'

DEFAULT_SCALAR_PREDICTOR_NAMES = [
    example_utils.ZENITH_ANGLE_NAME, example_utils.ALBEDO_NAME,
    example_utils.LATITUDE_NAME, example_utils.LONGITUDE_NAME,
    example_utils.COLUMN_LIQUID_WATER_PATH_NAME,
    example_utils.COLUMN_ICE_WATER_PATH_NAME
]

DEFAULT_VECTOR_PREDICTOR_NAMES = [
    example_utils.PRESSURE_NAME, example_utils.TEMPERATURE_NAME,
    example_utils.SPECIFIC_HUMIDITY_NAME,
    example_utils.LIQUID_WATER_CONTENT_NAME,
    example_utils.ICE_WATER_CONTENT_NAME
]

DEFAULT_SCALAR_TARGET_NAMES = [
    example_utils.SHORTWAVE_SURFACE_DOWN_FLUX_NAME,
    example_utils.SHORTWAVE_TOA_UP_FLUX_NAME
]

DEFAULT_VECTOR_TARGET_NAMES = [
    example_utils.SHORTWAVE_DOWN_FLUX_NAME,
    example_utils.SHORTWAVE_UP_FLUX_NAME,
    example_utils.SHORTWAVE_HEATING_RATE_NAME
]

PREDICTOR_NAME_TO_ORIG = {
    example_utils.ZENITH_ANGLE_NAME: 'sza',
    example_utils.LATITUDE_NAME: 'lat',
    example_utils.LONGITUDE_NAME: 'lon',
    example_utils.ALBEDO_NAME: 'albedo',
    example_utils.COLUMN_LIQUID_WATER_PATH_NAME: 'lwp',
    example_utils.COLUMN_ICE_WATER_PATH_NAME: 'iwp',
    example_utils.PRESSURE_NAME: 'p',
    example_utils.TEMPERATURE_NAME: 't',
    example_utils.SPECIFIC_HUMIDITY_NAME: 'q',
    example_utils.LIQUID_WATER_CONTENT_NAME: 'lwc',
    example_utils.ICE_WATER_CONTENT_NAME: 'iwc'
}

PREDICTOR_NAME_TO_CONV_FACTOR = {
    example_utils.ZENITH_ANGLE_NAME: DEG_TO_RADIANS,
    example_utils.LATITUDE_NAME: 1.,
    example_utils.LONGITUDE_NAME: 1.,
    example_utils.ALBEDO_NAME: 1.,
    example_utils.COLUMN_LIQUID_WATER_PATH_NAME: 0.001,
    example_utils.COLUMN_ICE_WATER_PATH_NAME: 0.001,
    example_utils.PRESSURE_NAME: 100.,
    example_utils.TEMPERATURE_NAME: 1.,
    example_utils.SPECIFIC_HUMIDITY_NAME: 0.001,
    example_utils.LIQUID_WATER_CONTENT_NAME: 0.001,
    example_utils.ICE_WATER_CONTENT_NAME: 0.001
}

TARGET_NAME_TO_ORIG = {
    example_utils.SHORTWAVE_SURFACE_DOWN_FLUX_NAME: 'sfcflux',
    example_utils.SHORTWAVE_TOA_UP_FLUX_NAME: 'toaflux',
    example_utils.SHORTWAVE_DOWN_FLUX_NAME: 'fluxd',
    example_utils.SHORTWAVE_UP_FLUX_NAME: 'fluxu',
    example_utils.SHORTWAVE_HEATING_RATE_NAME: 'hr'
}


def _layerwise_water_path_to_content(
        layerwise_path_matrix_kg_m02, heights_m_agl):
    """Converts profile of layerwise water path to profile of water content.

    E = number of examples
    H = number of heights

    :param layerwise_path_matrix_kg_m02: E-by-H numpy array of layerwise water
        paths (kg m^-2).  "Layerwise" means that the value in each grid cell is
        only the water path through that grid cell, not integrated over multiple
        grid cells.
    :param heights_m_agl: length-H numpy array with heights of grid-cell centers
        (metres above ground level).
    :return: water_content_matrix_kg_m03: E-by-H numpy array of water contents
        (kg m^-3).
    """

    edge_heights_m_agl = example_utils.get_grid_cell_edges(heights_m_agl)
    grid_cell_widths_metres = example_utils.get_grid_cell_widths(
        edge_heights_m_agl
    )

    num_examples = layerwise_path_matrix_kg_m02.shape[0]
    num_heights = layerwise_path_matrix_kg_m02.shape[1]

    grid_cell_width_matrix_metres = numpy.reshape(
        grid_cell_widths_metres, (1, num_heights)
    )
    grid_cell_width_matrix_metres = numpy.repeat(
        grid_cell_width_matrix_metres, repeats=num_examples, axis=0
    )

    return layerwise_path_matrix_kg_m02 / grid_cell_width_matrix_metres


def _water_content_to_layerwise_path(
        water_content_matrix_kg_m03, heights_m_agl):
    """Converts profile of water content to layerwise water path.

    This method is the inverse of `_layerwise_water_path_to_content`.

    :param water_content_matrix_kg_m03: See doc for
        `_layerwise_water_path_to_content`.
    :param heights_m_agl: Same.
    :return: layerwise_path_matrix_kg_m02: Same.
    """

    edge_heights_m_agl = example_utils.get_grid_cell_edges(heights_m_agl)
    grid_cell_widths_metres = example_utils.get_grid_cell_widths(
        edge_heights_m_agl
    )

    num_examples = water_content_matrix_kg_m03.shape[0]
    num_heights = water_content_matrix_kg_m03.shape[1]

    grid_cell_width_matrix_metres = numpy.reshape(
        grid_cell_widths_metres, (1, num_heights)
    )
    grid_cell_width_matrix_metres = numpy.repeat(
        grid_cell_width_matrix_metres, repeats=num_examples, axis=0
    )

    return water_content_matrix_kg_m03 * grid_cell_width_matrix_metres


def _get_air_density(example_dict):
    """Computes profiles of air density.

    E = number of examples
    H = number of heights

    :param example_dict: Dictionary of examples (in the format returned by
        `read_file`).
    :return: air_density_matrix_kg_m03: E-by-H numpy array of densities
        (kg m^-3).
    """

    specific_humidity_matrix_kg_kg01 = example_utils.get_field_from_dict(
        example_dict=example_dict,
        field_name=example_utils.SPECIFIC_HUMIDITY_NAME
    )
    temperature_matrix_kelvins = example_utils.get_field_from_dict(
        example_dict=example_dict, field_name=example_utils.TEMPERATURE_NAME
    )
    pressure_matrix_pascals = example_utils.get_field_from_dict(
        example_dict=example_dict, field_name=example_utils.PRESSURE_NAME
    )

    mixing_ratio_matrix_kg_kg01 = (
        moisture_conv.specific_humidity_to_mixing_ratio(
            specific_humidity_matrix_kg_kg01
        )
    )
    vapour_pressure_matrix_pascals = (
        moisture_conv.mixing_ratio_to_vapour_pressure(
            mixing_ratios_kg_kg01=mixing_ratio_matrix_kg_kg01,
            total_pressures_pascals=pressure_matrix_pascals
        )
    )
    virtual_temp_matrix_kelvins = (
        moisture_conv.temperature_to_virtual_temperature(
            temperatures_kelvins=temperature_matrix_kelvins,
            total_pressures_pascals=pressure_matrix_pascals,
            vapour_pressures_pascals=vapour_pressure_matrix_pascals
        )
    )

    denominator_matrix = (
        moisture_conv.DRY_AIR_GAS_CONSTANT_J_KG01_K01 *
        virtual_temp_matrix_kelvins
    )
    return pressure_matrix_pascals / denominator_matrix


def _specific_to_relative_humidity(example_dict):
    """Converts profiles of specific humidity to relative humidity.

    :param example_dict: Dictionary of examples (in the format returned by
        `read_file`).
    :return: example_dict: Same as input but with extra predictor variable.
    """

    specific_humidity_matrix_kg_kg01 = example_utils.get_field_from_dict(
        example_dict=example_dict,
        field_name=example_utils.SPECIFIC_HUMIDITY_NAME
    )
    temperature_matrix_kelvins = example_utils.get_field_from_dict(
        example_dict=example_dict, field_name=example_utils.TEMPERATURE_NAME
    )
    pressure_matrix_pascals = example_utils.get_field_from_dict(
        example_dict=example_dict, field_name=example_utils.PRESSURE_NAME
    )

    dewpoint_matrix_kelvins = moisture_conv.specific_humidity_to_dewpoint(
        specific_humidities_kg_kg01=specific_humidity_matrix_kg_kg01,
        temperatures_kelvins=temperature_matrix_kelvins,
        total_pressures_pascals=pressure_matrix_pascals
    )

    relative_humidity_matrix = moisture_conv.dewpoint_to_relative_humidity(
        dewpoints_kelvins=dewpoint_matrix_kelvins,
        temperatures_kelvins=temperature_matrix_kelvins,
        total_pressures_pascals=pressure_matrix_pascals
    )

    vector_predictor_names = (
        example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY]
    )
    found_rh = example_utils.RELATIVE_HUMIDITY_NAME in vector_predictor_names
    if not found_rh:
        vector_predictor_names.append(example_utils.RELATIVE_HUMIDITY_NAME)

    rh_index = (
        vector_predictor_names.index(example_utils.RELATIVE_HUMIDITY_NAME)
    )
    example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY] = (
        vector_predictor_names
    )

    if found_rh:
        example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY][..., rh_index] = (
            relative_humidity_matrix
        )
    else:
        example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY] = numpy.insert(
            example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY],
            obj=rh_index, values=relative_humidity_matrix, axis=-1
        )

    return example_dict


def _get_water_path_profiles(example_dict, get_lwp=True, get_iwp=True,
                             get_wvp=True, integrate_upward=False):
    """Computes profiles of LWP, IWP, and/or WVP.

    LWP = liquid-water path
    IWP = ice-water path
    WVP = water-vapour path

    If `integrate_upward == False`, then at height z, the LWP/IWP/WVP is the
    integral of LWC/IWC/WVC (respectively) from the top of atmosphere to z.

    If `integrate_upward == True`, then at height z, the LWP/IWP/WVP is the
    integral of LWC/IWC/WVC (respectively) from the surface to z.

    :param example_dict: Dictionary of examples (in the format returned by
        `read_file`).
    :param get_lwp: Boolean flag.  If True, will compute LWP profile for each
        example.
    :param get_iwp: Boolean flag.  If True, will compute IWP profile for each
        example.
    :param get_wvp: Boolean flag.  If True, will compute WVP profile for each
        example.
    :param integrate_upward: Boolean flag.  If True, will integrate from the
        surface up.  If False, will integrate from the top of atmosphere down.
    :return: example_dict: Same as input but with extra predictor variables.
    """

    vector_predictor_names = (
        example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY]
    )

    if integrate_upward:
        this_liquid_path_name = example_utils.UPWARD_LIQUID_WATER_PATH_NAME
        this_ice_path_name = example_utils.UPWARD_ICE_WATER_PATH_NAME
        this_vapour_path_name = example_utils.UPWARD_WATER_VAPOUR_PATH_NAME
    else:
        this_liquid_path_name = example_utils.LIQUID_WATER_PATH_NAME
        this_ice_path_name = example_utils.ICE_WATER_PATH_NAME
        this_vapour_path_name = example_utils.WATER_VAPOUR_PATH_NAME

    get_lwp = get_lwp and this_liquid_path_name not in vector_predictor_names
    get_iwp = get_iwp and this_ice_path_name not in vector_predictor_names
    get_wvp = get_wvp and this_vapour_path_name not in vector_predictor_names

    if not (get_lwp or get_iwp or get_wvp):
        return example_dict

    edge_heights_m_agl = example_utils.get_grid_cell_edges(
        example_dict[example_utils.HEIGHTS_KEY]
    )
    grid_cell_widths_metres = example_utils.get_grid_cell_widths(
        edge_heights_m_agl
    )

    num_examples = len(example_dict[example_utils.VALID_TIMES_KEY])
    num_heights = len(example_dict[example_utils.HEIGHTS_KEY])

    grid_cell_width_matrix_metres = numpy.reshape(
        grid_cell_widths_metres, (1, num_heights)
    )
    grid_cell_width_matrix_metres = numpy.repeat(
        grid_cell_width_matrix_metres, repeats=num_examples, axis=0
    )

    if get_lwp:
        lwc_matrix_kg_m03 = example_utils.get_field_from_dict(
            example_dict=example_dict,
            field_name=example_utils.LIQUID_WATER_CONTENT_NAME
        )

        if integrate_upward:
            lwp_matrix_kg_m02 = numpy.cumsum(
                lwc_matrix_kg_m03 * grid_cell_width_matrix_metres, axis=1
            )
        else:
            lwp_matrix_kg_m02 = numpy.fliplr(numpy.cumsum(
                numpy.fliplr(lwc_matrix_kg_m03 * grid_cell_width_matrix_metres),
                axis=1
            ))

        example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY].append(
            this_liquid_path_name
        )

        example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY] = (
            numpy.concatenate((
                example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY],
                numpy.expand_dims(lwp_matrix_kg_m02, axis=-1)
            ), axis=-1)
        )

    if get_iwp:
        iwc_matrix_kg_m03 = example_utils.get_field_from_dict(
            example_dict=example_dict,
            field_name=example_utils.ICE_WATER_CONTENT_NAME
        )

        if integrate_upward:
            iwp_matrix_kg_m02 = numpy.cumsum(
                iwc_matrix_kg_m03 * grid_cell_width_matrix_metres, axis=1
            )
        else:
            iwp_matrix_kg_m02 = numpy.fliplr(numpy.cumsum(
                numpy.fliplr(iwc_matrix_kg_m03 * grid_cell_width_matrix_metres),
                axis=1
            ))

        example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY].append(
            this_ice_path_name
        )

        example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY] = (
            numpy.concatenate((
                example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY],
                numpy.expand_dims(iwp_matrix_kg_m02, axis=-1)
            ), axis=-1)
        )

    if get_wvp:
        air_density_matrix_kg_m03 = _get_air_density(example_dict)
        specific_humidity_matrix_kg_kg01 = example_utils.get_field_from_dict(
            example_dict=example_dict,
            field_name=example_utils.SPECIFIC_HUMIDITY_NAME
        )
        vapour_content_matrix_kg_m03 = (
            specific_humidity_matrix_kg_kg01 * air_density_matrix_kg_m03
        )

        if integrate_upward:
            vapour_path_matrix_kg_m02 = numpy.cumsum(
                vapour_content_matrix_kg_m03 * grid_cell_width_matrix_metres,
                axis=1
            )
        else:
            vapour_path_matrix_kg_m02 = numpy.fliplr(numpy.cumsum(
                numpy.fliplr(
                    vapour_content_matrix_kg_m03 * grid_cell_width_matrix_metres
                ),
                axis=1
            ))

        example_dict[example_utils.VECTOR_PREDICTOR_NAMES_KEY].append(
            this_vapour_path_name
        )

        example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY] = (
            numpy.concatenate((
                example_dict[example_utils.VECTOR_PREDICTOR_VALS_KEY],
                numpy.expand_dims(vapour_path_matrix_kg_m02, axis=-1)
            ), axis=-1)
        )

    return example_dict


def find_file(directory_name, year, raise_error_if_missing=True):
    """Finds NetCDF file with RRTM data.

    :param directory_name: Name of directory where file is expected.
    :param year: Year (integer).
    :param raise_error_if_missing: Boolean flag.  If file is missing and
        `raise_error_if_missing == True`, will throw error.  If file is missing
        and `raise_error_if_missing == False`, will return *expected* file path.
    :return: rrtm_file_name: File path.
    :raises: ValueError: if file is missing
        and `raise_error_if_missing == True`.
    """

    error_checking.assert_is_string(directory_name)
    error_checking.assert_is_integer(year)
    error_checking.assert_is_boolean(raise_error_if_missing)

    rrtm_file_name = '{0:s}/rrtm_output_{1:04d}.nc'.format(directory_name, year)

    if raise_error_if_missing and not os.path.isfile(rrtm_file_name):
        error_string = 'Cannot find file.  Expected at: "{0:s}"'.format(
            rrtm_file_name
        )
        raise ValueError(error_string)

    return rrtm_file_name


def file_name_to_year(rrtm_file_name):
    """Parses year from file name.

    :param rrtm_file_name: Path to example file (readable by `read_file`).
    :return: year: Year (integer).
    """

    error_checking.assert_is_string(rrtm_file_name)
    pathless_file_name = os.path.split(rrtm_file_name)[-1]
    extensionless_file_name = os.path.splitext(pathless_file_name)[0]

    return int(extensionless_file_name.split('_')[-1])


def find_many_files(
        directory_name, first_time_unix_sec, last_time_unix_sec,
        raise_error_if_any_missing=True, raise_error_if_all_missing=True,
        test_mode=False):
    """Finds many NetCDF files with RRTM data.

    :param directory_name: Name of directory where files are expected.
    :param first_time_unix_sec: First time at which examples are desired.
    :param last_time_unix_sec: Last time at which examples are desired.
    :param raise_error_if_any_missing: Boolean flag.  If any file is missing and
        `raise_error_if_any_missing == True`, will throw error.
    :param raise_error_if_all_missing: Boolean flag.  If all files are missing
        and `raise_error_if_all_missing == True`, will throw error.
    :param test_mode: Leave this alone.
    :return: rrtm_file_names: 1-D list of paths to example files.  This list
        does *not* contain expected paths to non-existent files.
    """

    error_checking.assert_is_boolean(raise_error_if_any_missing)
    error_checking.assert_is_boolean(raise_error_if_all_missing)
    error_checking.assert_is_boolean(test_mode)

    start_year = int(
        time_conversion.unix_sec_to_string(first_time_unix_sec, '%Y')
    )
    end_year = int(
        time_conversion.unix_sec_to_string(last_time_unix_sec, '%Y')
    )
    years = numpy.linspace(
        start_year, end_year, num=end_year - start_year + 1, dtype=int
    )

    rrtm_file_names = []

    for this_year in years:
        this_file_name = find_file(
            directory_name=directory_name, year=this_year,
            raise_error_if_missing=raise_error_if_any_missing
        )

        if test_mode or os.path.isfile(this_file_name):
            rrtm_file_names.append(this_file_name)

    if raise_error_if_all_missing and len(rrtm_file_names) == 0:
        error_string = (
            'Cannot find any file in directory "{0:s}" from years {1:d}-{2:d}.'
        ).format(
            directory_name, start_year, end_year
        )
        raise ValueError(error_string)

    return rrtm_file_names


def read_file(netcdf_file_name, allow_bad_values=False):
    """Reads RRTM data from NetCDF file.

    E = number of examples
    H = number of heights
    P_s = number of scalar predictors
    P_v = number of vector predictors
    T_s = number of scalar targets
    T_v = number of vector targets

    :param netcdf_file_name: Path to NetCDF file with learning examples.
    :param allow_bad_values: Boolean flag.  If True, will allow bad values and
        remove examples that have bad values.

    :return: example_dict: Dictionary with the following keys.
    example_dict['scalar_predictor_matrix']: numpy array (E x P_s) with values
        of scalar predictors.
    example_dict['scalar_predictor_names']: list (length P_s) with names of
        scalar predictors.
    example_dict['vector_predictor_matrix']: numpy array (E x H x P_v) with
        values of vector predictors.
    example_dict['vector_predictor_names']: list (length P_v) with names of
        vector predictors.
    example_dict['scalar_target_matrix']: numpy array (E x T_s) with values of
        scalar targets.
    example_dict['scalar_target_names']: list (length T_s) with names of scalar
        targets.
    example_dict['vector_target_matrix']: numpy array (E x H x T_v) with values
        of vector targets.
    example_dict['vector_target_names']: list (length T_v) with names of vector
        targets.
    example_dict['valid_times_unix_sec']: length-E numpy array of valid times
        (Unix seconds).
    example_dict['heights_m_agl']: length-H numpy array of heights (metres above
        ground level).
    example_dict['standard_atmo_flags']: length-E numpy array of flags (each in
        the list `STANDARD_ATMO_ENUMS`).
    example_dict['example_id_strings']: length-E list of example IDs.
    """

    error_checking.assert_is_boolean(allow_bad_values)

    # TODO(thunderhoser): This is a HACK.
    if not os.path.isfile(netcdf_file_name):
        netcdf_file_name = netcdf_file_name.replace(
            '/home/ryan.lagerquist', '/home/ralager'
        )

    dataset_object = netCDF4.Dataset(netcdf_file_name)

    example_dict = {
        example_utils.SCALAR_PREDICTOR_NAMES_KEY:
            copy.deepcopy(DEFAULT_SCALAR_PREDICTOR_NAMES),
        example_utils.VECTOR_PREDICTOR_NAMES_KEY:
            copy.deepcopy(DEFAULT_VECTOR_PREDICTOR_NAMES),
        example_utils.SCALAR_TARGET_NAMES_KEY:
            copy.deepcopy(DEFAULT_SCALAR_TARGET_NAMES),
        example_utils.VECTOR_TARGET_NAMES_KEY:
            copy.deepcopy(DEFAULT_VECTOR_TARGET_NAMES),
        example_utils.VALID_TIMES_KEY: numpy.array(
            dataset_object.variables[VALID_TIMES_KEY][:],
            dtype=int
        ),
        example_utils.HEIGHTS_KEY: KM_TO_METRES * numpy.array(
            dataset_object.variables[HEIGHTS_KEY][:], dtype=float
        ),
        example_utils.STANDARD_ATMO_FLAGS_KEY: numpy.array(
            numpy.round(dataset_object.variables[STANDARD_ATMO_FLAGS_KEY][:]),
            dtype=int
        )
    }

    num_examples = len(example_dict[example_utils.VALID_TIMES_KEY])
    num_heights = len(example_dict[example_utils.HEIGHTS_KEY])
    num_scalar_predictors = len(DEFAULT_SCALAR_PREDICTOR_NAMES)
    num_vector_predictors = len(DEFAULT_VECTOR_PREDICTOR_NAMES)
    num_scalar_targets = len(DEFAULT_SCALAR_TARGET_NAMES)
    num_vector_targets = len(DEFAULT_VECTOR_TARGET_NAMES)

    scalar_predictor_matrix = numpy.full(
        (num_examples, num_scalar_predictors), numpy.nan
    )
    vector_predictor_matrix = numpy.full(
        (num_examples, num_heights, num_vector_predictors), numpy.nan
    )
    scalar_target_matrix = numpy.full(
        (num_examples, num_scalar_targets), numpy.nan
    )
    vector_target_matrix = numpy.full(
        (num_examples, num_heights, num_vector_targets), numpy.nan
    )

    for k in range(num_scalar_predictors):
        this_predictor_name_orig = (
            PREDICTOR_NAME_TO_ORIG[DEFAULT_SCALAR_PREDICTOR_NAMES[k]]
        )
        this_conversion_factor = (
            PREDICTOR_NAME_TO_CONV_FACTOR[DEFAULT_SCALAR_PREDICTOR_NAMES[k]]
        )
        scalar_predictor_matrix[:, k] = this_conversion_factor * numpy.array(
            dataset_object.variables[this_predictor_name_orig][:], dtype=float
        )

    for k in range(num_vector_predictors):
        this_predictor_name_orig = (
            PREDICTOR_NAME_TO_ORIG[DEFAULT_VECTOR_PREDICTOR_NAMES[k]]
        )
        this_conversion_factor = (
            PREDICTOR_NAME_TO_CONV_FACTOR[DEFAULT_VECTOR_PREDICTOR_NAMES[k]]
        )
        vector_predictor_matrix[..., k] = this_conversion_factor * numpy.array(
            dataset_object.variables[this_predictor_name_orig][:], dtype=float
        )

        if DEFAULT_VECTOR_PREDICTOR_NAMES[k] in [
                example_utils.LIQUID_WATER_CONTENT_NAME,
                example_utils.ICE_WATER_CONTENT_NAME
        ]:
            vector_predictor_matrix[..., k] = _layerwise_water_path_to_content(
                layerwise_path_matrix_kg_m02=vector_predictor_matrix[..., k],
                heights_m_agl=example_dict[example_utils.HEIGHTS_KEY]
            )

    for k in range(num_scalar_targets):
        this_target_name_orig = (
            TARGET_NAME_TO_ORIG[DEFAULT_SCALAR_TARGET_NAMES[k]]
        )
        scalar_target_matrix[:, k] = numpy.array(
            dataset_object.variables[this_target_name_orig][:], dtype=float
        )

    for k in range(num_vector_targets):
        this_target_name_orig = (
            TARGET_NAME_TO_ORIG[DEFAULT_VECTOR_TARGET_NAMES[k]]
        )
        vector_target_matrix[..., k] = numpy.array(
            dataset_object.variables[this_target_name_orig][:], dtype=float
        )

    example_dict.update({
        example_utils.SCALAR_PREDICTOR_VALS_KEY: scalar_predictor_matrix,
        example_utils.VECTOR_PREDICTOR_VALS_KEY: vector_predictor_matrix,
        example_utils.SCALAR_TARGET_VALS_KEY: scalar_target_matrix,
        example_utils.VECTOR_TARGET_VALS_KEY: vector_target_matrix
    })

    dataset_object.close()

    example_dict[example_utils.EXAMPLE_IDS_KEY] = (
        example_utils.create_example_ids(example_dict)
    )

    if allow_bad_values:
        bad_predictor_flags = numpy.logical_or(
            numpy.any(scalar_predictor_matrix >= MIN_BAD_VALUE, axis=1),
            numpy.any(vector_predictor_matrix >= MIN_BAD_VALUE, axis=(1, 2))
        )

        bad_target_flags = numpy.logical_or(
            numpy.any(scalar_target_matrix >= MIN_BAD_VALUE, axis=1),
            numpy.any(vector_target_matrix >= MIN_BAD_VALUE, axis=(1, 2))
        )

        good_indices = numpy.where(numpy.invert(
            numpy.logical_or(bad_predictor_flags, bad_target_flags)
        ))[0]

        num_examples = scalar_predictor_matrix.shape[0]

        if len(good_indices) != num_examples:
            warning_string = '{0:d} of {1:d} examples have bad values.'.format(
                num_examples - len(good_indices), num_examples
            )
            warnings.warn(warning_string)

        example_dict = example_utils.subset_by_index(
            example_dict=example_dict, desired_indices=good_indices
        )

    longitude_index = (
        example_dict[example_utils.SCALAR_PREDICTOR_NAMES_KEY].index(
            example_utils.LONGITUDE_NAME
        )
    )

    k = example_utils.SCALAR_PREDICTOR_VALS_KEY

    example_dict[k][:, longitude_index] = (
        longitude_conv.convert_lng_positive_in_west(
            longitudes_deg=example_dict[k][:, longitude_index], allow_nan=False
        )
    )

    example_dict = _get_water_path_profiles(
        example_dict=example_dict, get_lwp=True, get_iwp=True, get_wvp=True,
        integrate_upward=False
    )

    example_dict = _get_water_path_profiles(
        example_dict=example_dict, get_lwp=True, get_iwp=True, get_wvp=True,
        integrate_upward=True
    )

    example_dict = _specific_to_relative_humidity(example_dict)
    example_dict = example_utils.fluxes_actual_to_increments(example_dict)
    return example_utils.fluxes_increments_to_actual(example_dict)
