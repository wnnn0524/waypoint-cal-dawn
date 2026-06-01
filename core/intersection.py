"""
大地交会计算模块
"""
import math
from .vincenty import vincenty_forward, vincenty_inverse


def bearing_bearing_intersection_geo(lat1: float, lon1: float, az1: float,
                                      lat2: float, lon2: float, az2: float) -> tuple:
    """
    方位角与方位角交会（基于Vincenty精确扫描法）

    Args:
        lat1, lon1: 点1坐标
        az1: 从点1出发的方位角
        lat2, lon2: 点2坐标
        az2: 从点2出发的方位角

    Returns:
        (lat, lon) 交点坐标
    """
    az1 = ((az1 % 360) + 360) % 360
    az2 = ((az2 % 360) + 360) % 360

    def _az_error(lat_test, lon_test):
        _, az_actual, _ = vincenty_inverse(lat2, lon2, lat_test, lon_test)
        az_actual = ((az_actual % 360) + 360) % 360
        diff = (az_actual - az2 + 180) % 360 - 180
        return diff

    # 第一轮：粗扫描 0.1 - 200 NM，步长 0.01 NM
    best_lat, best_lon, best_err, best_d1_nm = None, None, 999.0, 0.0

    d1_nm = 0.1
    while d1_nm <= 200.0:
        lat_test, lon_test = vincenty_forward(lat1, lon1, az1, d1_nm * 1852.0)
        err = abs(_az_error(lat_test, lon_test))

        if err < best_err:
            best_err = err
            best_lat = lat_test
            best_lon = lon_test
            best_d1_nm = d1_nm

        if best_err < 0.1 and d1_nm > best_d1_nm + 1.0:
            break

        d1_nm += 0.01

    if best_lat is None:
        return None, None

    # 第二轮：在最佳值附近 0.5 NM 范围内精细扫描，步长 0.0001 NM
    start_nm = max(0.05, best_d1_nm - 0.5)
    end_nm = best_d1_nm + 0.5

    d1_nm = start_nm
    while d1_nm <= end_nm:
        lat_test, lon_test = vincenty_forward(lat1, lon1, az1, d1_nm * 1852.0)
        err = abs(_az_error(lat_test, lon_test))

        if err < best_err:
            best_err = err
            best_lat = lat_test
            best_lon = lon_test

        d1_nm += 0.0001

    return best_lat, best_lon


def segment_segment_intersection_geo(lat1: float, lon1: float, lat2: float, lon2: float,
                                      lat3: float, lon3: float, lat4: float, lon4: float) -> tuple:
    """
    线段与线段交会（大地坐标系）
    
    Args:
        lat1, lon1: 线段1起点
        lat2, lon2: 线段1终点
        lat3, lon3: 线段2起点
        lat4, lon4: 线段2终点
    
    Returns:
        (lat, lon) 交点坐标，无交点返回 (None, None)
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    lat3_rad = math.radians(lat3)
    lon3_rad = math.radians(lon3)
    lat4_rad = math.radians(lat4)
    lon4_rad = math.radians(lon4)
    
    x1 = lon1_rad
    y1 = math.log(math.tan(math.pi / 4 + lat1_rad / 2))
    x2 = lon2_rad
    y2 = math.log(math.tan(math.pi / 4 + lat2_rad / 2))
    x3 = lon3_rad
    y3 = math.log(math.tan(math.pi / 4 + lat3_rad / 2))
    x4 = lon4_rad
    y4 = math.log(math.tan(math.pi / 4 + lat4_rad / 2))
    
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-12:
        return None, None
    
    ua_num = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
    ub_num = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
    ua = ua_num / denom
    ub = ub_num / denom
    
    if 0 <= ua <= 1 and 0 <= ub <= 1:
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        lat_rad = 2 * math.atan(math.exp(y)) - math.pi / 2
        lon_rad = x
        lat = math.degrees(lat_rad)
        lon = math.degrees(lon_rad)
        lon = ((lon + 180) % 360) - 180
        return lat, lon
    
    return None, None


def segment_bearing_intersection_geo(lat1: float, lon1: float, lat2: float, lon2: float,
                                      lat3: float, lon3: float, az3: float) -> tuple:
    """
    线段与方位角交会（大地坐标系）
    
    Args:
        lat1, lon1: 线段起点
        lat2, lon2: 线段终点
        lat3, lon3: 方位角起点
        az3: 方位角
    
    Returns:
        (lat, lon) 交点坐标，无交点返回 (None, None)
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    lat3_rad = math.radians(lat3)
    lon3_rad = math.radians(lon3)
    az3_rad = math.radians(az3)
    
    x1 = lon1_rad
    y1 = math.log(math.tan(math.pi / 4 + lat1_rad / 2))
    x2 = lon2_rad
    y2 = math.log(math.tan(math.pi / 4 + lat2_rad / 2))
    x3 = lon3_rad
    y3 = math.log(math.tan(math.pi / 4 + lat3_rad / 2))
    a3 = math.sin(az3_rad)
    b3 = -math.cos(az3_rad)
    
    denom = a3 * (y2 - y1) - b3 * (x2 - x1)
    if abs(denom) < 1e-12:
        return None, None
    
    t = -(a3 * (y1 - y3) - b3 * (x1 - x3)) / denom
    if 0 <= t <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        lat_rad = 2 * math.atan(math.exp(y)) - math.pi / 2
        lon_rad = x
        lat = math.degrees(lat_rad)
        lon = math.degrees(lon_rad)
        lon = ((lon + 180) % 360) - 180
        return lat, lon
    
    return None, None


def segment_distance_intersection_geo(lat1: float, lon1: float, lat2: float, lon2: float,
                                       distance_from_lat1: float) -> tuple:
    """
    射线与距离交会（大地坐标系）
    
    从lat1出发，沿lat1到lat2的方向前进指定距离
    
    Args:
        lat1, lon1: 起点坐标
        lat2, lon2: 方向点坐标
        distance_from_lat1: 距离（米）
    
    Returns:
        (lat, lon) 计算点坐标
    """
    _, az12, _ = vincenty_inverse(lat1, lon1, lat2, lon2)
    lat, lon = vincenty_forward(lat1, lon1, az12, distance_from_lat1)
    return lat, lon


def circle_bearing_intersection_geo(lat1: float, lon1: float, radius: float,
                                     lat2: float, lon2: float, az2: float) -> list:
    """
    圆与方位角交会（大地坐标系）
    
    Args:
        lat1, lon1: 圆心坐标
        radius: 半径（米）
        lat2, lon2: 方位角起点
        az2: 方位角
    
    Returns:
        [(lat, lon)] 交点列表（0-2个）
    """
    intersections = []
    step = 0.0001
    for i in range(1000):
        dist = i * step * 100000
        lat_p, lon_p = vincenty_forward(lat2, lon2, az2, dist)
        d, _, _ = vincenty_inverse(lat1, lon1, lat_p, lon_p)
        if abs(d - radius) < 10:
            intersections.append((lat_p, lon_p))
            if len(intersections) == 2:
                break
    return intersections


def circle_circle_intersection_geo(lat1: float, lon1: float, r1: float,
                                    lat2: float, lon2: float, r2: float) -> list:
    """
    圆与圆交会（大地坐标系）
    
    Args:
        lat1, lon1: 圆1圆心
        r1: 圆1半径（米）
        lat2, lon2: 圆2圆心
        r2: 圆2半径（米）
    
    Returns:
        [(lat, lon)] 交点列表（0-2个）
    """
    intersections = []
    d, az12, _ = vincenty_inverse(lat1, lon1, lat2, lon2)
    
    if d > r1 + r2 or d < abs(r1 - r2):
        return []
    
    if d == 0 and r1 == r2:
        return []
    
    a = (r1**2 - r2**2 + d**2) / (2 * d)
    h = math.sqrt(r1**2 - a**2)
    
    lat_mid, lon_mid = vincenty_forward(lat1, lon1, az12, a)
    _, _, az_back = vincenty_inverse(lat1, lon1, lat_mid, lon_mid)
    
    perp_az1 = normalize_az(az_back + 90)
    perp_az2 = normalize_az(az_back - 90)
    
    lat_int1, lon_int1 = vincenty_forward(lat_mid, lon_mid, perp_az1, h)
    lat_int2, lon_int2 = vincenty_forward(lat_mid, lon_mid, perp_az2, h)
    
    intersections.append((lat_int1, lon_int1))
    intersections.append((lat_int2, lon_int2))
    
    return intersections


def normalize_az(az: float) -> float:
    """
    方位角归一化到 0-360 度
    """
    az = az % 360
    if az < 0:
        az += 360
    return az
