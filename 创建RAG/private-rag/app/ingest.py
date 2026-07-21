print("1. 开始导入模块")

import sys
import pysqlite3

sys.modules["sqlite3"] = pysqlite3

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

print("2. 模块导入完成")

loader = PyMuPDFLoader("../documents/test.pdf")
print("3. 创建 Loader 完成")

docs = loader.load()
print(f"4. PDF 加载完成，共 {len(docs)} 页")

embedding = OllamaEmbeddings(model="nomic-embed-text")
print("5. Embedding 初始化完成")

db = Chroma.from_documents(
    docs,
    embedding,
    persist_directory="../chroma"
)

print("6. 向量库创建完成")