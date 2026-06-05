import os
import sys
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.model_manager import ModelManager

async def main():
    from core.chat_engine import ChatEngine
    ce = ChatEngine()
    
    # Mock user since active_user is None
    class MockUser:
        tier = "free"
        id = 1
        username = "Test"
    
    gen = ce.chat_stream("Hello", MockUser(), "conv_123", mode="chat", trace_id="trc_test")
    print("Start stream:")
    for chunk in gen:
        print("CHUNK:", repr(chunk))
    print("End stream.")

if __name__ == '__main__':
    asyncio.run(main())
