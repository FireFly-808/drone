import numpy as np
import pandas as pd
from scipy import ndimage
import matplotlib.pyplot as plt


def detect_fires(thermal_data):
    temperature_threshold = 50
    thermal_data[6][0] = (
        thermal_data[6][1] + thermal_data[5][0] + thermal_data[7][0]
    ) / 3
    mlx_shape = (24, 32)  # mlx90640 shape

    mlx_interp_val = 10  # interpolate # on each dimension
    mlx_interp_shape = (
        mlx_shape[0] * mlx_interp_val,
        mlx_shape[1] * mlx_interp_val,
    )  # new shape

    data_array = np.reshape(thermal_data, mlx_shape)  # reshape
    # data_array = np.fliplr()  # flip data
    data_array = np.flipud(data_array)  # mirror image
    data_array = ndimage.zoom(data_array, mlx_interp_val)  # interpolate

    num_over_thresh = np.count_nonzero(data_array > temperature_threshold)
    return num_over_thresh

    # Uncomment if you want to plot IR data
    # plt.imshow(
    #     data_array,
    #     interpolation="none",
    #     cmap=plt.cm.bwr,
    #     vmin=np.min(data_array),
    #     vmax=np.max(data_array),
    # )
    # plt.colorbar()  # setup colorbar
    # # plt.set_label("Temperature [$^{\circ}$C]", fontsize=14)  # colorbar label
    # plt.show()