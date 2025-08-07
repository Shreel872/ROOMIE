# Add these imports at the top with your other imports
import requests
import json
import subprocess
import os
import tempfile
from gtts import gTTS
import pygame
import speech_recognition as sr
import edge_tts
import threading
import pyttsx3
import pvporcupine
import pyaudio
import struct
from vosk import Model, KaldiRecognizer
import pyaudio
import pygame
import os
import asyncio

# Add Spotify imports
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request

# Import your Spotify controller
from spotify import SpotifyController

# Create global Spotify instance
spotify_controller = None

# Add this at the very top of your file to suppress ALSA warnings
import os
os.environ['ALSA_PCM_CARD'] = '0'
os.environ['ALSA_PCM_DEVICE'] = '0'

# Redirect ALSA error messages to /dev/null
import sys
from contextlib import redirect_stderr
import io

# Suppress ALSA warnings globally
def suppress_alsa_warnings():
    """Suppress ALSA warnings and errors"""
    try:
        # For Linux systems, redirect ALSA errors
        os.system("export ALSA_CARD=0 2>/dev/null")
        os.system("export ALSA_DEVICE=0 2>/dev/null")
        
        # Suppress pygame mixer warnings
        os.environ['SDL_AUDIODRIVER'] = 'pulse'
        
    except:
        pass



# Global audio control variables
audio_playing = False
audio_stop_flag = False
audio_thread = None

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
            return f" Give a brief, friendly response: {new_user_message}"
        
        context = "a helpful AI assistant. Previous conversation:\n"
        for exchange in self.conversation_history[-2:]:  # Last 2 exchanges
            context += f"User: {exchange['user']}\n"
            context += f"ROOMIE: {exchange['assistant']}\n"
        
        context += f"\nUser: {new_user_message}\nROOMIE:"
        return context
    
    def clear_history(self):
        self.conversation_history = []
        print("🔄 Conversation history cleared!")

conversation = ConversationManager()
def get_ollama_response(prompt, use_history=True):
    """Get response from Ollama with conversation context"""
    try:
        if use_history:
            full_prompt = conversation.get_context_prompt(prompt)
        else:
            full_prompt = f"Give a brief INFORMATIVE response: {prompt}"
        
        print("🔗 Connecting to Ollama...")  # Debug info
            
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llama3:latest", 
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,
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
        
        print(f"📡 Response status: {res.status_code}")  # Debug info
        
        if res.status_code == 200:
            response_data = res.json()
            ai_response = response_data.get("response", "No response")
            
            if use_history:
                conversation.add_exchange(prompt, ai_response)
            
            return ai_response
        else:
            print(f"❌ HTTP Error: {res.status_code} - {res.text}")
            return "Sorry, I'm having connection issues"
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Is it running?")
        return "I can't connect to my AI brain right now. Is Ollama running?"
    except requests.exceptions.Timeout:
        print("❌ Ollama request timed out")
        return "Sorry, I'm thinking too slowly right now"
    except json.JSONDecodeError:
        print("❌ Invalid JSON response from Ollama")
        return "I got a confusing response from my brain"
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return "Something unexpected happened"

def initialize_spotify():

    global spotify_controller
    try:
        print(" Initializing Spotify connection...")
        spotify_controller = SpotifyController()

        if os.path.exists(".spotify_cache"):
            print("Found existing Spotify credentials")
            try:

                auth_manager = SpotifyOAuth(
                    client_id=spotify_controller.client_id,
                    client_secret=spotify_controller.client_secret,
                    redirect_uri=spotify_controller.redirect_uri,
                    scope=spotify_controller.scope,
                    cache_path=".spotify_cache"
                )
                
                token_info = auth_manager.get_cached_token()
                if token_info:
                    spotify_controller.sp = spotipy.Spotify(auth_manager=auth_manager)
                    spotify_controller.is_authenticated = True
                    print("Spotify connected using cached credentials")
                    return True
            except:
                print("Cached credentials expired")

        print("Spotify authentication required")
        return spotify_controller.authenticate()
        
    except Exception as e:
        print(f"Spotify initialization failed: {e}")
        return False

def handle_spotify_commands(user_input):
    """Check if user wants to control Spotify and handle it"""
    global spotify_controller
    spotify_keywords = [
        "play", "pause", "stop", "next", "skip", "previous", "back",
        "volume", "spotify", "music", "song", "artist", "playlist",
        "what's playing", "current song", "shuffle"
    ]
    if any(keyword in user_input.lower() for keyword in spotify_keywords):
        
        # Initialize Spotify if not done already
        if spotify_controller is None or not spotify_controller.is_authenticated:
            print("🎵 Setting up Spotify connection...")
            if not initialize_spotify():
                return "Sorry, I couldn't connect to Spotify right now."
        
        # Process the Spotify command
        try:
            command = user_input.lower()
            
            if "play" in command and len(command.split()) > 1:
                # Extract what to play
                if "play " in command:
                    query = command.split("play ", 1)[1]
                    
                    # Clean up common phrases
                    query = query.replace("on spotify", "").strip()
                    query = query.replace("please", "").strip()
                    
                    if "playlist" in query:
                        query = query.replace("playlist", "").strip()
                        return spotify_controller.search_and_play(query, "playlist")
                    elif "artist" in query or "by" in query:
                        query = query.replace("artist", "").replace("by", "").strip()
                        return spotify_controller.search_and_play(query, "artist")
                    else:
                        return spotify_controller.search_and_play(query, "track")
                else:
                    return spotify_controller.resume_music()
            
            elif "pause" in command or "stop music" in command:
                return spotify_controller.pause_music()
            
            elif "next" in command or "skip" in command:
                return spotify_controller.next_track()
            
            elif "previous" in command or "back" in command:
                return spotify_controller.previous_track()
            
            elif "volume" in command:
                # Extract volume level
                words = command.split()
                for i, word in enumerate(words):
                    if word == "volume" and i + 1 < len(words):
                        try:
                            volume = int(words[i + 1])
                            return spotify_controller.set_volume(volume)
                        except ValueError:
                            pass
                return "Please specify a volume level between 0 and 100"
            
            elif "what's playing" in command or "current song" in command:
                return spotify_controller.get_current_track()
            
            elif "shuffle on" in command:
                return spotify_controller.shuffle_toggle(True)
            
            elif "shuffle off" in command:
                return spotify_controller.shuffle_toggle(False)
            
            else:

                if "play" in command:
                    words = command.split()
                    if len(words) > 1:
                        song_name = " ".join(words[words.index("play") + 1:])
                        return spotify_controller.search_and_play(song_name, "track")
                
                return "I didn't understand that music command. Try saying 'play [song name]', 'pause', 'next', or 'volume [number]'"
                
        except Exception as e:
            print(f"Spotify command error: {e}")
            return "Sorry, I had trouble with that music command."
    
    return None  # Not a Spotify command
# Global audio control variables
audio_playing = False
audio_stop_flag = False
audio_thread = None

def play_audio_file(output_file):
    global audio_playing, audio_stop_flag
    
    try:
        audio_playing = True
        with redirect_stderr(io.StringIO()):
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Load and play sound
        sound = pygame.mixer.Sound(output_file)
        sound.play()
        
        print("Speaking... (say 'stop' to interrupt)")
        
        while pygame.mixer.get_busy() and not audio_stop_flag:
            pygame.time.wait(50)
        
        if audio_stop_flag:
            pygame.mixer.stop()
            print("Audio interrupted!")
        else:
            print("Audio completed")
        
    except Exception as e:
        print(f"Audio playback error: {e}")
    finally:
        audio_playing = False
        audio_stop_flag = False
        try:
            pygame.mixer.quit()
        except:
            pass

async def speak_edge_tts(text, voice="en-GB-RyanNeural"):
    global audio_thread, audio_stop_flag
    output_file = "/home/patel/roomie/roomie_response.wav"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
        if not os.path.exists(output_file):
            print(f"WAV file not created")
            return
        audio_stop_flag = False
        audio_thread = threading.Thread(target=play_audio_file, args=(output_file,), daemon=True)
        audio_thread.start()
        return audio_thread
        
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def stop_audio():
    global audio_stop_flag, audio_thread
    if audio_playing:
        audio_stop_flag = True
        print("Stopping audio...")
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0.5)
def wait_for_audio_or_interrupt():
    global audio_thread
    
    while audio_playing:
        # Listen for interrupt commands while audio is playing
        user_input = listen_for_interrupt_command()
        if user_input:
            if check_for_interrupt_commands(user_input):
                stop_audio()
                return True
        
        import time
        time.sleep(0.05)
    
    return False 

def listen_for_interrupt_command():
    try:
        if not hasattr(speechrecognition_whisper, 'model'):
            return None
        mic = pyaudio.PyAudio()
        
        with redirect_stderr(io.StringIO()):
            stream = mic.open(
                format=pyaudio.paInt16, 
                channels=1,
                rate=16000, 
                input=True, 
                frames_per_buffer=1024
            )
        
        frames = []
        for i in range(0, int(16000 / 1024 * 0.5)):
            try:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            except:
                break
        
        stream.stop_stream()
        stream.close()
        mic.terminate()
        
        if len(frames) > 5: 
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                wf = wave.open(tmp_file.name, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
                result = speechrecognition_whisper.model.transcribe(tmp_file.name, fp16=False)
                text = result["text"].strip()
                
                os.unlink(tmp_file.name)
                return text
                
    except Exception as e:
        pass
    
    return None
def speak_text_windows_powershell(text):
    """Use Windows PowerShell TTS from WSL - Most Reliable"""
    try:
        print("🔊 ROOMIE speaking...")
        max_length = 300
        if len(text) > max_length:
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        else:
            chunks = [text]
        
        for chunk in chunks:
            escaped_text = chunk.replace('"', '""').replace("'", "''")
            ps_command = f"""
            Add-Type -AssemblyName System.Speech;
            $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;
            $speak.Rate = 4;
            $speak.Volume = 100;
            $speak.Speak('{escaped_text}');
            """
            result = subprocess.run([
                'powershell.exe', '-Command', ps_command
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"ROOMIE says: {text}")
                break
        
        print("ROOMIE finished speaking")
            
    except Exception as e:
        print(f"ROOMIE says: {text}")
access_key  = "yVgCoNgUgf+aHvjPwHh2L6hCR1SanP0WiLD8D8O+/e6x/zkJ5YPJgg=="
def hotword_detect_loop():
    porcupine = pvporcupine.create(access_key = access_key,keywords=["computer"])
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )
    print("looking for HOTWORD")
    while True:
        audio = stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h"*porcupine.frame_length, audio)
        hotkey_trig = porcupine.process(pcm)
        if hotkey_trig >=0:
            print("HOTKEY TRIGGERED!!")
            subprocess.run([
                'powershell.exe', '-Command', 
                '[console]::beep(800,200)'
            ], capture_output=True, timeout=2)
            stream.stop_stream()
            stream.close()
            pa.terminate()
            porcupine.delete()
            return True
def speechrecognition():
    model = Model("/mnt/c/Users/crick/Downloads/vosk-model-en-us-0.22-lgraph/vosk-model-en-us-0.22-lgraph") 
    rec = KaldiRecognizer(model, 16000)
    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16, channels=1,
                      rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()

    print("🎤 Listening for command...")
    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            return result.get("text", "")
def play_startup_sound():
    try:
        pygame.mixer.init()
        sound_path = "/mnt/c/Users/crick/Downloads/startup.mp3"
        
        if os.path.exists(sound_path):
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(10)
            print("Startup sound played successfully")
        else:
            print("startup.mp3 not found at:", sound_path)
    except Exception as e:
        print(f"Could not play startup sound: {e}")
    finally:
        pygame.mixer.quit()

import whisper
import pyaudio
import wave
import tempfile
import os

def speechrecognition_whisper():
    """Use OpenAI Whisper for much better accuracy"""
    try:
        # Load Whisper model (do this once at startup)
        if not hasattr(speechrecognition_whisper, 'model'):
            print("Loading Whisper model")
            speechrecognition_whisper.model = whisper.load_model("medium")  # or "small", "medium", "large"
        
        # Record audio
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16, channels=1,
                          rate=16000, input=True, frames_per_buffer=8000)
        
        print("Listening for command...")
        frames = []
        

        for i in range(0, int(16000 / 8000 * 5)): 
            data = stream.read(8000, exception_on_overflow=False)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        mic.terminate()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            wf = wave.open(tmp_file.name, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(mic.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            result = speechrecognition_whisper.model.transcribe(tmp_file.name)
            text = result["text"].strip()
            
            # Clean up
            os.unlink(tmp_file.name)
            
            print(f"Whisper heard: {text}")
            return text
            
    except Exception as e:
        print(f"Whisper error: {e}")
        return ""

def check_for_interrupt_commands(user_input):
    """Check if user wants to interrupt AI processing"""
    interrupt_phrases = [
        'stop', 'cancel', 'interrupt', 'shut up', 'quiet', 'pause ai',
        'stop talking', 'be quiet', 'enough', 'never mind', 'skip'
    ]
    
    if any(phrase in user_input.lower() for phrase in interrupt_phrases):
        print("Interrupt command detected!")
        return True
    return False
class RoomieLogicSM:
    def __init__(self):
        self.state = "WAIT"
    def state(self, event):
        if(self.state == "WAIT"):
            if hotword_detect_loop() == True:
                self.state = "GETPHRASE"
        elif(self.state == "GETPHRASE"):
            user_input = speechrecognition()
            self.state = "CONDTS"
        elif self.state == "CONDTS":
            speak_func = speak_text_windows_powershell
            if any(word in user_input.lower() for word in ['quit', 'exit', 'goodbye', 'bye bye']):
                asyncio.run(speak_edge_tts("Goodbye! It was nice talking with you!"))
            elif any(phrase in user_input.lower() for phrase in ['clear memory', 'reset conversation', 'start over']):
                conversation.clear_history()
                asyncio.run(speak_edge_tts("Memory cleared! Starting fresh conversation."))         
            if user_input and user_input.strip():
                print("🤔 ROOMIE is thinking...")
                response = get_ollama_response(user_input, use_history=True)
                print(f"🤖 ROOMIE: {response}")
                print(f"💭 Memory: {len(conversation.conversation_history)} exchanges")
                

                print(user_input)
                asyncio.run(speak_edge_tts(response))




def main():
    suppress_alsa_warnings()
    print("ROOMIE - Shreel's AI Assistant")
    print("=" * 50)
    speak_func = speak_text_windows_powershell
    
    play_startup_sound()
    asyncio.run(speak_edge_tts("Hello! I'm ROOMIE, your voice assistant. I can also control your Spotify music. How can I help you Shrill?"))
    
    hotkey = hotword_detect_loop()
    
    while hotkey:
        try:
            user_input = speechrecognition_whisper()
            
            if not user_input:
                continue
                
            # Check for exit commands
            if any(word in user_input.lower() for word in ['quit', 'exit', 'goodbye', 'bye bye']):
                asyncio.run(speak_edge_tts("Shutting down say Yes to confirm"))
                break
            elif any(phrase in user_input.lower() for phrase in ['clear memory', 'reset conversation', 'start over']):
                conversation.clear_history()
                asyncio.run(speak_edge_tts("Memory cleared! Starting fresh conversation."))
                continue
            elif any(phrase in user_input.lower() for phrase in ['open door','unlock door','open sesame']):
                asyncio.run(speak_edge_tts("The door should be open now, sir!"))

                #add connecting code that transmits data to the esp32 to send voltage through transistor gate and activate solenoid
                continue
            elif any(phrase in user_input.lower() for phrase in ['open rivals','open marvel','open le game']):
                asyncio.run(speak_edge_tts("Opening Marvel Rivals Now ... sir!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            f'Start-Process "{r"C:\Users\crick\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Steam\Marvel Rivals.url"}"'
                        ], capture_output=True)
                continue
            elif any(phrase in user_input.lower() for phrase in ["open split gate","Launch Split gate"]):
                asyncio.run(speak_edge_tts("Opening Marvel Rivals Now ... sir!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            f'Start-Process "{r"C:\Users\crick\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Steam\Splitgate 2.url"}"'
                        ], capture_output=True)
            elif any(phrase in user_input.lower() for phrase in ["spotify","open music"]):
                asyncio.run(speak_edge_tts("opening spotify!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            'start spotify:'
                        ], capture_output=True)
                continue
            elif any(phrase in user_input.lower() for phrase in ["close music"]):
                asyncio.run(speak_edge_tts("closing spotify now!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            'Stop-Process -Name spotify'
                        ], capture_output=True)
                continue
            elif any(phrase in user_input.lower() for phrase in ["close google"]):
                asyncio.run(speak_edge_tts("closing google now!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            'Stop-Process -Name google'
                        ], capture_output=True)
                continue
            elif any(phrase in user_input.lower() for phrase in ["open google","google"]):
                asyncio.run(speak_edge_tts("The google web browser should be open now ... sir!"))
                subprocess.run([
                            'powershell.exe', '-Command', 
                            f'Start-Process "{r"C:\Program Files\Google\Chrome\Application\chrome.exe"}"'
                        ], capture_output=True)
                continue


            if user_input and user_input.strip():
                print(f"You said: {user_input}")

                if check_for_interrupt_commands(user_input):
                    asyncio.run(speak_edge_tts("Okay, stopping."))
                    hotkey = hotword_detect_loop()
                    continue
                
                # Check for Spotify commands SECOND
                spotify_response = handle_spotify_commands(user_input)
                if spotify_response:
                    print(f"Spotify: {spotify_response}")
                    asyncio.run(speak_edge_tts(spotify_response))
                    # Wait for next command
                    hotkey = hotword_detect_loop()
                    continue
                
                # If not a Spotify command, process with Ollama
                print("ROOMIE is thinking...")
                
                response = get_ollama_response(user_input, use_history=True)
                
                print(f"ROOMIE: {response}")
                print(f"Memory: {len(conversation.conversation_history)} exchanges")
                
                # Start audio playback in separate thread
                audio_thread = asyncio.run(speak_edge_tts(response))
                
                # Wait for audio to finish or for interrupt
                if audio_thread:
                    interrupted = wait_for_audio_or_interrupt()
                    if interrupted:
                        print("Audio was interrupted by user")
                    else:
                        print("Audio completed normally")
                
            # Wait for next hotword
            hotkey = hotword_detect_loop()
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            asyncio.run(speak_edge_tts("Goodbye!"))
            break
        except Exception as e:
            print(f"Error: {e}")
            asyncio.run(speak_edge_tts("Sorry, I didn't quite get that"))
            hotkey = hotword_detect_loop()
            continue

if __name__ == "__main__":
    main()