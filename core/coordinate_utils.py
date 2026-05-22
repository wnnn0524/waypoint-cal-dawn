"""
坐标转换工具模块
"""
import math


def dms2deg(d: int, m: int, s: float, direction: str) -> float:
    """
    度分秒转十进制度
    
    Args:
        d: 度
        m: 分
        s: 秒
        direction: 方向 ('N','S','E','W')
    
    Returns:
        十进制度
    """
    deg = d + m / 60 + s / 3600
    if direction in ['S', 'W']:
        deg = -deg
    return deg


def deg2dms(deg: float) -> tuple:
    """
    十进制度转度分秒
    
    Args:
        deg: 十进制度
    
    Returns:
        (d, m, s, lat_dir, lon_dir)
    """
    d = int(math.floor(math.fabs(deg)))
    rem = (math.fabs(deg) - d) * 60
    m = int(math.floor(rem))
    s = (rem - m) * 60
    lat_dir = 'N' if deg >= 0 else 'S'
    lon_dir = 'E' if deg >= 0 else 'W'
    return d, m, s, lat_dir, lon_dir


def normalize_az(az: float) -> float:
    """
    方位角归一化到 0-360 度
    
    Args:
        az: 方位角
    
    Returns:
        归一化后的方位角
    """
    az = az % 360
    if az < 0:
        az += 360
    return az


def parse_dms_coordinate(coord_str) -> float:
    """
    解析度分秒格式的坐标
    
    支持格式: N37-45-07.00, E112-36-54.30
    
    Args:
        coord_str: 坐标字符串
    
    Returns:
        十进制度
    """
    if coord_str is None or (isinstance(coord_str, float) and math.isnan(coord_str)):
        return None
    
    coord_str = str(coord_str).strip()
    if not coord_str:
        return None
    
    direction = coord_str[0]
    dms_part = coord_str[1:].replace(' ', '-').replace('°', '-').replace('\'', '-').replace('"', '-')
    
    parts = dms_part.split('-')
    parts = [p.strip() for p in parts if p.strip()]
    
    d = float(parts[0]) if parts else 0.0
    m = float(parts[1]) if len(parts) > 1 else 0.0
    s = float(parts[2]) if len(parts) > 2 else 0.0
    
    deg = d + m / 60 + s / 3600
    if direction in ['S', 'W']:
        deg = -deg
    return deg


def format_degrees_as_dms(lat: float, lon: float) -> str:
    """
    格式化坐标为度分秒字符串
    
    Args:
        lat: 纬度
        lon: 经度
    
    Returns:
        格式化的字符串，格式: N37-03-15.00，E112-51-01.00
    """
    lat_d, lat_m, lat_s, lat_dir, _ = deg2dms(lat)
    lon_d, lon_m, lon_s, _, lon_dir = deg2dms(lon)
    
    # 确保秒数在0-60范围内，处理浮点精度问题
    lat_s = min(lat_s, 59.9999)
    lon_s = min(lon_s, 59.9999)
    
    # 格式化秒数为 SS.SS 格式（使用round避免浮点数精度问题）
    lat_s_deg = int(lat_s)
    lat_s_sec = round((lat_s - lat_s_deg) * 100)
    lon_s_deg = int(lon_s)
    lon_s_sec = round((lon_s - lon_s_deg) * 100)
    
    # 处理四舍五入后可能超过59.99的情况
    if lat_s_sec >= 100:
        lat_s_deg += 1
        lat_s_sec = 0
    if lon_s_sec >= 100:
        lon_s_deg += 1
        lon_s_sec = 0
    
    lat_s_str = f"{lat_s_deg:02d}.{lat_s_sec:02d}"
    lon_s_str = f"{lon_s_deg:02d}.{lon_s_sec:02d}"
    
    return (f"{lat_dir}{int(lat_d):02d}-{int(lat_m):02d}-{lat_s_str}，{lon_dir}{int(lon_d):03d}-{int(lon_m):02d}-{lon_s_str}")
