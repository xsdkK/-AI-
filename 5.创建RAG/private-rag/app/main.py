import sys
import pysqlite3

sys.modules["sqlite3"] = pysqlite3

from fastapi import FastAPI

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama

from langchain_core.prompts import ChatPromptTemplate


app = FastAPI()


embedding = OllamaEmbeddings(
    model="nomic-embed-text"
)


db = Chroma(
    persist_directory="../chroma",
    embedding_function=embedding
)


llm = ChatOllama(
    model="qwen2.5:7b"
)


prompt = ChatPromptTemplate.from_template(
"""
请根据下面的资料回答问题：

{context}

问题：
{question}
"""
)


@app.get("/chat")
def chat(q: str):

    docs = db.similarity_search(q, k=3)

    context = "\n".join(
        [doc.page_content for doc in docs]
    )

    response = llm.invoke(
        prompt.format(
            context=context,
            question=q
        )
    )

    return {
        "answer": response.content
    }