"""
Vincenty 大地计算算法模块
"""
import math
from .coordinate_utils import normalize_az


# WGS84 椭球体参数
a = 6378137.0  # 长半轴
f = 1 / 298.257223563  # 扁率
b = a * (1 - f)  # 短半轴


def vincenty_forward(lat1: float, lon1: float, az12: float, s: float) -> tuple:
    """
    Vincenty 大地正算
    
    已知起点、方位角、距离，求终点坐标
    
    Args:
        lat1: 起点纬度（十进制度）
        lon1: 起点经度（十进制度）
        az12: 方位角（度）
        s: 距离（米）
    
    Returns:
        (lat2, lon2) 终点经纬度
    """
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    az12 = math.radians(az12)
    
    sin_alpha1 = math.sin(az12)
    cos_alpha1 = math.cos(az12)
    tan_u1 = (1 - f) * math.tan(lat1)
    cos_u1 = 1.0 / math.hypot(1.0, tan_u1)
    sin_u1 = tan_u1 * cos_u1
    sigma1 = math.atan2(tan_u1, cos_alpha1)
    sin_alpha = cos_u1 * sin_alpha1
    cos_sq_alpha = 1.0 - sin_alpha**2
    u_sq = cos_sq_alpha * (a**2 - b**2) / (b**2)
    A = 1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)))
    B = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)))
    sigma = s / (b * A)
    sigma_prev = 0.0
    
    for _ in range(100):
        if abs(sigma - sigma_prev) < 1e-12:
            break
        sigma_prev = sigma
        cos2sigma_m = math.cos(2.0 * sigma1 + sigma)
        sin_sigma = math.sin(sigma)
        cos_sigma = math.cos(sigma)
        delta_sigma = B * sin_sigma * (
            cos2sigma_m + B / 4.0 * (
                cos_sigma * (-1.0 + 2.0 * cos2sigma_m**2)
                - B / 6.0 * cos2sigma_m * (-3.0 + 4.0 * sin_sigma**2) * (-3.0 + 4.0 * cos2sigma_m**2)
            )
        )
        sigma = s / (b * A) + delta_sigma
    
    tmp = sin_u1 * sin_sigma - cos_u1 * cos_sigma * cos_alpha1
    lat2 = math.atan2(
        sin_u1 * cos_sigma + cos_u1 * sin_sigma * cos_alpha1,
        (1.0 - f) * math.hypot(sin_alpha, tmp)
    )
    lam = math.atan2(
        sin_sigma * sin_alpha1,
        cos_u1 * cos_sigma - sin_u1 * sin_sigma * cos_alpha1
    )
    C = f / 16.0 * cos_sq_alpha * (4.0 + f * (4.0 - 3.0 * cos_sq_alpha))
    L = lam - (1.0 - C) * f * sin_alpha * (
        sigma + C * sin_sigma * (cos2sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos2sigma_m**2))
    )
    lon2 = lon1 + L
    
    return math.degrees(lat2), math.degrees(lon2)


def vincenty_inverse(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple:
    """
    Vincenty 大地反算
    
    已知两点，求距离和方位角
    
    Args:
        lat1: 点1纬度（十进制度）
        lon1: 点1经度（十进制度）
        lat2: 点2纬度（十进制度）
        lon2: 点2经度（十进制度）
    
    Returns:
        (distance_m, az12, az21) 距离（米）、正方位角、反方位角
    """
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    delta_lon = lon2 - lon1
    tan_u1 = (1 - f) * math.tan(lat1)
    cos_u1 = 1.0 / math.hypot(1.0, tan_u1)
    sin_u1 = tan_u1 * cos_u1
    tan_u2 = (1 - f) * math.tan(lat2)
    cos_u2 = 1.0 / math.hypot(1.0, tan_u2)
    sin_u2 = tan_u2 * cos_u2
    lam = delta_lon
    lam_prev = 0.0
    
    for _ in range(100):
        if abs(lam - lam_prev) < 1e-12:
            break
        lam_prev = lam
        sin_lam = math.sin(lam)
        cos_lam = math.cos(lam)
        sin_sigma = math.hypot(
            cos_u2 * sin_lam,
            cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam
        )
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos_sq_alpha = 1.0 - sin_alpha**2
        
        if cos_sq_alpha == 0:
            cos2sigma_m = 0.0
        else:
            cos2sigma_m = cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha
        
        C = f / 16.0 * cos_sq_alpha * (4.0 + f * (4.0 - 3.0 * cos_sq_alpha))
        lam = delta_lon + (1.0 - C) * f * sin_alpha * (
            sigma + C * sin_sigma * (cos2sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos2sigma_m**2))
        )
    
    u_sq = cos_sq_alpha * (a**2 - b**2) / (b**2)
    A = 1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)))
    B = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)))
    cos2sigma_m = cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha
    sin_sigma = math.hypot(
        cos_u2 * math.sin(lam),
        cos_u1 * sin_u2 - sin_u1 * cos_u2 * math.cos(lam)
    )
    cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * math.cos(lam)
    delta_sigma = B * sin_sigma * (
        cos2sigma_m + B / 4.0 * (
            cos_sigma * (-1.0 + 2.0 * cos2sigma_m**2)
            - B / 6.0 * cos2sigma_m * (-3.0 + 4.0 * sin_sigma**2) * (-3.0 + 4.0 * cos2sigma_m**2)
        )
    )
    s = b * A * (sigma - delta_sigma)
    
    az12 = math.atan2(
        cos_u2 * math.sin(lam),
        cos_u1 * sin_u2 - sin_u1 * cos_u2 * math.cos(lam)
    )
    az21 = math.atan2(
        cos_u1 * math.sin(lam),
        -sin_u1 * cos_u2 + cos_u1 * sin_u2 * math.cos(lam)
    )
    az21 = az21 + math.pi
    
    return s, normalize_az(math.degrees(az12)), normalize_az(math.degrees(az21))


def meters_to_nautical_miles(meters: float) -> float:
    """
    米转换为海里
    
    Args:
        meters: 米
    
    Returns:
        海里
    """
    return meters / 1852.0


def nautical_miles_to_meters(nm: float) -> float:
    """
    海里转换为米
    
    Args:
        nm: 海里
    
    Returns:
        米
    """
    return nm * 1852.0
