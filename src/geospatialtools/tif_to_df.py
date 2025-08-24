import rasterio
import pandas as pd
import numpy as np

def tif_to_dataframe(tif_path, to_latlon=True):
    """
    Đọc ảnh .tif và trả về DataFrame gồm 2 cột lat/lon và n cột band.
    
    Parameters:
        tif_path (str): đường dẫn file .tif
        to_latlon (bool): nếu True thì chuyển tọa độ sang EPSG:4326
        
    Returns:
        pd.DataFrame: DataFrame với các cột ['lat', 'lon', 'band_1', ..., 'band_n']
    """
    with rasterio.open(tif_path) as src:
        bands_data = src.read()  # shape: (bands, height, width)
        transform = src.transform
        crs = src.crs
        height, width = bands_data.shape[1], bands_data.shape[2]

        # Tạo lưới pixel index
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")

        # Tính tọa độ pixel center
        xs, ys = rasterio.transform.xy(transform, rows, cols)
        xs = np.array(xs)
        ys = np.array(ys)

        if to_latlon and crs is not None and crs.to_epsg() != 4326:
            from pyproj import Transformer
            transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(xs, ys)
        else:
            lon, lat = xs, ys

        # Chuyển bands thành (height*width, n_bands)
        bands_flat = bands_data.reshape(bands_data.shape[0], -1).T

        # Tạo DataFrame
        df = pd.DataFrame(bands_flat, columns=[f"band_{i+1}" for i in range(bands_data.shape[0])])
        df.insert(0, "lon", np.array(lon).ravel())
        df.insert(0, "lat", np.array(lat).ravel())

    return df