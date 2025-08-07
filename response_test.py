import requests
import json
import subprocess
import os
import tempfile
from gtts import gTTS
import pygame
import speech_recognition as sr
import threading
import pyttsx3

# Suppress ALSA error messages
os.environ['ALSA_PCM_CARD'] = 'default'
os.environ['ALSA_PCM_DEVICE'] = '0'

class ConversationManager:
    def __init__(self):
        self.conversation_history = []
        self.max_history = 3  # Increased for better context
    
    def add_exchange(self, user_message, ai_response):
        self.conversation_history.append({
            "user": user_message,
            "assistant": ai_response
        })
        
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_context_prompt(self, new_user_message):
        if not self.conversation_history:
            return f"You are ROOMIE, a helpful AI assistant. Give a brief, friendly response: {new_user_message}"
        
        context = "You are ROOMIE, a helpful AI assistant. Previous conversation:\n"
        for exchange in self.conversation_history[-2:]:  # Last 2 exchanges
            context += f"User: {exchange['user']}\n"
            context += f"ROOMIE: {exchange['assistant']}\n"
        
        context += f"\nUser: {new_user_message}\nROOMIE:"
        return context
    
    def clear_history(self):
        self.conversation_history = []
        print("🔄 Conversation history cleared!")

conversation = ConversationManager()

def speech_to_text_with_hotword():
    """Listen for hotword, then capture command - with error suppression"""
    r = sr.Recognizer()
    r.energy_threshold = 300
    
    # Suppress microphone warnings
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
    except Exception:
        print("⚠️ Microphone access limited, but continuing...")
    
    print("🎤 Say 'Hey ROOMIE' to activate...")
    
    while True:
        try:
            with sr.Microphone() as source:
                # Redirect stderr to suppress ALSA errors
                with open(os.devnull, 'w') as devnull:
                    old_stderr = os.dup(2)
                    os.dup2(devnull.fileno(), 2)
                    
                    try:
                        audio = r.listen(source, timeout=1, phrase_time_limit=3)
                    finally:
                        os.dup2(old_stderr, 2)
                        os.close(old_stderr)
            
            text = r.recognize_google(audio).lower()
            
            if "hey roomie" in text or "hey roomy" in text or "roomie" in text:
                print("✅ ROOMIE activated! What can I help you with?")
                
                # Now listen for the actual command
                with sr.Microphone() as source:
                    with open(os.devnull, 'w') as devnull:
                        old_stderr = os.dup(2)
                        os.dup2(devnull.fileno(), 2)
                        
                        try:
                            audio = r.listen(source, timeout=10, phrase_time_limit=15)
                        finally:
                            os.dup2(old_stderr, 2)
                            os.close(old_stderr)
                
                command = r.recognize_google(audio)
                print(f"📝 Command: {command}")
                return command
                
        except sr.WaitTimeoutError:
            continue  # Keep listening silently
        except sr.UnknownValueError:
            continue  # Keep listening silently
        except sr.RequestError as e:
            print(f"❌ Speech service error: {e}")
            return None
        except Exception:
            continue  # Suppress other audio errors

def get_ollama_response(prompt, use_history=True):
    """Get response from Ollama with conversation context"""
    try:
        if use_history:
            full_prompt = conversation.get_context_prompt(prompt)
        else:
            full_prompt = f"You are ROOMIE, a helpful AI assistant. Give a brief, friendly response: {prompt}"
        
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llama3:latest", 
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,        # Slightly longer responses
                    "top_p": 0.8,
                    "repeat_penalty": 1.1,
                    "num_ctx": 2048,
                    "num_threads": 4,
                    "num_gpu_layers": -1,
                    "numa": False,
                    "low_vram": False,
                    "f16_kv": True,
                    "use_mlock": True,
                    "use_mmap": True,
                }
            },
            timeout=30
        )
        if res.status_code == 200:
            response_data = res.json()
            ai_response = response_data.get("response", "No response")
            
            if use_history:
                conversation.add_exchange(prompt, ai_response)
            
            return ai_response
        else:
            return "Sorry I didn't quite get that"
    except Exception as e:
        return "Sorry I didn't quite get that"

def speak_text_windows_powershell(text):
    """Use Windows PowerShell TTS from WSL - Most Reliable"""
    try:
        print("🔊 ROOMIE speaking...")
        
        # Split long responses into chunks
        max_length = 300
        if len(text) > max_length:
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        else:
            chunks = [text]
        
        for chunk in chunks:
            # Escape quotes properly
            escaped_text = chunk.replace('"', '""').replace("'", "''")
            
            # PowerShell command for TTS
            ps_command = f"""
            Add-Type -AssemblyName System.Speech;
            $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;
            $speak.Rate = 4;
            $speak.Volume = 100;
            $speak.Speak('{escaped_text}');
            """
            
            # Run PowerShell from WSL with error suppression
            result = subprocess.run([
                'powershell.exe', '-Command', ps_command
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"📢 ROOMIE says: {text}")
                break
        
        print("✅ ROOMIE finished speaking")
            
    except Exception as e:
        print(f"📢 ROOMIE says: {text}")

def test_microphone_silent():
    """Test microphone without showing ALSA errors"""
    try:
        r = sr.Recognizer()
        with open(os.devnull, 'w') as devnull:
            old_stderr = os.dup(2)
            os.dup2(devnull.fileno(), 2)
            
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=1)
                return True
            finally:
                os.dup2(old_stderr, 2)
                os.close(old_stderr)
    except:
        return False

def main():
    print("🤖 ROOMIE - Voice AI Assistant")
    print("=" * 50)
    
    # Test microphone silently
    if test_microphone_silent():
        print("✅ Microphone detected")
    else:
        print("⚠️ Limited microphone access, but continuing...")
    
    print("🎙️ Starting ROOMIE...")
    speak_func = speak_text_windows_powershell
    
    print("\n" + "=" * 50)
    print("🎤 VOICE MODE ACTIVATED")
    print("• Say 'Hey ROOMIE' to start conversation")
    print("• Say 'clear memory' to reset conversation")  
    print("• Say 'goodbye' or 'quit' to exit")
    print("=" * 50)
    
    # Startup message
    print("\n🧪 ROOMIE initializing...")
    speak_func("Hello! I'm ROOMIE, your voice assistant. Say hey ROOMIE to talk with me!")
    
    while True:
        try:
            user_input = speech_to_text_with_hotword()
            
            if not user_input:
                continue
                
            # Check for exit commands
            if any(word in user_input.lower() for word in ['quit', 'exit', 'goodbye', 'bye bye']):
                speak_func("Goodbye! It was nice talking with you!")
                break
            elif any(phrase in user_input.lower() for phrase in ['clear memory', 'reset conversation', 'start over']):
                conversation.clear_history()
                speak_func("Memory cleared! Starting fresh conversation.")
                continue
            
            if user_input and user_input.strip():
                print("🤔 ROOMIE is thinking...")
                response = get_ollama_response(user_input, use_history=True)
                print(f"🤖 ROOMIE: {response}")
                print(f"💭 Memory: {len(conversation.conversation_history)} exchanges")
                
                # Speak the response
                speak_func(response)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            speak_func("Goodbye!")
            break
        except Exception as e:
            print("Sorry i Didn't quite get that")
            continue

if __name__ == "__main__":
    main()