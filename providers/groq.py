import httpx
from typing import Dict, Any, Optional, AsyncGenerator
import json
from config import GROQ_API_KEY, GROQ_BASE_URL

class GroqProvider:
    def __init__(self):
        self.name = "groq"
        self.api_key = GROQ_API_KEY
        self.base_url = GROQ_BASE_URL
        self.client = httpx.AsyncClient(timeout=60.0)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def chat_completions(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Send chat completion request to Groq."""
        url = f"{self.base_url}/chat/completions"
        
        # If in test mode (no API key), return mock response
        if not self.api_key or self.api_key == "":
            return self._mock_response(request_body)
        
        try:
            response = await self.client.post(
                url,
                headers=self.headers,
                json=request_body,
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Groq error {response.status_code}: {response.text}")
            
            return response.json()
        except httpx.TimeoutException:
            raise Exception("Groq request timed out")
        except Exception as e:
            raise Exception(f"Groq request failed: {str(e)}")
    
    async def stream_chat_completions(self, request_body: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Stream chat completion from Groq."""
        url = f"{self.base_url}/chat/completions"
        
        if not self.api_key or self.api_key == "":
            # Mock streaming
            yield self._mock_stream_chunk(request_body)
            yield "data: [DONE]\n\n"
            return
        
        request_body["stream"] = True
        
        try:
            async with self.client.stream(
                "POST",
                url,
                headers=self.headers,
                json=request_body,
                timeout=120.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Groq error {response.status_code}: {error_text.decode()}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield f"{line}\n\n"
        except Exception as e:
            raise Exception(f"Groq stream failed: {str(e)}")
    
    async def health_check(self) -> tuple[bool, int, Optional[str]]:
        """Check if Groq API is healthy."""
        if not self.api_key or self.api_key == "":
            # In test mode, we consider it "healthy" but return a signal
            return True, 0, "TEST_MODE_NO_KEY"
        
        try:
            import time
            start = time.time()
            response = await self.client.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10.0
            )
            latency_ms = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return True, latency_ms, None
            else:
                return False, latency_ms, f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            return False, 10000, "Timeout"
        except Exception as e:
            return False, 0, str(e)
    
    def _mock_response(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock response for testing without API key."""
        import uuid
        import time
        
        model = request_body.get("model", "unknown")
        messages = request_body.get("messages", [])
        last_message = messages[-1]["content"] if messages else "Hello"
        
        return {
            "id": f"chatcmpl-mock-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[MOCK - Groq test mode] You said: '{last_message[:50]}...' This is a test response. Set GROQ_API_KEY for real responses."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(last_message.split()),
                "completion_tokens": 15,
                "total_tokens": len(last_message.split()) + 15
            }
        }
    
    def _mock_stream_chunk(self, request_body: Dict[str, Any]) -> str:
        """Generate a mock stream chunk."""
        import uuid
        import time
        
        model = request_body.get("model", "unknown")
        chunk = {
            "id": f"chatcmpl-mock-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": "[MOCK - test mode] Set GROQ_API_KEY for real responses. "},
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
