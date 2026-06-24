import streamlit as st
from datetime import datetime
import pandas as pd

from ui.calculators import (
    forward_calculator,
    inverse_calculator,
    segment_segment_calculator,
    bearing_bearing_calculator,
    segment_distance_calculator,
    circle_bearing_calculator,
    circle_circle_calculator,
    segment_bearing_calculator
)
from ui.history import show_history
from data.excel_reader import NavaidData, RunwayData, WaypointData


def load_excel_data(file):
    data_handlers = {}
    try:
        xls = pd.ExcelFile(file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            # 根据表名创建对应的处理器
            if sheet_name == "Navaid":
                data_handlers[sheet_name] = NavaidData(df)
            elif sheet_name == "Runway":
                data_handlers[sheet_name] = RunwayData(df)
            elif sheet_name == "Waypoint":
                data_handlers[sheet_name] = WaypointData(df)
            else:
                data_handlers[sheet_name] = df
        return data_handlers
    except Exception as e:
        st.error(f"读取Excel文件失败: {e}")
        return None


def main():
    st.set_page_config(page_title="COMPSYS 21 数据驱动计算", layout="wide")

    # 增大左侧边栏文字
    st.markdown("""
    <style>
    [data-testid="stSidebar"] * {
        font-size: 25px !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 26px !important;
    }
    [data-testid="stSidebar"] .stSubheader {
        font-size: 28px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("✈️ COMPSYS 21 坐标计算器 1.1")
    
    st.session_state['current_time'] = datetime.now().isoformat()
    
    with st.sidebar:
        page = st.radio("导航", ["🧮 计算器", "📖 使用说明", "📋 版本更新"], key="nav_page")
        
        if page == "🧮 计算器":
            st.subheader("📁 数据文件")
            uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
            
            if uploaded_file is not None:
                data_tables = load_excel_data(uploaded_file)
                if data_tables:
                    st.session_state['data_tables'] = data_tables
                    st.success(f"成功加载 {len(data_tables)} 个工作表")
                    st.write("可用表：")
                    for sheet in data_tables.keys():
                        st.write(f"- {sheet}")
            else:
                st.session_state.pop('data_tables', None)
                st.info("请上传Excel文件以启用数据引用功能")
    
    if page == "🧮 计算器":
        tabs = st.tabs([
            "Forward", "Inverse", "Seg/Seg", "Brg/Brg",
            "Seg Dist", "Cir/Brg", "Cir/Cir", "Seg/Brg", "历史记录"
        ])
        
        data_tables = st.session_state.get('data_tables', None)
        
        with tabs[0]:
            forward_calculator(data_tables)
        
        with tabs[1]:
            inverse_calculator(data_tables)
        
        with tabs[2]:
            segment_segment_calculator(data_tables)
        
        with tabs[3]:
            bearing_bearing_calculator(data_tables)
        
        with tabs[4]:
            segment_distance_calculator(data_tables)
        
        with tabs[5]:
            circle_bearing_calculator(data_tables)
        
        with tabs[6]:
            circle_circle_calculator(data_tables)
        
        with tabs[7]:
            segment_bearing_calculator(data_tables)
        
        with tabs[8]:
            show_history()
    
    elif page == "📖 使用说明":
        st.markdown("""## 📖 使用说明""")
        st.divider()
        st.markdown("""### 误差说明""")
        st.markdown("前五个计算器，Forward，Inverse，Seg/Seg，Brg/Brg，Seg Dist已经过三期验证，可使用。")
        st.markdown("C/B计算会与21计算器存在0.5秒误差。")
        st.divider()
        st.caption("（后续将补充完整的使用说明内容）")

    elif page == "📋 版本更新":
        st.markdown("""## 📋 版本更新""")
        st.divider()
        st.markdown("1、优化UI界面，新增了使用说明。")
        st.markdown("2、更新Cir/Brg计算精度，与21计算器的误差经测试在0.5秒以内。")
        st.divider()
        st.caption("（后续版本更新将在此记录）")


if __name__ == "__main__":
    main()