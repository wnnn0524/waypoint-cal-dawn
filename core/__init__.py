"""
核心计算模块
"""
from .coordinate_utils import (
    dms2deg, deg2dms, normalize_az,
    parse_dms_coordinate, format_degrees_as_dms
)
from .vincenty import (
    vincenty_forward, vincenty_inverse,
    meters_to_nautical_miles, nautical_miles_to_meters
)
from .intersection import (
    bearing_bearing_intersection_geo,
    segment_segment_intersection_geo,
    segment_bearing_intersection_geo,
    segment_distance_intersection_geo,
    circle_bearing_intersection_geo,
    circle_circle_intersection_geo
)

__all__ = [
    # 坐标工具
    'dms2deg', 'deg2dms', 'normalize_az',
    'parse_dms_coordinate', 'format_degrees_as_dms',
    # Vincenty算法
    'vincenty_forward', 'vincenty_inverse',
    'meters_to_nautical_miles', 'nautical_miles_to_meters',
    # 交会计算
    'bearing_bearing_intersection_geo',
    'segment_segment_intersection_geo',
    'segment_bearing_intersection_geo',
    'segment_distance_intersection_geo',
    'circle_bearing_intersection_geo',
    'circle_circle_intersection_geo'
]
