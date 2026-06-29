import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Fix windows encoding for emojis in console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from core.model_manager import ModelManager
import config

def test_model(mm, model_name, messages, system_prompt):
    print(f"\n--- Testing Node: {model_name} ---")
    try:
        stream = mm.generate_stream(
            messages=messages, 
            system_prompt=system_prompt, 
            model_override=model_name
        )
        print("Response: ", end="")
        for chunk in stream:
            print(chunk, end="", flush=True)
        print("\n\n[SUCCESS] Generation complete.")
    except Exception as e:
        print(f"\n[ERROR] Failure: {e}")

def main():
    print("=== JARVIS Intelligence Grid Status ===")
    print(f"GROQ_API_KEY Active: {bool(config.GROQ_API_KEY)}")
    print(f"GEMINI_API_KEY Active: {bool(config.GEMINI_API_KEY)}")
    
    print("\nInitializing Neural Hub...")
    try:
        mm = ModelManager()
    except Exception as e:
        print(f"Initialization Failed: {e}")
        return
    
    messages = [{"role": "user", "content": "Respond with the word 'Active' and nothing else."}]
    system_prompt = config.SYSTEM_PROMPT.format(current_date="Today")
    
    # 1. Test Groq
    test_model(mm, "llama-3.1-8b-instant", messages, system_prompt)
    
    # 2. Test Gemini
    test_model(mm, "gemini-2.5-flash", messages, system_prompt)

if __name__ == "__main__":
    main()
