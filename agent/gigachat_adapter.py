"""GigaChat adapter — wraps the GigaChat SDK to look like an OpenAI client.

Hermes expects an OpenAI-compatible ``client.chat.completions.create(...)``
interface.  The GigaChat SDK has a different API, so this adapter translates
between the two, handling OAuth token refresh automatically.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GigaChatOpenAIAdapter:
    """Drop-in replacement for ``openai.OpenAI`` that routes through GigaChat SDK."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ):
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole

        self._gigachat_client = GigaChat(
            credentials=api_key,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            model="GigaChat",
            timeout=timeout,
        )
        self._Chat = Chat
        self._Messages = Messages
        self._MessagesRole = MessagesRole
        self._timeout = timeout
        self._default_headers = default_headers or {}
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"

    @property
    def chat(self) -> "ChatCompletionsProxy":
        return ChatCompletionsProxy(self._gigachat_client, self._Messages, self._MessagesRole, self._Chat)

    def close(self) -> None:
        try:
            self._gigachat_client.close()
        except Exception:
            pass

    def __enter__(self) -> "GigaChatOpenAIAdapter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class ChatCompletionsProxy:
    """Proxy for ``client.chat.completions`` that translates OpenAI → GigaChat."""

    def __init__(self, gc_client, Messages, MessagesRole, Chat):
        self._gc = gc_client
        self._Messages = Messages
        self._MessagesRole = MessagesRole
        self._Chat = Chat
        self.completions = self  # self.completions.create → self.create

    def create(
        self,
        model: str = "GigaChat",
        messages: List[Dict[str, str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        from gigachat.models import Function

        # Translate OpenAI messages → GigaChat messages
        gc_messages = []
        for msg in messages or []:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Map roles
            if role == "system":
                # GigaChat doesn't have system role in older versions; merge into first user
                role = "user"
            elif role == "assistant":
                role = "assistant"
            elif role == "tool":
                role = "user"  # GigaChat doesn't have tool role
                # Include tool result as user content
                content = f"[Tool result: {msg.get('name', 'tool')}] {content}"

            gc_messages.append(self._Messages(role=self._MessagesRole(role), content=content))

        # Build chat payload
        chat_kwargs: Dict[str, Any] = {"messages": gc_messages}
        if model:
            chat_kwargs["model"] = model

        # Function calling support
        if tools:
            gc_functions = []
            for tool in tools:
                if tool.get("type") == "function":
                    fn = tool["function"]
                    gc_functions.append(
                        Function(
                            name=fn.get("name", ""),
                            description=fn.get("description", ""),
                            parameters=fn.get("parameters", {}),
                        )
                    )
            if gc_functions:
                chat_kwargs["functions"] = gc_functions

        chat = self._Chat(**chat_kwargs)

        # Call GigaChat
        response = self._gc.chat(chat)

        # Translate GigaChat response → OpenAI format
        return self._translate_response(response)

    def _translate_response(self, gc_response) -> "OpenAIChatCompletion":
        """Translate GigaChat response to OpenAI-like object."""
        choices = []
        if gc_response.choices:
            for choice in gc_response.choices:
                msg = choice.message
                message = {
                    "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    "content": msg.content or "",
                }
                if hasattr(msg, "function_call") and msg.function_call:
                    import json
                    message["tool_calls"] = [{
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": msg.function_call.name,
                            "arguments": json.dumps(msg.function_call.arguments) if isinstance(msg.function_call.arguments, dict) else msg.function_call.arguments,
                        },
                    }]
                choices.append({
                    "index": choice.index,
                    "message": message,
                    "finish_reason": choice.finish_reason,
                })

        usage = None
        if hasattr(gc_response, "usage") and gc_response.usage:
            usage = {
                "prompt_tokens": gc_response.usage.prompt_tokens,
                "completion_tokens": gc_response.usage.completion_tokens,
                "total_tokens": gc_response.usage.total_tokens,
            }

        return OpenAIChatCompletion(
            id=f"gc-{uuid.uuid4().hex[:12]}",
            object="chat.completion",
            created=gc_response.created if hasattr(gc_response, "created") else int(time.time()),
            model=gc_response.model if hasattr(gc_response, "model") else "GigaChat",
            choices=choices,
            usage=usage,
        )


class OpenAIChatCompletion:
    """OpenAI-like response object."""

    def __init__(self, id, object, created, model, choices, usage=None):
        self.id = id
        self.object = object
        self.created = created
        self.model = model
        self.choices = [OpenAIChoice(**c) for c in choices]
        self.usage = usage

    def model_dump(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [c.model_dump() for c in self.choices],
            "usage": self.usage,
        }


class OpenAIChoice:
    def __init__(self, index, message, finish_reason):
        self.index = index
        self.message = OpenAIMessage(**message)
        self.finish_reason = finish_reason

    def model_dump(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "message": self.message.model_dump(),
            "finish_reason": self.finish_reason,
        }


class OpenAIMessage:
    def __init__(self, role, content, tool_calls=None, **kwargs):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result
