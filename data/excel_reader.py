"""
Excel文件读取模块
"""
import pandas as pd
from typing import Dict, Any, Optional
import io


def load_excel_file(file_obj: io.BytesIO) -> Dict[str, pd.DataFrame]:
    """
    加载Excel文件，返回所有工作表
    
    Args:
        file_obj: 文件对象
    
    Returns:
        {sheet_name: DataFrame}
    """
    excel_file = pd.ExcelFile(file_obj)
    return {name: excel_file.parse(name) for name in excel_file.sheet_names}


class NavaidData:
    """Navaid表数据处理 - 支持嵌套双表结构"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
        # 检测是否为嵌套双表结构（Ident表 + LocID表在同一Sheet中）
        self.has_nested_structure = self._detect_nested_structure()
        
        if self.has_nested_structure:
            # 分离两个表
            self.ident_df, self.loc_df = self._split_nested_tables()
        else:
            self.ident_df = df
            self.loc_df = None
        
        # Ident表列
        self.ident_column = self._find_column(self.ident_df, ['Ident', 'IDENT', 'ident'])
        self.ident_lat_column = self._find_column(self.ident_df, ['Latitude', 'Lat', '纬度', 'LAT'])
        self.ident_lon_column = self._find_column(self.ident_df, ['Longitude', 'Lon', 'Long', '经度', 'LON'])
        
        # LocID表列
        self.loc_id_column = None
        self.loc_lat_column = None
        self.loc_lon_column = None
        if self.loc_df is not None:
            self.loc_id_column = self._find_column(self.loc_df, ['LocID', 'LocId', 'LOCID'])
            self.loc_lat_column = self._find_column(self.loc_df, ['LocLatitude', 'LocLat', 'LOCLAT', 'Latitude'])
            self.loc_lon_column = self._find_column(self.loc_df, ['LocLongitude', 'LocLon', 'LocLong', 'Longitude'])
    
    def _detect_nested_structure(self) -> bool:
        """检测是否存在嵌套双表结构"""
        # 检查第一列是否包含"AirportID"作为数据行（表示第二张表的开始）
        first_col = self.df.iloc[:, 0].astype(str).str.strip()
        return 'AirportID' in first_col.values
    
    def _split_nested_tables(self) -> tuple:
        """分离嵌套的两张表"""
        first_col = self.df.iloc[:, 0].astype(str).str.strip()
        
        # 找到AirportID所在的行索引（第二张表的表头行）
        airportid_row = -1
        for idx, val in enumerate(first_col):
            if val == 'AirportID':
                airportid_row = idx
                break
        
        if airportid_row == -1:
            return self.df, None
        
        # 第一张表：Ident表（从开始到AirportID行之前）
        ident_df = self.df.iloc[:airportid_row].copy()
        ident_df.columns = self.df.columns.tolist()
        
        # 第二张表：LocID表（从AirportID行开始）
        loc_df = self.df.iloc[airportid_row:].copy()
        
        # 将AirportID行作为新表头
        new_header = loc_df.iloc[0].tolist()
        loc_df = loc_df[1:].copy()
        loc_df.columns = new_header
        
        # 重置索引
        ident_df = ident_df.reset_index(drop=True)
        loc_df = loc_df.reset_index(drop=True)
        
        return ident_df, loc_df
    
    def _find_column(self, df, possible_names) -> Optional[str]:
        """在DataFrame中查找列"""
        if df is None:
            return None
        for name in possible_names:
            if name in df.columns:
                return name
        return None
    
    def has_ident_table(self) -> bool:
        """是否有Ident表"""
        return self.ident_column is not None and self.ident_lat_column is not None
    
    def has_locid_table(self) -> bool:
        """是否有LocID表"""
        return self.loc_df is not None and self.loc_id_column is not None and self.loc_lat_column is not None
    
    def get_coordinate(self, ident: str, use_loc: bool = False) -> Optional[tuple]:
        """
        获取坐标
        
        Args:
            ident: 标识
            use_loc: 是否使用LocID表
        
        Returns:
            (lat, lon) 或 None
        """
        from core import parse_dms_coordinate
        
        if use_loc:
            df = self.loc_df
            id_col = self.loc_id_column
            lat_col = self.loc_lat_column
            lon_col = self.loc_lon_column
        else:
            df = self.ident_df
            id_col = self.ident_column
            lat_col = self.ident_lat_column
            lon_col = self.ident_lon_column
        
        if df is None or id_col is None or lat_col is None or lon_col is None:
            return None
        
        rows = df[df[id_col].astype(str).str.strip() == str(ident).strip()]
        if rows.empty:
            return None
        
        row = rows.iloc[0]
        
        if pd.isna(row[lat_col]) or pd.isna(row[lon_col]):
            return None
        
        lat = parse_dms_coordinate(row[lat_col])
        lon = parse_dms_coordinate(row[lon_col])
        
        if lat is not None and lon is not None:
            return lat, lon
        return None
    
    def get_all_idents(self, use_loc: bool = False) -> list:
        """获取所有标识列表"""
        if use_loc:
            df = self.loc_df
            id_col = self.loc_id_column
        else:
            df = self.ident_df
            id_col = self.ident_column
        
        if df is None or id_col is None:
            return []
        
        return sorted([x for x in df[id_col].dropna().unique() if x and str(x).strip()])


class RunwayData:
    """Runway表数据处理"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.ident_column = self._find_ident_column()
        self.lat_column = self._find_lat_column()
        self.lon_column = self._find_lon_column()
    
    def _find_column(self, possible_names) -> Optional[str]:
        """在DataFrame中查找列（不区分大小写）"""
        # 首先尝试精确匹配
        for name in possible_names:
            if name in self.df.columns:
                return name
        
        # 如果精确匹配失败，尝试不区分大小写匹配
        df_cols_lower = {col.lower(): col for col in self.df.columns}
        for name in possible_names:
            if name.lower() in df_cols_lower:
                return df_cols_lower[name.lower()]
        
        return None
    
    def _find_ident_column(self) -> Optional[str]:
        """查找跑道标识列"""
        possible = ['Rwy Ident', 'RwyIdent', 'Runway', 'Runway ID', 'RWY', '跑道', 
                    'Rwy ID', 'Rwy', 'Ident', 'ID', '跑道标识']
        return self._find_column(possible)
    
    def _find_lat_column(self) -> Optional[str]:
        """查找纬度列"""
        possible = ['Rwy Latitude', 'Latitude', 'Lat', '纬度', 'LAT', 'latitude', 
                    'RwyLat', 'Rwy_Lat']
        return self._find_column(possible)
    
    def _find_lon_column(self) -> Optional[str]:
        """查找经度列"""
        possible = ['Rwy Longitude', 'Longitude', 'Lon', 'Long', '经度', 'LON', 'longitude',
                    'RwyLon', 'Rwy_Lon']
        return self._find_column(possible)
    
    def get_coordinate(self, ident: str) -> Optional[tuple]:
        """获取坐标"""
        from core import parse_dms_coordinate
        
        if not self.ident_column or self.ident_column not in self.df.columns:
            return None
        
        rows = self.df[self.df[self.ident_column].astype(str).str.strip() == str(ident).strip()]
        if rows.empty:
            return None
        
        row = rows.iloc[0]
        
        if not self.lat_column or not self.lon_column:
            return None
        
        if pd.isna(row[self.lat_column]) or pd.isna(row[self.lon_column]):
            return None
        
        lat = parse_dms_coordinate(row[self.lat_column])
        lon = parse_dms_coordinate(row[self.lon_column])
        
        if lat is not None and lon is not None:
            return lat, lon
        return None
    
    def get_all_idents(self) -> list:
        """获取所有标识列表"""
        if not self.ident_column or self.ident_column not in self.df.columns:
            return []
        return sorted([x for x in self.df[self.ident_column].dropna().unique() if x and str(x).strip()])


class WaypointData:
    """Waypoint表数据处理"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.ident_column = self._find_ident_column()
        self.lat_column = self._find_lat_column()
        self.lon_column = self._find_lon_column()
    
    def _find_ident_column(self) -> Optional[str]:
        """查找航点标识列"""
        possible = ['Ident', 'IDENT', 'ident', 'Code', 'CODE', 'code', 'Name', '名称', 'WPID']
        for col in possible:
            if col in self.df.columns:
                return col
        return None
    
    def _find_lat_column(self) -> Optional[str]:
        possible = ['Latitude', 'Lat', '纬度', 'LAT', 'latitude']
        for col in possible:
            if col in self.df.columns:
                return col
        return None
    
    def _find_lon_column(self) -> Optional[str]:
        possible = ['Longitude', 'Lon', 'Long', '经度', 'LON', 'longitude']
        for col in possible:
            if col in self.df.columns:
                return col
        return None
    
    def get_coordinate(self, ident: str) -> Optional[tuple]:
        """获取坐标"""
        from core import parse_dms_coordinate
        
        if not self.ident_column or self.ident_column not in self.df.columns:
            return None
        
        rows = self.df[self.df[self.ident_column].astype(str).str.strip() == str(ident).strip()]
        if rows.empty:
            return None
        
        row = rows.iloc[0]
        
        if not self.lat_column or not self.lon_column:
            return None
        
        if pd.isna(row[self.lat_column]) or pd.isna(row[self.lon_column]):
            return None
        
        lat = parse_dms_coordinate(row[self.lat_column])
        lon = parse_dms_coordinate(row[self.lon_column])
        
        if lat is not None and lon is not None:
            return lat, lon
        return None
    
    def get_all_idents(self) -> list:
        """获取所有标识列表"""
        if not self.ident_column or self.ident_column not in self.df.columns:
            return []
        return sorted([x for x in self.df[self.ident_column].dropna().unique() if x and str(x).strip()])
