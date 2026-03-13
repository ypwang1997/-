import streamlit as st
import pandas as pd
from openai import OpenAI
import json

# ================= 1. 页面配置与初始化 =================
st.set_page_config(page_title="ReviewMaster Pro - 深度交互综述生成器", layout="wide")
st.title("🧪 ReviewMaster Pro: 高级交互式文献综述系统")

# 初始化会话状态，用于存储生成的草稿和历史记录
if 'review_draft' not in st.session_state:
    st.session_state.review_draft = ""
if 'history' not in st.session_state:
    st.session_state.history = []

# ================= 2. 侧边栏：API 配置与文件上传 =================
with st.sidebar:
    st.header("⚙️ 配置中心")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("Base URL", value="https://api.deepseek.com")
    
    st.divider()
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader("上传文献CSV (需包含ID, Year, Title, Abstract等)", type="csv")
    
    if uploaded_file:
        try:
            # 使用兼容模式读取
            df = pd.read_csv(uploaded_file, encoding_errors='ignore')
            st.success(f"已加载 {len(df)} 篇文献")
            docs_json = df.to_json(orient='records')
        except Exception as e:
            st.error(f"读取失败: {e}")
            docs_json = None

# ================= 3. 主界面：自定义大纲配置 =================
st.subheader("📝 第一步：定义您的综述结构")
col1, col2 = st.columns([1, 1])

with col1:
    main_theme = st.text_input("综述总主题", placeholder="例如：植物单细胞转录组学在逆境响应中的应用")
    total_words = st.number_input("期望总字数（概估）", min_value=500, max_value=10000, value=3000)

with col2:
    custom_outline = st.text_area(
        "输入自定义大纲及各部分要求", 
        height=150,
        placeholder="格式建议：\n1. 引言 (约500字)：强调XX研究的紧迫性\n2. 核心技术进展 (约1000字)：重点分析XX方法\n3. 现存瓶颈 (约800字)...\n4. 未来展望..."
    )

# ================= 4. 核心逻辑：生成与迭代 =================

client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

def call_ai(prompt, system_instruction):
    """通用 AI 调用函数"""
    with st.spinner("AI 正在深度思考并撰写中..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat", # 或 gpt-4o
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"生成出错: {e}")
            return None

# --- 按钮：初稿生成 ---
if st.button("🚀 根据自定义大纲生成初稿"):
    if not (api_key and docs_json and custom_outline):
        st.warning("请检查：API Key、文献文件和大纲是否均已准备就绪？")
    else:
        system_instruction = f"""
        你是一位顶尖学术作家（参考 Molecular Plant 风格）。
        【核心任务】基于提供的文献JSON数据，严格按照用户定义的【大纲】和【字数要求】撰写综述。
        【学术规范】
        1. 必须在观点后标注 [ID]。
        2. 结构逻辑：{custom_outline}。总字数目标：{total_words}字左右。
        3. 优先突出近三年研究，严禁主观臆断。
        4. 格式：摘要 -> 引言 -> 正文 -> 参考文献(列表格式：[ID] 作者. 标题. 期刊. 发表年份. DOI)。
        """
        user_prompt = f"主题：{main_theme}\n\n文献数据：{docs_json}"
        
        result = call_ai(user_prompt, system_instruction)
        if result:
            st.session_state.review_draft = result
            st.success("初稿已生成！请在下方查看并提出修改意见。")

# --- 展示与修改区 ---
if st.session_state.review_draft:
    st.divider()
    st.subheader("📄 综述预览与实时优化")
    
    # 使用文本区域显示，方便用户直接看到当前版本
    current_draft = st.text_area("当前草稿内容", value=st.session_state.review_draft, height=400)
    
    # 修改反馈区
    feedback = st.chat_input("针对某一部分提出修改意见（例如：'请在第二部分增加更多关于XX技术的争议讨论'）")
    
    if feedback:
        modify_instruction = f"""
        你是一位严谨的学术编辑。现在有一篇综述草稿和原始文献数据。
        【任务】根据用户的反馈意见对草稿进行局部优化或重写。
        【要求】保持原有的 [ID] 引用格式、学术语调和参考文献列表。
        【用户反馈】：{feedback}
        """
        modify_prompt = f"当前草稿：\n{st.session_state.review_draft}\n\n原始文献数据：{docs_json}"
        
        updated_result = call_ai(modify_prompt, modify_instruction)
        if updated_result:
            st.session_state.review_draft = updated_result
            st.rerun() # 重新运行以更新界面内容

# ================= 5. 导出功能 =================
if st.session_state.review_draft:
    st.divider()
    st.subheader("📥 最终确认与导出")
    
    final_text = st.session_state.review_draft
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="💾 导出为 Markdown (.md)",
            data=final_text,
            file_name=f"{main_theme}_综述.md",
            mime="text/markdown"
        )
    with col_dl2:
        # 提供简单的文本导出
        st.download_button(
            label="📄 导出为 纯文本 (.txt)",
            data=final_text,
            file_name=f"{main_theme}_综述.txt",
            mime="text/plain"
        )

    st.info("💡 提示：Markdown 格式可以使用 Typora 或 Word 直接打开，并保留良好的标题层级。")
