#!/usr/bin/env python3
"""
Hermes API Server v0.3.0

Локальный API-сервер для Hermes Agent.
Поддерживает:
- OpenAI-совместимый формат (Kilo Code, Continue, Cline)
- Кастомный формат (Agent проект D:\GitHub\agent)
- Стриминг (SSE)
- API Key защита

Использование:
    python api_server.py
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Literal, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import yaml  # Для работы с config.yaml

from run_agent import AIAgent

API_DIR = Path(__file__).parent
HERMES_HOME = Path.home() / ".hermes"  # Стандартная папка Hermes


class Config:
    HOST = "0.0.0.0"
    PORT = 8765
    PROVIDER = os.getenv("HERMES_PROVIDER", "alibaba")
    MODEL = os.getenv("HERMES_MODEL", "qwen3.5-plus")
    API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    ENABLED_TOOLSETS = ["hermes-cli"]
    SESSION_ID = "api-server-session"
    PLATFORM = "api-server"
    SERVER_API_KEY = os.getenv("HERMES_SERVER_API_KEY", "hermes-secret-key-2026")
    
    # Публичное имя модели (видят внешние клиенты)
    PUBLIC_MODEL_NAME = "Hermes"
    
    # Файлы конфигурации и статистики
    CONFIG_FILE = HERMES_HOME / "config.yaml"
    STATS_FILE = HERMES_HOME / "hermes_api_stats.json"


# === Модели для кастомного формата ===
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# === Модели для OpenAI формата ===
class OpenAIMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, list, None] = None
    name: Optional[str] = None


class OpenAIChatRequest(BaseModel):
    model: str = "Hermes"  # Клиенты отправляют "Hermes", мы игнорируем
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIMessage
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatResponse(BaseModel):
    id: str = "chatcmpl-hermes"
    object: str = "chat.completion"
    created: int = 0
    model: str = "Hermes"  # Всегда возвращаем "Hermes"
    choices: List[OpenAIChoice]
    usage: OpenAIUsage


class OpenAIModel(BaseModel):
    id: str = "Hermes"  # Внешний мир видит "Hermes"
    object: str = "model"
    created: int = 0
    owned_by: str = "hermes"


class OpenAIModelList(BaseModel):
    object: str = "list"
    data: List[OpenAIModel]


def extract_message_content(msg: OpenAIMessage) -> str:
    if msg.content is None:
        return ""
    if isinstance(msg.content, str):
        return msg.content
    if isinstance(msg.content, list):
        texts = []
        for block in msg.content:
            if isinstance(block, dict):
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)
    return str(msg.content)

def log_usage(prompt_tokens: int, completion_tokens: int, model: str):
    """Записывает статистику использования токенов в файл."""
    try:
        HERMES_HOME.mkdir(parents=True, exist_ok=True)
        stats_file = Config.STATS_FILE
        
        stats = {}
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        
        # Обновляем общую статистику
        stats["total_prompt_tokens"] = stats.get("total_prompt_tokens", 0) + prompt_tokens
        stats["total_completion_tokens"] = stats.get("total_completion_tokens", 0) + completion_tokens
        stats["total_tokens"] = stats.get("total_tokens", 0) + (prompt_tokens + completion_tokens)
        stats["last_request"] = time.strftime("%Y-%m-%d %H:%M:%S")
        stats["model_used"] = model
        
        # История запросов (последние 10)
        history = stats.get("history", [])
        history.append({
            "time": stats["last_request"],
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
            "model": model
        })
        stats["history"] = history[-10:]  # Храним последние 10
        
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Ошибка записи статистики: {e}")


# === FastAPI приложение ===
app = FastAPI(
    title="Hermes API Server",
    description="Локальный API-сервер с OpenAI-совместимостью и кастомным форматом",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
    
    if api_key != Config.SERVER_API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    
    return await call_next(request)


agent: Optional[AIAgent] = None


@app.on_event("startup")
async def startup():
    global agent
    print("🚀 Hermes API Server v0.3.0")
    print(f"   Порт: {Config.PORT}")
    print(f"   API Key: ✅")
    print(f"   Стриминг: ✅")
    print(f"   Кастомный /chat: ✅")
    print(f"   OpenAI /v1: ✅")
    
    try:
        agent = AIAgent(
            provider=Config.PROVIDER,
            model=Config.MODEL,
            api_key=Config.API_KEY or None,
            enabled_toolsets=Config.ENABLED_TOOLSETS,
            session_id=Config.SESSION_ID,
            platform=Config.PLATFORM,
            quiet_mode=True,
        )
        print("✅ Агент готов")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        agent = None


# === КАСТОМНЫЕ ENDPOINTS (для Agent проекта) ===

@app.get("/health")
async def health():
    return {"status": "ok" if agent else "init", "model": Config.MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Кастомный endpoint для Agent проекта (D:\GitHub\agent)"""
    if not agent:
        raise HTTPException(503, "Агент не готов")
    try:
        response = agent.chat(request.message)
        return ChatResponse(response=response, session_id=request.session_id or Config.SESSION_ID)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/tools")
async def list_tools():
    from model_tools import get_all_tool_names, get_available_toolsets
    return {"tools": get_all_tool_names(), "toolsets": list(get_available_toolsets().keys())}


@app.websocket("/stream")
async def stream_ws(websocket: WebSocket):
    await websocket.accept()
    if not agent:
        await websocket.send_json({"type": "error", "message": "Агент не готов"})
        return
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            async def callback(token):
                await websocket.send_json({"type": "token", "content": token})
            response = agent.chat(msg["text"], stream_callback=callback)
            await websocket.send_json({"type": "complete", "content": response})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


# === OPENAI ENDPOINTS (для Kilo Code, Continue, Cline) ===

@app.get("/v1/models", response_model=OpenAIModelList)
async def list_models():
    return OpenAIModelList(data=[OpenAIModel(id=Config.PUBLIC_MODEL_NAME, created=int(time.time()), owned_by="hermes")])


@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat(request: OpenAIChatRequest):
    if not agent:
        raise HTTPException(503, "Агент не готов")
    
    try:
        last_message = None
        system_prompt = ""
        
        for msg in request.messages:
            if msg.role == "system":
                system_prompt = extract_message_content(msg)
            elif msg.role == "user":
                last_message = extract_message_content(msg)
        
        if not last_message:
            raise HTTPException(400, "No user message")
        
        if request.stream:
            return await openai_chat_stream(request, last_message, system_prompt)
        
        full_prompt = f"{system_prompt}\n\n{last_message}" if system_prompt else last_message
        response = agent.chat(full_prompt)  # Используем ВНУТРЕННЮЮ модель (Config.MODEL)
        
        prompt_tokens = int(len(last_message.split()) * 1.3)
        completion_tokens = int(len(response.split()) * 1.3)
        log_usage(prompt_tokens, completion_tokens, Config.MODEL)
        
        return OpenAIChatResponse(
            created=int(time.time()),
            model=Config.PUBLIC_MODEL_NAME,  # Возвращаем "Hermes" (не внутреннюю модель)
            choices=[OpenAIChoice(message=OpenAIMessage(role="assistant", content=response), finish_reason="stop")],
            usage=OpenAIUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
    except Exception as e:
        raise HTTPException(500, str(e))


async def openai_chat_stream(request: OpenAIChatRequest, last_message: str, system_prompt: str):
    full_prompt = f"{system_prompt}\n\n{last_message}" if system_prompt else last_message
    
    async def generate():
        try:
            response = agent.chat(full_prompt)
            chunk = {
                "id": "chatcmpl-hermes",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": Config.PUBLIC_MODEL_NAME,  # "Hermes"
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": response}, "finish_reason": "stop"}],
            }
            
            prompt_tokens = int(len(last_message.split()) * 1.3)
            completion_tokens = int(len(response.split()) * 1.3)
            log_usage(prompt_tokens, completion_tokens, Config.MODEL)
            
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Hermes API Server v0.3.0")
    print(f"  http://localhost:{Config.PORT}")
    print(f"  Кастомный: /chat, /tools, /stream")
    print(f"  OpenAI: /v1/models, /v1/chat/completions")
    print("=" * 60)
    uvicorn.run(app, host=Config.HOST, port=Config.PORT, log_level="info")
