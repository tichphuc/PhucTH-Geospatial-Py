import numpy as np
import pandas as pd
from scipy.interpolate import griddata, Rbf

def get_grid_from_df(df: pd.DataFrame, points_xy=['lon', 'lat']):
    """
    Trường hợp df được rút ra từ *một raster đầy đủ* (không thiếu pixel):
    Dùng trực tiếp các giá trị lon/lat duy nhất làm trục lưới.

    Lưu ý: nếu df thiếu hàng/cột, lưới vẫn sinh ra đủ trục (cartesian product)
    nhưng dữ liệu nội suy sẽ trả NaN ở nơi không có điểm (với griddata 'linear/cubic').

    Returns
    -------
    (Xg, Yg) : tuple[np.ndarray, np.ndarray]
    """
    x_unique = np.sort(df[points_xy[0]].unique())
    y_unique = np.sort(df[points_xy[1]].unique())
    Xg, Yg = np.meshgrid(x_unique, y_unique)
    return Xg, Yg

def getInterpArray_griddata(
    df,
    points_xy=['lon', 'lat'],
    feature='temperature_2m',
    my_grid=None,                    # kỳ vọng tuple (Xg, Yg) dạng 2D từ np.meshgrid
    my_method='cubic'                # 'linear' | 'nearest' | 'cubic'
):
    """
    Nội suy từ các điểm rời rạc -> lưới đều bằng scipy.interpolate.griddata.

    Parameters
    ----------
    df : pandas.DataFrame
        Bảng chứa các cột toạ độ và giá trị cần nội suy.
    points_xy : list[str], default ['lon','lat']
        Tên 2 cột toạ độ trong df (theo thứ tự x, y).
    feature : str, default 'temperature_2m'
        Tên cột giá trị z cần nội suy.
    my_grid : tuple[np.ndarray, np.ndarray]
        (Xg, Yg) là 2 mảng 2D cùng shape, thường tạo bởi np.meshgrid.
    my_method : str, default 'cubic'
        Phương pháp nội suy: 'linear' | 'nearest' | 'cubic'.

    Returns
    -------
    Z : np.ndarray
        Mảng 2D (cùng shape với Xg/Yg) là kết quả nội suy trên lưới.
        Lưu ý: ngoài convex hull sẽ là NaN (trừ khi dùng 'nearest').
    """
    if my_grid is None or len(my_grid) != 2:
        raise ValueError("my_grid phải là tuple (Xg, Yg) 2D được tạo bởi np.meshgrid.")

    # Lấy điểm (x, y) và giá trị z từ DataFrame
    points = df[[points_xy[0], points_xy[1]]].to_numpy()   # shape (N, 2)
    values = df[feature].to_numpy()                        # shape (N,)

    # Loại bỏ hàng có NaN để tránh lỗi trong nội suy
    mask = ~np.isnan(values) & ~np.isnan(points).any(axis=1)
    points = points[mask]
    values = values[mask]

    # Nội suy lên lưới
    Xg, Yg = my_grid
    Z = griddata(points, values, (Xg, Yg), method=my_method)

    return Z

def getInterpArray_rbf(
    df,
    points_xy=['lon', 'lat'],
    feature='temperature_2m',
    my_grid=None,                    # kỳ vọng tuple (Xg, Yg) dạng 2D từ np.meshgrid
    my_method='cubic'                # sẽ được ánh xạ sang kernel của RBF
):
    """
    Nội suy từ các điểm rời rạc -> lưới đều bằng scipy.interpolate.Rbf (Radial Basis Function).
    Ưu điểm: có thể ngoại suy ra ngoài convex hull; bề mặt mượt. Nhược: chậm với N lớn.

    Parameters
    ----------
    df : pandas.DataFrame
        Bảng chứa các cột toạ độ và giá trị cần nội suy.
    points_xy : list[str], default ['lon','lat']
        Tên 2 cột toạ độ trong df (theo thứ tự x, y).
    feature : str, default 'temperature_2m'
        Tên cột giá trị z cần nội suy.
    my_grid : tuple[np.ndarray, np.ndarray]
        (Xg, Yg) là 2 mảng 2D cùng shape, thường tạo bởi np.meshgrid.
    my_method : str, default 'cubic'
        Được ánh xạ sang 'function' của Rbf:
            - 'linear'  -> 'linear'
            - 'cubic'   -> 'cubic'
            - 'quintic' -> 'quintic'
            - 'nearest' -> không có trong Rbf, sẽ chuyển về 'linear'
            - khác      -> 'thin_plate'

    Returns
    -------
    Z : np.ndarray
        Mảng 2D (cùng shape với Xg/Yg) là kết quả nội suy trên lưới.
        Khác với griddata, Rbf có thể ngoại suy nên thường không NaN ngoài biên.
    """
    if my_grid is None or len(my_grid) != 2:
        raise ValueError("my_grid phải là tuple (Xg, Yg) 2D được tạo bởi np.meshgrid.")

    # Lấy điểm (x, y) và giá trị z
    x = df[points_xy[0]].to_numpy()
    y = df[points_xy[1]].to_numpy()
    z = df[feature].to_numpy()

    # Loại bỏ NaN
    mask = ~np.isnan(x) & ~np.isnan(y) & ~np.isnan(z)
    x, y, z = x[mask], y[mask], z[mask]

    # Ánh xạ method -> kernel của Rbf
    method_lower = (my_method or "").lower()
    if method_lower in {"linear", "cubic", "quintic", "thin_plate", "multiquadric", "inverse", "gaussian"}:
        rbf_func = method_lower
    elif method_lower == "nearest":
        # Rbf không có 'nearest' -> dùng 'linear' như một xấp xỉ hợp lý
        rbf_func = "linear"
    else:
        # Mặc định mượt và ổn định
        rbf_func = "thin_plate"

    # Khởi tạo RBF (smooth=0 -> khớp đúng dữ liệu; tăng smooth nếu muốn làm mượt)
    rbf = Rbf(x, y, z, function=rbf_func, smooth=0.0)

    # Đánh giá trên lưới
    Xg, Yg = my_grid
    Z = rbf(Xg, Yg)

    return Z
