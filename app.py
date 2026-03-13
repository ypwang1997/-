import streamlit as st
import pandas as pd
from openai import OpenAI
import json

# ================= 1. 页面配置 =================
st.set_page_config(page_title="ReviewMaster Pro v2", layout="wide")
st.title("📚 ReviewMaster Pro v2: 高覆盖度学术综述生成器")

# 初始化状态
if 'review_draft' not in st.session_state: st.session_state.review_draft = ""
if 'eng_draft' not in st.session_state: st.session_state.eng_draft = ""

# ================= 2. 侧边栏配置 =================
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("Base URL", value="https://api.deepseek.com")
    model_name = st.selectbox("选择模型", ["deepseek-chat", "gpt-4o"])
    
    st.divider()
    uploaded_file = st.file_uploader("上传文献CSV (需含ID, Year, Author, Title, Journal, DOI, Abstract)", type="csv")
    
    docs_json = ""
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, encoding_errors='ignore')
            st.success(f"已加载 {len(df)} 篇文献")
            # 关键：确保 ID 被作为字符串处理，防止丢失
            docs_json = df.to_json(orient='records')
        except Exception as e:
            st.error(f"读取失败: {e}")

# ================= 3. 主界面：任务定义 =================
st.subheader("📝 任务定义")
col1, col2 = st.columns(2)
with col1:
    main_theme = st.text_input("综述主题", value="植物感应逆境的分子机制")
    target_words = st.number_input("目标字数 (建议 3000-5000)", value=3000)
with col2:
    custom_outline = st.text_area("大纲要求", placeholder="1.引言; 2.核心机制; 3.现存争议; 4.总结", height=100)

# ================= 4. 核心功能函数 =================
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

def ai_request(system_prompt, user_prompt):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=8000 # 尽可能设置高一些
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ================= 5. 操作流程 =================

tab1, tab2 = st.tabs(["🇨🇳 中文初稿生成与迭代", "🇺🇸 英文润色与 TiPS 风格转换"])

with tab1:
    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("🚀 生成高覆盖度初稿"):
        sys_msg = f"""你是一位资深学术作家。现有{len(df) if uploaded_file else 0}篇文献。
        【硬性要求】
        1. 覆盖度：必须尽可能在综述中体现所有提供的文献内容，不要轻易舍弃任何一篇。
        2. 引用格式：每一个观点后必须紧跟 [ID]，[ID]必须与输入数据的ID严格对应。
        3. 逻辑：按主题聚类，严禁写成流水账。
        4. 字数：目标{target_words}字。如果内容多，请详细展开每个研究的方法和结论。
        5. 文末列表：必须列出 References 章节，格式为 [ID] Author. Title. Journal. Year. DOI.
        6. 结构：{custom_outline}
        """
        user_msg = f"主题：{main_theme}\n数据：{docs_json}"
        st.session_state.review_draft = ai_request(sys_msg, user_msg)
        st.rerun()

    if col_btn2.button("⏬ 内容缺失？点击继续撰写"):
        sys_msg = "你是一篇长综述的撰写者。由于字数限制，你之前的输出中断了。请从你上次中断的地方（或未完成的章节）开始继续撰写，保持逻辑连贯，并最后补齐参考文献列表。"
        user_msg = f"这是你之前写的草稿，请继续完成未尽部分：\n{st.session_state.review_draft}"
        continuation = ai_request(sys_msg, user_msg)
        st.session_state.review_draft += f"\n\n{continuation}"
        st.rerun()

    if st.session_state.review_draft:
        st.text_area("中文稿编辑区", value=st.session_state.review_draft, height=500, key="zh_edit")
        
        # 局部修改功能
        feedback = st.chat_input("输入修改意见（例如：‘详细展开关于[5]号文献的研究方法’）")
        if feedback:
            res = ai_request("根据用户意见修改草稿，保持引用格式。", f"草稿：{st.session_state.review_draft}\n意见：{feedback}")
            st.session_state.review_draft = res
            st.rerun()

with tab2:
    st.markdown("### 🧬 Trends in Plant Science 风格转换")
    st.info("该功能将中文稿翻译为英文，并进行深度学术润色，强调“Trends（趋势）”和“Outstanding Questions”。")
    
    if st.button("🪄 开始翻译并进行 TiPS 级润色"):
        tips_sys = """You are a senior editor for 'Trends in Plant Science'. 
        Task: Translate and polish the provided Chinese review into English.
        Style Guide:
        1. Tone: Authoritative, forward-looking, and concise.
        2. Vocabulary: Use precise scientific verbs (e.g., 'orchestrates', 'elicits', 'recapitulates').
        3. Structure: Maintain the [ID] citations. Create a section named 'Concluding Remarks and Future Perspectives'.
        4. Special Requirement: Add a 'Box 1: Outstanding Questions' at the end based on the future directions.
        5. References: Ensure the [ID] list is preserved in the required format.
        """
        st.session_state.eng_draft = ai_request(tips_sys, st.session_state.review_draft)
        st.rerun()

    if st.session_state.eng_draft:
        st.text_area("英文终稿预览", value=st.session_state.eng_draft, height=500)
        st.download_button("📥 下载英文终稿 (.md)", st.session_state.eng_draft, file_name="Final_Review_TiPS_Style.md")

# ================= 6. 通用导出 =================
if st.session_state.review_draft:
    st.sidebar.download_button("📥 下载中文草稿 (.md)", st.session_state.review_draft, file_name="Chinese_Review.md")
