import time
import requests
import pandas as pd
from typing import Sequence, Tuple, Optional, Union

# https://open-meteo.com/en/docs/historical-weather-api

def getMeteoData(
    coor: Sequence[float],                 # [lat, lon]
    se_time: Tuple[str, str],              # ('YYYY-MM-DD', 'YYYY-MM-DD')
    meteo_features: Union[str, Sequence[str]],  # 'temperature_2m,...' hoặc list các biến
    output_path: Optional[str] = None,     # đường dẫn CSV để lưu (nếu muốn)
    timezone: str = 'GMT',                 # múi giờ Open-Meteo (vd: 'GMT', 'Asia/Bangkok')
    sleep_time: Optional[str] = None,      # tgian nghỉ nếu cần
):
    """
    Gọi Open-Meteo Archive API để lấy dữ liệu **hourly** trong khoảng thời gian cho trước
    tại tọa độ (lat, lon), trả về DataFrame và (nếu chỉ định) ghi ra CSV.

    Parameters
    ----------
    coor : Sequence[float]
        [latitude, longitude] theo WGS84 (độ).
    se_time : (str, str)
        (start_date, end_date) dạng 'YYYY-MM-DD'.
    meteo_features : str | Sequence[str]
        Tên các biến hourly của Open-Meteo (chuỗi phẩy hoặc list).
        Ví dụ: ['temperature_2m', 'relative_humidity_2m'].
    output_path : str | None
        Nếu khác None, kết quả sẽ được ghi ra CSV tại đường dẫn này.
    timezone : str
        Múi giờ mà API sẽ trả về (ví dụ 'GMT', 'Asia/Bangkok').

    Returns
    -------
    pd.DataFrame | None
        Bảng dữ liệu khí tượng theo giờ. Trả None nếu request thất bại.
    """

    # Chuẩn hóa tham số 'hourly': API mong chuỗi phẩy, nên nối nếu người dùng đưa list.
    if isinstance(meteo_features, (list, tuple)):
        hourly_param = ",".join(meteo_features)
    else:
        hourly_param = str(meteo_features)

    # 1) Tạo bộ tham số gửi lên API
    meteo_request_param = {
        'latitude' : str(coor[0]),
        'longitude': str(coor[1]),
        'start_date': se_time[0],
        'end_date'  : se_time[1],
        'hourly'    : hourly_param,   # danh sách biến theo giờ, cách nhau bởi dấu phẩy
        'timezone'  : timezone        # ví dụ: 'GMT' (UTC+0) hoặc 'Asia/Bangkok'
    }

    # (Tùy chọn) nghỉ 1s để “nhẹ nhàng” với rate-limit khi lặp nhiều lần
    if sleep_time != None:
        time.sleep(1)

    # 2) Gửi yêu cầu GET tới Open-Meteo Archive API
    rq = requests.get(
        'https://archive-api.open-meteo.com/v1/archive',
        params=meteo_request_param,
        timeout=30
    )

    # 3) Kiểm tra trạng thái HTTP
    if rq.ok:
        rq_json = rq.json()  # parse JSON trả về

        # 4) Phần "hourly" trong JSON là một dict các mảng -> chuyển thành DataFrame
        df_meteo = pd.DataFrame(rq_json['hourly'])

        # 5) Gắn thêm thông tin tọa độ:
        #    - meteo_lat/lon: tọa độ API phản hồi (đã làm tròn 6 chữ số)
        #    - my_lat/lon   : tọa độ bạn yêu cầu (để đối chiếu)
        df_meteo['meteo_lat'] = [round(rq_json['latitude'], 6)]  * len(df_meteo)
        df_meteo['meteo_lon'] = [round(rq_json['longitude'], 6)] * len(df_meteo)
        df_meteo['my_lat']    = [meteo_request_param['latitude']]  * len(df_meteo)
        df_meteo['my_lon']    = [meteo_request_param['longitude']] * len(df_meteo)

        # 6) Chuẩn hoá định dạng thời gian: bỏ dấu '-' trong chuỗi ISO
        #    (ví dụ '2024-01-01T10:00' -> '20240101T10:00')
        df_meteo['time'] = df_meteo['time'].apply(lambda r: r.replace('-', ''))

        # 7) Ghi ra CSV nếu được yêu cầu
        if output_path is not None:
            df_meteo.to_csv(output_path, index=False)

        return df_meteo

    # 8) Trường hợp request lỗi -> thông báo ngắn gọn và trả None
    print(f"=> request error! HTTP {rq.status_code}: {rq.text[:200]}")
    return None
