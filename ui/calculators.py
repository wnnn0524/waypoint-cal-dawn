import streamlit as st
from core import (
    dms2deg, deg2dms, normalize_az,
    format_degrees_as_dms,
    vincenty_forward, vincenty_inverse,
    meters_to_nautical_miles, nautical_miles_to_meters,
    bearing_bearing_intersection_geo,
    segment_segment_intersection_geo,
    segment_bearing_intersection_geo,
    circle_bearing_intersection_geo,
    circle_circle_intersection_geo
)


def _validated_number(label, default, min_val, max_val, step, key):
    """无 +/- 按钮的数字输入，带范围/格式校验"""
    default_str = str(int(default) if isinstance(default, float) and default == int(default) else default)
    raw = st.text_input(label, value=default_str, key=key, label_visibility="visible")
    try:
        if isinstance(default, int):
            val = int(raw)
        else:
            val = float(raw)
        if val < min_val or val > max_val:
            st.caption(f"范围 {min_val}~{max_val}")
        return val
    except (ValueError, TypeError):
        st.caption(f"请输入有效数字")
        return default


def format_result(lat, lon):
    dms_str = format_degrees_as_dms(lat, lon)
    parts = dms_str.split('，')
    return f"**纬度**：{parts[0]} | **经度**：{parts[1]} | **十进制度**：{lat:.6f}, {lon:.6f}"


def get_coords_with_ref(label, key_prefix, data_tables, default_lat_d=30, default_lon_d=120):
    st.write(f"**{label}**")
    
    # 检查是否有引用的坐标
    if 'ref_coords' in st.session_state and st.session_state['ref_coords']:
        ref_coords = st.session_state['ref_coords']
        ref_record_name = st.session_state.get('ref_record_name', '')
        
        st.info(f"📍 已引用来自记录「{ref_record_name}」的坐标")
        
        # 如果只有一个坐标，直接使用
        if len(ref_coords) == 1:
            lat, lon = ref_coords[0]['lat'], ref_coords[0]['lon']
            st.write(f"引用坐标：{format_result(lat, lon)}")
            
            # 提供清除引用按钮
            if st.button(f"清除引用", key=f"{key_prefix}_clear_ref"):
                
                del st.session_state['ref_coords']
                del st.session_state['ref_record_name']
                st.rerun()
            
            return lat, lon, True, {"source": "record_ref", "record": ref_record_name}
        
        # 如果有多个坐标，提供选择
        coord_options = [f"{c['source']}：{format_result(c['lat'], c['lon'])}" for c in ref_coords]
        selected_idx = st.selectbox("选择要使用的坐标", range(len(coord_options)), format_func=lambda i: coord_options[i], key=f"{key_prefix}_ref_select")
        
        lat, lon = ref_coords[selected_idx]['lat'], ref_coords[selected_idx]['lon']
        st.write(f"引用坐标：{format_result(lat, lon)}")
        
        if st.button(f"清除引用", key=f"{key_prefix}_clear_ref"):
            del st.session_state['ref_coords']
            del st.session_state['ref_record_name']
            st.rerun()
        
        return lat, lon, True, {"source": "record_ref", "record": ref_record_name}
    
    # 坐标输入方式选择
    input_method = st.radio("坐标来源", ["手动输入", "引用Excel数据", "引用保存记录"], key=f"{key_prefix}_input_method", horizontal=True)
    
    if input_method == "引用保存记录":
        from ui.history import load_records
        records = st.session_state.get('records', load_records())
        
        if not records:
            st.warning("暂无保存的记录")
            return None, None, False, None
        else:
            # 构建选择列表
            record_options = [f"{r['name']} ({r['type']})" for r in records]
            selected_record_idx = st.selectbox("选择记录", range(len(record_options)), format_func=lambda i: record_options[i], key=f"{key_prefix}_record_select")
            
            selected_record = records[selected_record_idx]
            output = selected_record['output']
            
            # 提取坐标
            coords_to_ref = []
            if 'intersection_points' in output and output['intersection_points']:
                for pt in output['intersection_points']:
                    if pt and 'lat' in pt and 'lon' in pt:
                        coords_to_ref.append({'lat': pt['lat'], 'lon': pt['lon'], 'source': '交点'})
            elif 'intersection_point' in output and output['intersection_point']:
                pt = output['intersection_point']
                if 'lat' in pt and 'lon' in pt:
                    coords_to_ref.append({'lat': pt['lat'], 'lon': pt['lon'], 'source': '交会点'})
            elif 'end_point' in output:
                pt = output['end_point']
                if 'lat' in pt and 'lon' in pt:
                    coords_to_ref.append({'lat': pt['lat'], 'lon': pt['lon'], 'source': '终点'})
            elif 'result_point' in output:
                pt = output['result_point']
                if 'lat' in pt and 'lon' in pt:
                    coords_to_ref.append({'lat': pt['lat'], 'lon': pt['lon'], 'source': '结果点'})
            
            if coords_to_ref:
                if len(coords_to_ref) == 1:
                    lat, lon = coords_to_ref[0]['lat'], coords_to_ref[0]['lon']
                    st.write(f"📍 {coords_to_ref[0]['source']}：{format_result(lat, lon)}")
                    return lat, lon, True, {"source": "record_ref", "record": selected_record['name']}
                else:
                    coord_options = [f"{c['source']}：{format_result(c['lat'], c['lon'])}" for c in coords_to_ref]
                    selected_idx = st.selectbox("选择坐标", range(len(coord_options)), format_func=lambda i: coord_options[i], key=f"{key_prefix}_coord_select")
                    lat, lon = coords_to_ref[selected_idx]['lat'], coords_to_ref[selected_idx]['lon']
                    st.write(f"📍 {coords_to_ref[selected_idx]['source']}：{format_result(lat, lon)}")
                    return lat, lon, True, {"source": "record_ref", "record": selected_record['name']}
            else:
                st.warning("该记录中没有可用的坐标")
                return None, None, False, None
    
    elif input_method == "引用Excel数据":
        data_tables = st.session_state.get('data_tables')
        if not data_tables:
            st.warning("请先在侧边栏上传Excel文件")
            return None, None, False, None
            
        table_type = st.selectbox("选择数据表", ["Navaid", "Runway", "Waypoint"], key=f"{key_prefix}_table")

        if table_type == "Navaid" and "Navaid" in data_tables:
            navaid_data = data_tables["Navaid"]
            
            # 使用新的NavaidData接口
            available_tables = []
            if navaid_data.has_ident_table():
                available_tables.append("Ident表")
            if navaid_data.has_locid_table():
                available_tables.append("LocID表")
            
            if available_tables:
                selected_table = st.selectbox("选择子表", available_tables, key=f"{key_prefix}_navaid_table")
                
                use_loc = (selected_table == "LocID表")
                idents = navaid_data.get_all_idents(use_loc=use_loc)
                
                if idents:
                    ident = st.selectbox(f"选择{selected_table[:-1]}", sorted(idents), key=f"{key_prefix}_ident")
                    coord = navaid_data.get_coordinate(ident, use_loc=use_loc)
                    
                    if coord:
                        lat, lon = coord
                        st.write(f"引用坐标：{format_result(lat, lon)}")
                        return lat, lon, True, {"table": "Navaid", "sub_table": selected_table, "ident": ident}
                    else:
                        st.warning(f"未找到 {ident} 的有效坐标")
                        return None, None, False, None
                else:
                    st.warning(f"{selected_table}中没有找到有效的标识")
                    return None, None, False, None
            else:
                st.warning("Navaid表结构不符合预期，未找到Ident表或LocID表")
                return None, None, False, None

        elif table_type == "Runway" and "Runway" in data_tables:
            runway_data = data_tables["Runway"]
            
            idents = runway_data.get_all_idents()
            if idents:
                ident = st.selectbox("选择跑道标识", sorted(idents), key=f"{key_prefix}_ident")
                coord = runway_data.get_coordinate(ident)
                
                if coord:
                    lat, lon = coord
                    st.write(f"引用坐标：{format_result(lat, lon)}")
                    return lat, lon, True, {"table": "Runway", "ident": ident}
                else:
                    st.warning(f"未找到 {ident} 的有效坐标")
                    return None, None, False, None
            else:
                st.warning("Runway表中没有找到有效的标识")
                return None, None, False, None

        elif table_type == "Waypoint" and "Waypoint" in data_tables:
            waypoint_data = data_tables["Waypoint"]
            
            idents = waypoint_data.get_all_idents()
            if idents:
                ident = st.selectbox("选择标识", sorted(idents), key=f"{key_prefix}_ident")
                coord = waypoint_data.get_coordinate(ident)
                
                if coord:
                    lat, lon = coord
                    st.write(f"引用坐标：{format_result(lat, lon)}")
                    return lat, lon, True, {"table": "Waypoint", "ident": ident}
                else:
                    st.warning(f"未找到 {ident} 的有效坐标")
                    return None, None, False, None
            else:
                st.warning("Waypoint表中没有找到有效的标识")
                return None, None, False, None

        else:
            st.warning(f"{table_type} 表为空或不存在")
            return None, None, False, None
    
    else:  # 手动输入
        row_lat = st.columns([0.6, 1.2, 1.2, 1.2])
        with row_lat[0]:
            lat_dir = st.selectbox("N/S", ["N", "S"], key=f"{key_prefix}_lat_dir", label_visibility="visible")
        with row_lat[1]:
            lat_d = _validated_number("纬度°", default_lat_d, 0, 90, 1, f"{key_prefix}_lat_d")
        with row_lat[2]:
            lat_m = _validated_number("′", 0, 0, 59, 1, f"{key_prefix}_lat_m")
        with row_lat[3]:
            lat_s = _validated_number("″", 0.0, -0.01, 60.0, 0.0001, f"{key_prefix}_lat_s")
        
        row_lon = st.columns([0.6, 1.2, 1.2, 1.2])
        with row_lon[0]:
            lon_dir = st.selectbox("E/W", ["E", "W"], key=f"{key_prefix}_lon_dir", label_visibility="visible")
        with row_lon[1]:
            lon_d = _validated_number("经度°", default_lon_d, 0, 180, 1, f"{key_prefix}_lon_d")
        with row_lon[2]:
            lon_m = _validated_number("′", 0, 0, 59, 1, f"{key_prefix}_lon_m")
        with row_lon[3]:
            lon_s = _validated_number("″", 0.0, -0.01, 60.0, 0.0001, f"{key_prefix}_lon_s")

        lat = dms2deg(lat_d, lat_m, lat_s, lat_dir)
        lon = dms2deg(lon_d, lon_m, lon_s, lon_dir)
        return lat, lon, False, {"lat_dir": lat_dir, "lat_d": lat_d, "lat_m": lat_m, "lat_s": lat_s,
                                 "lon_dir": lon_dir, "lon_d": lon_d, "lon_m": lon_m, "lon_s": lon_s}


def forward_calculator(data_tables):
    st.subheader("大地正算 (Forward)")
    col1, col2 = st.columns(2)
    with col1:
        lat1, lon1, _, ref_info1 = get_coords_with_ref("起点坐标", "fwd", data_tables)
    with col2:
        az_type = st.radio("方位角类型", ["真方位", "磁方位"], key="fwd_az_type")
        az12 = st.number_input("方位角 (°)", value=45.0, min_value=0.0, max_value=360.0, step=0.1, key="fwd_az")
        declination = st.number_input("磁偏角 (东偏为正，°)", value=0.0, step=0.1, key="fwd_decl")
        dist_unit = st.radio("距离单位", ["米", "海里"], key="fwd_dist_unit")
        dist_value = st.number_input("距离", value=5.3996, min_value=0.0, step=0.0001, key="fwd_dist")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="fwd_calc"):
        if lat1 is None or lon1 is None:
            with result_placeholder.container():
                st.error("请输入有效的起点坐标")
            return
            
        if az_type == "磁方位":
            true_az = normalize_az(az12 + declination)
        else:
            true_az = az12
        if dist_unit == "海里":
            distance = nautical_miles_to_meters(dist_value)
        else:
            distance = dist_value
        lat2, lon2 = vincenty_forward(lat1, lon1, true_az, distance)
        
        with result_placeholder.container():
            st.success(f"**终点坐标：**")
            st.write(format_result(lat2, lon2))
            st.write(f"**使用的真方位角**：{true_az:.2f}°")
            st.write(f"**输入距离**：{dist_value} {dist_unit} = {distance:.2f} 米")
        
        st.session_state['fwd_result'] = {
            'lat2': lat2,
            'lon2': lon2,
            'true_az': true_az,
            'dist_value': dist_value,
            'dist_unit': dist_unit,
            'distance': distance,
            'input_data': {
                'start_point': {'lat': lat1, 'lon': lon1, 'ref_info': ref_info1},
                'az_type': az_type,
                'azimuth': az12,
                'declination': declination,
                'dist_unit': dist_unit,
                'distance': dist_value
            }
        }
    
    if 'fwd_result' in st.session_state:
        result = st.session_state['fwd_result']
        record_name = st.text_input("保存记录名称", value="", key="fwd_record_name")
        if st.button("保存计算记录", key="fwd_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Forward',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'end_point': {'lat': result['lat2'], 'lon': result['lon2']},
                    'true_azimuth': result['true_az'],
                    'distance_meters': result['distance']
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['fwd_result']


def inverse_calculator(data_tables):
    st.subheader("大地反算 (Inverse)")
    col1, col2 = st.columns(2)
    with col1:
        lat1, lon1, _, ref_info1 = get_coords_with_ref("起点坐标", "inv1", data_tables)
    with col2:
        lat2, lon2, _, ref_info2 = get_coords_with_ref("终点坐标", "inv2", data_tables, default_lat_d=30, default_lon_d=120)
    az_output_type = st.radio("输出方位角类型", ["真方位", "磁方位"], key="inv_az_type")
    declination = st.number_input("磁偏角 (东偏为正，°)", value=0.0, step=0.1, key="inv_decl")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="inv_calc"):
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        dist, az12, az21 = vincenty_inverse(lat1, lon1, lat2, lon2)
        if az_output_type == "磁方位":
            az12 = normalize_az(az12 - declination)
            az21 = normalize_az(az21 - declination)
        
        with result_placeholder.container():
            st.success(f"**计算结果：**")
            st.write(f"**距离**：{meters_to_nautical_miles(dist):.4f} 海里 = {dist:.2f} 米")
            st.write(f"**正方位角 (1→2)**：{az12:.6f}°")
            st.write(f"**反方位角 (2→1)**：{az21:.6f}°")
        
        st.session_state['inv_result'] = {
            'distance': dist,
            'az12': az12,
            'az21': az21,
            'az_output_type': az_output_type,
            'input_data': {
                'start_point': {'lat': lat1, 'lon': lon1, 'ref_info': ref_info1},
                'end_point': {'lat': lat2, 'lon': lon2, 'ref_info': ref_info2},
                'az_output_type': az_output_type,
                'declination': declination
            }
        }
    
    if 'inv_result' in st.session_state:
        result = st.session_state['inv_result']
        record_name = st.text_input("保存记录名称", value="", key="inv_record_name")
        if st.button("保存计算记录", key="inv_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Inverse',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'distance_meters': result['distance'],
                    'distance_nm': meters_to_nautical_miles(result['distance']),
                    'forward_azimuth': result['az12'],
                    'backward_azimuth': result['az21']
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['inv_result']


def segment_segment_calculator(data_tables):
    st.subheader("射线与射线交会 (Seg/Seg)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**射线1：A → B**")
        latA, lonA, _, ref_infoA = get_coords_with_ref("点A", "ss_A", data_tables)
        latB, lonB, _, ref_infoB = get_coords_with_ref("点B", "ss_B", data_tables, default_lat_d=30, default_lon_d=120)
    with col2:
        st.write("**射线2：C → D**")
        latC, lonC, _, ref_infoC = get_coords_with_ref("点C", "ss_C", data_tables, default_lat_d=30, default_lon_d=119)
        latD, lonD, _, ref_infoD = get_coords_with_ref("点D", "ss_D", data_tables, default_lat_d=30, default_lon_d=121)
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="ss_calc"):
        if latA is None or lonA is None or latB is None or lonB is None or latC is None or lonC is None or latD is None or lonD is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        lat_intersect, lon_intersect = segment_segment_intersection_geo(latA, lonA, latB, lonB, latC, lonC, latD, lonD)
        
        with result_placeholder.container():
            if lat_intersect is not None:
                st.success(f"**交会点：**")
                st.write(format_result(lat_intersect, lon_intersect))
            else:
                st.warning("两条射线不相交（平行或交点在起点后方）")
        
        st.session_state['ss_result'] = {
            'lat_intersect': lat_intersect,
            'lon_intersect': lon_intersect,
            'input_data': {
                'pointA': {'lat': latA, 'lon': lonA, 'ref_info': ref_infoA},
                'pointB': {'lat': latB, 'lon': lonB, 'ref_info': ref_infoB},
                'pointC': {'lat': latC, 'lon': lonC, 'ref_info': ref_infoC},
                'pointD': {'lat': latD, 'lon': lonD, 'ref_info': ref_infoD}
            }
        }
    
    if 'ss_result' in st.session_state:
        result = st.session_state['ss_result']
        record_name = st.text_input("保存记录名称", value="", key="ss_record_name")
        if st.button("保存计算记录", key="ss_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Seg/Seg',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'intersection_point': {'lat': result['lat_intersect'], 'lon': result['lon_intersect']} if result['lat_intersect'] else None
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['ss_result']


def bearing_bearing_calculator(data_tables):
    st.subheader("方位角与方位角交会 (Brg/Brg)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**方位线1**")
        lat1, lon1, _, ref_info1 = get_coords_with_ref("起点", "bb_1", data_tables)
        az1_type = st.radio("方位角1类型", ["真方位", "磁方位"], key="bb_az1_type", horizontal=True)
        az1 = st.number_input("方位角1 (°)", value=45.0, min_value=0.0, max_value=360.0, step=0.1, key="bb_az1")
        decl1 = st.number_input("磁偏角1 (东偏为正，°)", value=0.0, step=0.1, key="bb_decl1")
    with col2:
        st.write("**方位线2**")
        lat2, lon2, _, ref_info2 = get_coords_with_ref("起点", "bb_2", data_tables, default_lat_d=30, default_lon_d=120)
        az2_type = st.radio("方位角2类型", ["真方位", "磁方位"], key="bb_az2_type", horizontal=True)
        az2 = st.number_input("方位角2 (°)", value=315.0, min_value=0.0, max_value=360.0, step=0.1, key="bb_az2")
        decl2 = st.number_input("磁偏角2 (东偏为正，°)", value=0.0, step=0.1, key="bb_decl2")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="bb_calc"):
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
        
        true_az1 = normalize_az(az1 + decl1) if az1_type == "磁方位" else az1
        true_az2 = normalize_az(az2 + decl2) if az2_type == "磁方位" else az2
        
        lat_intersect, lon_intersect = bearing_bearing_intersection_geo(lat1, lon1, true_az1, lat2, lon2, true_az2)
        
        with result_placeholder.container():
            if lat_intersect is not None:
                st.success(f"**交会点：**")
                st.write(format_result(lat_intersect, lon_intersect))
            else:
                st.warning("两条方位线平行，无交点")
        
        st.session_state['bb_result'] = {
            'lat_intersect': lat_intersect,
            'lon_intersect': lon_intersect,
            'input_data': {
                'point1': {'lat': lat1, 'lon': lon1, 'ref_info': ref_info1},
                'azimuth1': az1,
                'az1_type': az1_type,
                'declination1': decl1,
                'true_az1': true_az1,
                'point2': {'lat': lat2, 'lon': lon2, 'ref_info': ref_info2},
                'azimuth2': az2,
                'az2_type': az2_type,
                'declination2': decl2,
                'true_az2': true_az2
            }
        }
    
    if 'bb_result' in st.session_state:
        result = st.session_state['bb_result']
        record_name = st.text_input("保存记录名称", value="", key="bb_record_name")
        if st.button("保存计算记录", key="bb_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Brg/Brg',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'intersection_point': {'lat': result['lat_intersect'], 'lon': result['lon_intersect']} if result['lat_intersect'] else None
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['bb_result']


def segment_distance_calculator(data_tables):
    st.subheader("射线与距离交会 (Seg Dist)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**射线：点A -> 点B**")
        latA, lonA, _, ref_infoA = get_coords_with_ref("起点A", "sd_A", data_tables)
        latB, lonB, _, ref_infoB = get_coords_with_ref("方向点B", "sd_B", data_tables, default_lat_d=30, default_lon_d=120)
    with col2:
        st.write("**距离参数**")
        dist_unit = st.radio("距离单位", ["米", "海里"], key="sd_dist_unit")
        dist_value = st.number_input("距离（从A点出发）", value=5000.0, min_value=0.0, step=100.0, key="sd_dist")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="sd_calc"):
        if latA is None or lonA is None or latB is None or lonB is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        if dist_unit == "海里":
            distance = nautical_miles_to_meters(dist_value)
        else:
            distance = dist_value
        dist_ab, az_ab, az_ba = vincenty_inverse(latA, lonA, latB, lonB)
        lat_result, lon_result = vincenty_forward(latA, lonA, az_ab, distance)
        dist_ar, _, _ = vincenty_inverse(latA, lonA, lat_result, lon_result)
        
        with result_placeholder.container():
            st.success(f"**计算结果：**")
            st.write(f"**线段信息：AB = {meters_to_nautical_miles(dist_ab):.4f} 海里 = {dist_ab:.2f} 米，方位角 A→B = {az_ab:.4f}°**")
            st.write(f"**计算结果：从A点出发，沿射线AB方向前进 {dist_value} {dist_unit} 到达：**")
            st.write(format_result(lat_result, lon_result))
            st.write(f"**验证距离：A→结果 = {meters_to_nautical_miles(dist_ar):.4f} 海里 = {dist_ar:.2f} 米**")
        
        st.session_state['sd_result'] = {
            'lat_result': lat_result,
            'lon_result': lon_result,
            'dist_ab': dist_ab,
            'az_ab': az_ab,
            'dist_ar': dist_ar,
            'input_data': {
                'pointA': {'lat': latA, 'lon': lonA, 'ref_info': ref_infoA},
                'pointB': {'lat': latB, 'lon': lonB, 'ref_info': ref_infoB},
                'dist_unit': dist_unit,
                'distance': dist_value
            }
        }
    
    if 'sd_result' in st.session_state:
        result = st.session_state['sd_result']
        record_name = st.text_input("保存记录名称", value="", key="sd_record_name")
        if st.button("保存计算记录", key="sd_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Ray Dist',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'result_point': {'lat': result['lat_result'], 'lon': result['lon_result']},
                    'AB_distance_meters': result['dist_ab'],
                    'AB_azimuth': result['az_ab'],
                    'AR_distance_meters': result['dist_ar']
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['sd_result']


def circle_bearing_calculator(data_tables):
    st.subheader("圆与方位角交会 (Cir/Brg)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**圆**")
        latC, lonC, _, ref_infoC = get_coords_with_ref("圆心", "cb_C", data_tables)
        radius_unit = st.radio("半径单位", ["米", "海里"], key="cb_radius_unit")
        radius_value = st.number_input("半径", value=8000.0, min_value=0.0, step=100.0, key="cb_radius")
    with col2:
        st.write("**方位线**")
        latP, lonP, _, ref_infoP = get_coords_with_ref("起点", "cb_P", data_tables, default_lat_d=30, default_lon_d=120)
        az_type = st.radio("方位角类型", ["真方位", "磁方位"], key="cb_az_type", horizontal=True)
        az = st.number_input("方位角 (°)", value=45.0, min_value=0.0, max_value=360.0, step=0.1, key="cb_az")
        declination = st.number_input("磁偏角 (东偏为正，°)", value=0.0, step=0.1, key="cb_decl")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="cb_calc"):
        if latC is None or lonC is None or latP is None or lonP is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        if radius_unit == "海里":
            radius = nautical_miles_to_meters(radius_value)
        else:
            radius = radius_value
        true_az = normalize_az(az + declination) if az_type == "磁方位" else az
        results = circle_bearing_intersection_geo(latC, lonC, radius, latP, lonP, true_az)
        
        with result_placeholder.container():
            if results:
                st.success(f"**找到 {len(results)} 个交会点：**")
                for i, (lat, lon) in enumerate(results, 1):
                    st.write(f"**交点{i}：**")
                    st.write(format_result(lat, lon))
            else:
                st.warning("未找到交会点")
        
        st.session_state['cb_result'] = {
            'results': results,
            'input_data': {
                'center': {'lat': latC, 'lon': lonC, 'ref_info': ref_infoC},
                'radius_unit': radius_unit,
                'radius': radius_value,
                'pointP': {'lat': latP, 'lon': lonP, 'ref_info': ref_infoP},
                'azimuth': az,
                'az_type': az_type,
                'declination': declination,
                'true_az': true_az
            }
        }
    
    if 'cb_result' in st.session_state:
        result = st.session_state['cb_result']
        record_name = st.text_input("保存记录名称", value="", key="cb_record_name")
        if st.button("保存计算记录", key="cb_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Cir/Brg',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'intersection_points': [{'lat': r[0], 'lon': r[1]} for r in result['results']]
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['cb_result']


def circle_circle_calculator(data_tables):
    st.subheader("圆与圆交会 (Cir/Cir)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**圆1**")
        latC1, lonC1, _, ref_infoC1 = get_coords_with_ref("圆心", "cc_C1", data_tables)
        radius1_unit = st.radio("半径单位", ["米", "海里"], key="cc_radius1_unit")
        radius1_value = st.number_input("半径", value=8000.0, min_value=0.0, step=100.0, key="cc_radius1")
    with col2:
        st.write("**圆2**")
        latC2, lonC2, _, ref_infoC2 = get_coords_with_ref("圆心", "cc_C2", data_tables, default_lat_d=30, default_lon_d=120)
        radius2_unit = st.radio("半径单位", ["米", "海里"], key="cc_radius2_unit")
        radius2_value = st.number_input("半径", value=8000.0, min_value=0.0, step=100.0, key="cc_radius2")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="cc_calc"):
        if latC1 is None or lonC1 is None or latC2 is None or lonC2 is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        if radius1_unit == "海里":
            r1 = nautical_miles_to_meters(radius1_value)
        else:
            r1 = radius1_value
        if radius2_unit == "海里":
            r2 = nautical_miles_to_meters(radius2_value)
        else:
            r2 = radius2_value
        results = circle_circle_intersection_geo(latC1, lonC1, r1, latC2, lonC2, r2)
        
        with result_placeholder.container():
            if results:
                st.success(f"**找到 {len(results)} 个交会点：**")
                for i, (lat, lon) in enumerate(results, 1):
                    st.write(f"**交点{i}：**")
                    st.write(format_result(lat, lon))
            else:
                st.warning("两圆不相交")
        
        st.session_state['cc_result'] = {
            'results': results,
            'input_data': {
                'center1': {'lat': latC1, 'lon': lonC1, 'ref_info': ref_infoC1},
                'radius1_unit': radius1_unit,
                'radius1': radius1_value,
                'center2': {'lat': latC2, 'lon': lonC2, 'ref_info': ref_infoC2},
                'radius2_unit': radius2_unit,
                'radius2': radius2_value
            }
        }
    
    if 'cc_result' in st.session_state:
        result = st.session_state['cc_result']
        record_name = st.text_input("保存记录名称", value="", key="cc_record_name")
        if st.button("保存计算记录", key="cc_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Cir/Cir',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'intersection_points': [{'lat': r[0], 'lon': r[1]} for r in result['results']]
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['cc_result']


def segment_bearing_calculator(data_tables):
    st.subheader("线段与方位角交会 (Seg/Brg)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**线段：A -> B**")
        latA, lonA, _, ref_infoA = get_coords_with_ref("点A", "sb_A", data_tables)
        latB, lonB, _, ref_infoB = get_coords_with_ref("点B", "sb_B", data_tables, default_lat_d=30, default_lon_d=120)
    with col2:
        st.write("**方位线**")
        latP, lonP, _, ref_infoP = get_coords_with_ref("起点", "sb_P", data_tables, default_lat_d=30, default_lon_d=119)
        az = st.number_input("方位角 (°)", value=90.0, min_value=0.0, max_value=360.0, step=0.1, key="sb_az")
    
    result_placeholder = st.empty()
    
    if st.button("计算", key="sb_calc"):
        if latA is None or lonA is None or latB is None or lonB is None or latP is None or lonP is None:
            with result_placeholder.container():
                st.error("请输入有效的坐标")
            return
            
        lat_intersect, lon_intersect = segment_bearing_intersection_geo(latA, lonA, latB, lonB, latP, lonP, az)
        
        with result_placeholder.container():
            if lat_intersect is not None:
                st.success(f"**交会点：**")
                st.write(format_result(lat_intersect, lon_intersect))
            else:
                st.warning("方位线与线段不相交")
        
        st.session_state['sb_result'] = {
            'lat_intersect': lat_intersect,
            'lon_intersect': lon_intersect,
            'input_data': {
                'pointA': {'lat': latA, 'lon': lonA, 'ref_info': ref_infoA},
                'pointB': {'lat': latB, 'lon': lonB, 'ref_info': ref_infoB},
                'pointP': {'lat': latP, 'lon': lonP, 'ref_info': ref_infoP},
                'azimuth': az
            }
        }
    
    if 'sb_result' in st.session_state:
        result = st.session_state['sb_result']
        record_name = st.text_input("保存记录名称", value="", key="sb_record_name")
        if st.button("保存计算记录", key="sb_save") and record_name.strip():
            record = {
                'name': record_name.strip(),
                'type': 'Seg/Brg',
                'timestamp': st.session_state.get('current_time', ''),
                'input': result['input_data'],
                'output': {
                    'intersection_point': {'lat': result['lat_intersect'], 'lon': result['lon_intersect']} if result['lat_intersect'] else None
                }
            }
            from ui.history import save_record
            save_record(record)
            st.success(f"记录 '{record_name}' 已保存！")
            del st.session_state['sb_result']