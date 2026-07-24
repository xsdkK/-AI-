import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
import pysqlite3
sys.modules["sqlite3"] = pysqlite3

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.retrievers import BM25Retriever

# FastAPI实例化
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Embedding 模型
embedding = OllamaEmbeddings(model="nomic-embed-text")

# 加载已有向量库
db = Chroma(
    persist_directory="../chroma",
    embedding_function=embedding
)

# ---------- 构建 BM25 检索器 ----------
all_docs_data = db.get()
doc_texts = all_docs_data['documents']
metadatas = all_docs_data.get('metadatas', [None] * len(doc_texts))

bm25_retriever = BM25Retriever.from_texts(doc_texts, metadatas=metadatas)
bm25_retriever.k = 30   # 增大候选数

# ---------- 构建向量检索器（MMR 重排序，提高多样性） ----------
vector_retriever = db.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 30,               # 返回30个
        "fetch_k": 150,        # 候选池150
        "lambda_mult": 0.3     # 0.3 更偏重多样性
    }
)

# ---------- 初始化 LLM ----------
llm = ChatOllama(model="qwen2.5:7b")

# ---------- 分级 Prompt（允许推断） ----------
prompt = ChatPromptTemplate.from_template(
"""
你是一个知识渊博的助手，需要根据以下提供的资料回答问题。请遵循以下规则：

1. 如果资料中有与问题完全匹配的原文句子，请**直接引用原文**（不加修饰）。
2. 如果资料中没有完全匹配的原文，但包含相关的信息或上下文，请**基于资料内容进行合理推断**，用自己的话总结答案，并在开头说明“根据资料推断：”。

请确保你的回答**有据可依**，不要凭空编造。

资料：
{context}

问题：{question}

回答：
"""
)

# ================== 端点 ==================

@app.get("/chat")
def chat(q: str):
    # 分别检索
    bm25_docs = bm25_retriever.invoke(q)
    vector_docs = vector_retriever.invoke(q)
    
    # 合并去重
    seen = set()
    merged = []
    for doc in bm25_docs + vector_docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            merged.append(doc)
    
    # 取前50个（若少于50则全部）
    docs = merged[:50]
    context = "\n".join([doc.page_content for doc in docs])

    # 调试日志
    print("\n=== RETRIEVED CONTEXT ===")
    print(context)
    print("=== END OF CONTEXT ===\n")

    response = llm.invoke(prompt.format(context=context, question=q))

    print("=== MODEL RESPONSE ===")
    print(response.content)
    print("=== END OF RESPONSE ===\n")

    return {"answer": response.content}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "rag-qwen2.5-7b",
                "object": "model",
                "created": 1720000000,
                "owned_by": "rag-server"
            }
        ]
    }


class ChatRequest(BaseModel):
    model: str
    messages: list


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    user_q = req.messages[-1]["content"]
    res = await asyncio.to_thread(chat, q=user_q)
    return JSONResponse(content={
        "id": "rag-local",
        "object": "chat.completion",
        "choices": [{"message": {"role": "assistant", "content": res["answer"]}}],
    })