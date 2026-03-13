import streamlit as st
import pandas as pd
from openai import OpenAI
import json

# ================= 页面配置 =================
st.set_page_config(page_title="AI 学术综述生成器", layout="wide")
st.title("📚 AI 高级学术文献综述生成系统")
st.markdown("支持100+篇文献输入，对标 *Molecular Plant* 等高水平期刊风格。")

# ================= API 配置 =================
# 建议使用 DeepSeek 或 Kimi 的 API，不仅便宜且长文本能力出色
API_KEY = st.sidebar.text_input("请输入大模型 API Key", type="password")
BASE_URL = st.sidebar.text_input("请输入 API Base URL", value="https://api.deepseek.com")

if not API_KEY:
    st.warning("👈 请在左侧输入API Key以启动应用。")
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ================= 文件上传 =================
st.subheader("1. 上传文献数据")
st.markdown("请上传包含以下列的 CSV 文件：`ID, Year, Author, Title, Journal, DOI, Abstract`")
uploaded_file = st.file_uploader("", type="csv")

if uploaded_file is not None:
    # 尝试使用多种编码格式读取文件，防止 UnicodeDecodeError
    try:
        # 1. 尝试带有 BOM 的 UTF-8（Windows Excel 常用）
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    except UnicodeDecodeError:
        try:
            # 2. 尝试 GBK 编码（中文 Windows 系统常用）
            uploaded_file.seek(0) # 重置文件指针到开头
            df = pd.read_csv(uploaded_file, encoding='gbk')
        except UnicodeDecodeError:
            # 3. 尝试 Latin-1 或 ISO 编码（PubMed 等海外数据库常用）
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='latin1', on_bad_lines='skip')
            
    st.write(f"✅ 成功加载 {len(df)} 篇文献，预览如下：")
    st.dataframe(df.head(3))

    if st.button("🚀 开始一键生成高质量综述"):
        # 预处理数据：转为JSON供大模型阅读
        docs_json = df.to_json(orient='records')
        
        with st.spinner('AI 正在深度研读文献并提取5大核心要素，请耐心等待（约需2-5分钟）...'):
            
            # 构建强大的系统提示词，强制规范AI行为
            system_prompt = """
            你是一位国际顶尖的生物学/植物学领域的资深科学家。你需要根据用户提供的文献JSON数据，撰写一篇高质量的学术综述（风格对标 Molecular Plant）。
            
            【核心任务与要求】
            1. 数据提炼：隐式提取每篇文献的核心科学问题、观点、方法、结论和展望。
            2. 逻辑框架：严格按照“摘要 -> 引言(研究背景) -> 正文(核心进展与分类) -> 现存争议 -> 未来方向”展开结构。
            3. 学术规范：
               - 必须极度客观，严禁主观臆断和空泛表达。
               - 按研究主题串联，绝对不要写成文献的流水账罗列。
               - 优先突出近三年（Year >= 2021）的研究成果。
            4. 引用规则：正文中每一次提及他人研究，必须在句末使用 [ID] 标注。
            5. 参考文献：在全文最后，必须单列【References】章节，按格式输出：“[ID] 作者. 标题. 期刊. 发表年份. DOI.”
            """
            
            user_prompt = f"请阅读以下 {len(df)} 篇文献的数据，并直接输出完整的 Markdown 格式综述初稿：\n\n{docs_json}"

            try:
                # 调用大模型（设置较低的 temperature 以保证客观性和严谨性）
                response = client.chat.completions.create(
                    model="deepseek-chat", # 根据您的API提供商替换模型名称，如 gpt-4o, claude-3-5-sonnet
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2, # 核心：0.2代表极低的随机性，最大程度避免幻觉
                    max_tokens=8000
                )
                
                review_content = response.choices[0].message.content
                
                st.success("🎉 综述初稿生成完毕！")
                st.markdown("### 📝 综述内容预览")
                st.markdown(review_content)
                
                # 提供 Markdown 下载功能
                st.download_button(
                    label="💾 下载综述初稿 (Markdown格式)",
                    data=review_content,
                    file_name="Literature_Review.md",
                    mime="text/markdown"
                )
                
            except Exception as e:

                st.error(f"生成过程中出现错误: {e}")
