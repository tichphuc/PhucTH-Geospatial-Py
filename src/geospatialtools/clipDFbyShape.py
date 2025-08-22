import pandas as pd
import geopandas as gpd
from typing import Union
from pathlib import Path
# from osgeo import gdal

#-------------------------------------------------------------------------------
def clipDFbyShape (
        df: pd.DataFrame,
        shapefile: Union[str, Path, gpd.GeoDataFrame],
        coor=('smap_lat', 'smap_lon'),
    ) -> pd.DataFrame:
    """
        Hàm có chức năng cắt DataFrame theo shapefile. Hệ tọa độ WGS84 được sử dụng (hoặc theo hệ của shp).

        Parameters
        ----------
        df : pandas.DataFrame
            Bảng dữ liệu đầu vào có chứa tọa độ.
        shapefile : str | pathlib.Path | geopandas.GeoDataFrame
            Đường dẫn tới file biên (shp/geojson/…) hoặc GeoDataFrame đã đọc sẵn.
        coor : list, default ['smap_lat', 'smap_lon']
            Tên cột [latitude, longitude] trong DataFrame.

        Returns
        -------
        pandas.DataFrame
            DataFrame đã được cắt theo shapefile, giữ lại các cột ban đầu.
    """
    # Chuẩn hóa shapefile -> GeoDataFrame
    if isinstance(shapefile, (str, Path)):
        shp = gpd.read_file(str(shapefile))
    elif isinstance(shapefile, gpd.GeoDataFrame):
        shp = shapefile
    else:
        raise TypeError("`shapefile` phải là đường dẫn (str/Path) hoặc GeoDataFrame.")

    if shp.crs is None:
        raise ValueError("Shapefile không có CRS. Hãy gán CRS cho shapefile trước khi clip.")
    
    # Lấy danh sách cột gốc
    base_cols   = list(df.columns)

    # Convert DataFrame sang GeoDataFrame (tọa độ WGS84 mặc định theo shp)
    gdf_csv = gpd.GeoDataFrame(
                                df,
                                geometry    = gpd.points_from_xy(
                                                                df[coor[1]], df[coor[0]]
                                                            ),
                                crs = shapefile.crs #"EPSG:4326"
                            )   

    # gán hệ tọa độ cho gdf
    gdf_csv = gdf_csv.to_crs(shapefile.crs)

    # clip by shapefile
    cut_data= gpd.overlay(gdf_csv, shapefile, how='intersection')

    # Sắp xếp theo lat/lon (giữ index liên tục)
    cut_data_sorted = cut_data.sort_values(by=[coor[0], coor[1]]).reset_index(drop=True)

    # Trả về DataFrame (không geometry)
    return cut_data_sorted[base_cols]