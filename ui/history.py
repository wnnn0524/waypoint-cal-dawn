import streamlit as st
import json
import os
from datetime import datetime
from core import meters_to_nautical_miles, format_degrees_as_dms


DEFAULT_RECORD_FILE = os.path.join(os.path.expanduser("~"), "compsys21_records.json")


def get_record_file():
    return st.session_state.get('record_file_path', DEFAULT_RECORD_FILE)


def load_records():
    try:
        with open(get_record_file(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_record(record):
    # 如果session_state中没有records，先从本地文件加载初始化
    if 'records' not in st.session_state:
        existing_records = load_records()
    else:
        # 创建副本以确保正确更新状态
        existing_records = list(st.session_state['records'])
    
    # 在现有列表中插入新记录
    existing_records.insert(0, record)
    if len(existing_records) > 100:
        existing_records = existing_records[:100]
    
    # 更新session_state
    st.session_state['records'] = existing_records


def format_result(lat, lon):
    dms_str = format_degrees_as_dms(lat, lon)
    parts = dms_str.split('，')
    return f"**纬度**：{parts[0]} | **经度**：{parts[1]} | **十进制度**：{lat:.6f}, {lon:.6f}"


def show_history():
    st.subheader("📋 历史记录")
    
    st.write("**文件操作：**")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        uploaded_file = st.file_uploader("📂 打开记录文件", type=['json'], key="open_record")
        if uploaded_file is not None:
            try:
                imported_records = json.load(uploaded_file)
                if isinstance(imported_records, list):
                    # 获取当前已有的记录（如果有）
                    current_records = st.session_state.get('records', [])
                    # 追加新记录（去重）
                    for record in imported_records:
                        # 通过名称和时间戳判断是否重复
                        exists = False
                        for existing in current_records:
                            if existing.get('name') == record.get('name') and existing.get('timestamp') == record.get('timestamp'):
                                exists = True
                                break
                        if not exists:
                            current_records.append(record)
                    # 更新状态
                    st.session_state['records'] = current_records
                    st.success(f"成功追加 {len(imported_records)} 条记录！")
                else:
                    st.error("文件格式不正确")
            except Exception as e:
                st.error(f"加载失败：{e}")
    with col2:
        records = st.session_state.get('records', load_records())
        if records:
            json_str = json.dumps(records, ensure_ascii=False, indent=2)
            st.download_button(
                label="💾 保存记录文件",
                data=json_str,
                file_name=f"compsys21_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="save_record"
            )
    with col3:
        if st.button("🗑️ 清空记录", key="clear_records"):
            st.session_state['records'] = []
            st.rerun()
    with col4:
        if st.button("📖 从本地加载", key="load_local"):
            # 获取当前已有的记录（如果有）
            current_records = st.session_state.get('records', [])
            # 加载本地文件记录
            local_records = load_records()
            # 追加并去重
            for record in local_records:
                exists = False
                for existing in current_records:
                    if existing.get('name') == record.get('name') and existing.get('timestamp') == record.get('timestamp'):
                        exists = True
                        break
                if not exists:
                    current_records.append(record)
            st.session_state['records'] = current_records
            st.success(f"已从本地追加 {len(local_records)} 条记录！")
            st.rerun()
    
    st.divider()
    
    records = st.session_state.get('records', load_records())
    
    if not records:
        st.info("暂无保存的记录，先去做一些计算并保存吧！")
    else:
        st.write(f"共 {len(records)} 条记录")
        
        for idx, record in enumerate(records):
            with st.expander(f"📌 {record['name']} - {record['type']} ({record['timestamp'][:19].replace('T', ' ')})"):
                st.write("**输入参数：**")
                for key, value in record['input'].items():
                    if isinstance(value, dict) and 'lat' in value and 'lon' in value:
                        lat, lon = value['lat'], value['lon']
                        st.write(f"- {key}：{format_result(lat, lon)}")
                    elif isinstance(value, dict) and 'ref_info' in value:
                        st.write(f"- {key}：{value}")
                    else:
                        st.write(f"- {key}：{value}")
                
                st.write("**输出结果：**")
                output = record['output']
                if 'intersection_points' in output and output['intersection_points']:
                    for i, pt in enumerate(output['intersection_points'], 1):
                        if pt:
                            st.write(f"- 交点{i}：{format_result(pt['lat'], pt['lon'])}")
                        else:
                            st.write(f"- 交点{i}：无")
                elif 'intersection_point' in output and output['intersection_point']:
                    pt = output['intersection_point']
                    st.write(f"- 交会点：{format_result(pt['lat'], pt['lon'])}")
                elif 'end_point' in output:
                    pt = output['end_point']
                    st.write(f"- 终点：{format_result(pt['lat'], pt['lon'])}")
                elif 'result_point' in output:
                    pt = output['result_point']
                    st.write(f"- 结果点：{format_result(pt['lat'], pt['lon'])}")
                
                for key, value in output.items():
                    if key not in ['intersection_points', 'intersection_point', 'end_point', 'result_point']:
                        if 'distance' in key.lower() and '_meters' in key:
                            st.write(f"- {key}：{value:.2f} 米 = {meters_to_nautical_miles(value):.4f} 海里")
                        elif isinstance(value, float):
                            st.write(f"- {key}：{value:.6f}")
                        else:
                            st.write(f"- {key}：{value}")
                
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    json_str = json.dumps(record, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📤 导出记录",
                        data=json_str,
                        file_name=f"{record['name']}.json",
                        mime="application/json",
                        key=f"export_{idx}"
                    )
                with col_b:
                    if st.button(f"📍 引用坐标", key=f"ref_{idx}"):
                        # 尝试提取输出中的坐标
                        output = record['output']
                        coords_to_ref = []
                        
                        # 从输出结果中提取坐标
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
                            st.session_state['ref_coords'] = coords_to_ref
                            st.session_state['ref_record_name'] = record['name']
                            st.success(f"已引用坐标：{coords_to_ref[0]['source']} - {format_result(coords_to_ref[0]['lat'], coords_to_ref[0]['lon'])}")
                            st.rerun()
                        else:
                            st.warning("该记录中没有可引用的坐标")
                
                with col_c:
                    if st.button(f"🗑️ 删除", key=f"del_{idx}"):
                        records.pop(idx)
                        st.session_state['records'] = records
                        st.rerun()