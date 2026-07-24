import shutil
import sys
import pysqlite3
sys.modules["sqlite3"] = pysqlite3

import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

MAX_PAGES=15

# ---------- 配置 ----------
PDF_DIR = "./documents"          # PDF 存放目录（相对于脚本运行位置）
CHROMA_PATH = "./chroma"         # Chroma 持久化目录（根目录下）
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200

if os.path.exists(CHROMA_PATH):
    print(f"检测到旧数据库 {CHROMA_PATH}，正在删除...")
    shutil.rmtree(CHROMA_PATH)
    print("旧库已删除")

# ---------- 加载所有 PDF ----------
def load_pdfs(directory):
    all_docs = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(directory, filename)
            print(f"正在加载 PDF: {filename}")
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            docs = docs[:MAX_PAGES]  # 限制每个 PDF 的最大页数
            print(f"只加载了前{len(docs)}页内容")
            all_docs.extend(docs)
    return all_docs

print("开始加载 PDF 文件...")
documents = load_pdfs(PDF_DIR)
print(f"共加载 {len(documents)} 页内容")

# ---------- 分块 ----------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
)
chunks = text_splitter.split_documents(documents)
print(f"分块后共 {len(chunks)} 个块")

# ---------- 初始化 Embedding ----------
embedding = OllamaEmbeddings(model="nomic-embed-text")

# ---------- 重建 Chroma 数据库（会覆盖旧库） ----------
print(f"正在重建 Chroma 数据库，路径: {CHROMA_PATH}")
db = Chroma.from_documents(
    documents=chunks,
    embedding=embedding,
    persist_directory=CHROMA_PATH
)
print("重建完成！")