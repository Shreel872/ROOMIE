import speech_recognition as sr
import pyaudio
import threading
import pvporcupine
import time
from typing import Optional

def speech_to_text_simple() -> Optional[str]:
    """Simple one-time speech recognition"""
    r = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("🎤 Say something...")
        try:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=1)
            
            # Listen for audio
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            
            print("🔄 Processing speech...")
            
            # Convert to text using Google's service
            text = r.recognize_google(audio)
            print(f"📝 You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Error with speech service: {e}")
            return None

def speech_to_text_continuous():
    """Continuous speech recognition with hotword detection"""
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8
    
    print("🎤 Continuous listening mode activated!")
    print("Say 'Hey computer' to activate, or 'stop listening' to quit")
    
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
    
    listening_for_command = False
    
    while True:
        try:
            with sr.Microphone() as source:
                if not listening_for_command:
                    print("🔍 Listening for 'Hey computer'...")
                    audio = r.listen(source, timeout=1, phrase_time_limit=3)
                else:
                    print("🎤 Listening for your command...")
                    audio = r.listen(source, timeout=10, phrase_time_limit=15)
                
            text = r.recognize_google(audio).lower()
            
            if not listening_for_command:
                if "hey computer" in text or "hey assistant" in text:
                    print("✅ Activated! What can I help you with?")
                    listening_for_command = True
                    continue
            else:
                if "stop listening" in text or "quit" in text:
                    print("👋 Stopping continuous listening")
                    break
                    
                print(f"📝 Command: {text}")
                listening_for_command = False
                return text
                
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            if listening_for_command:
                print("❌ Didn't catch that, try again")
                listening_for_command = False
        except sr.RequestError as e:
            print(f"❌ Speech service error: {e}")
            break

def speech_to_text_with_options():
    """Speech recognition with multiple service options"""
    r = sr.Recognizer()
    
    # Try different speech recognition services
    services = [
        ("Google", r.recognize_google),
        ("Sphinx (offline)", r.recognize_sphinx),
    ]
    
    with sr.Microphone() as source:
        print("🎤 Speak now...")
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, timeout=10, phrase_time_limit=15)
    
    for service_name, recognize_func in services:
        try:
            print(f"🔄 Trying {service_name}...")
            if service_name == "Sphinx (offline)":
                text = recognize_func(audio)
            else:
                text = recognize_func(audio)
            
            print(f"✅ {service_name}: {text}")
            return text
            
        except sr.UnknownValueError:
            print(f"❌ {service_name} could not understand")
        except sr.RequestError as e:
            print(f"❌ {service_name} error: {e}")
        except Exception as e:
            print(f"❌ {service_name} failed: {e}")
    
    return None

def speech_to_text_realtime():
    """Real-time speech recognition with live transcription"""
    r = sr.Recognizer()
    r.energy_threshold = 4000
    r.dynamic_energy_threshold = False
    
    with sr.Microphone() as source:
        print("🎤 Real-time speech recognition starting...")
        r.adjust_for_ambient_noise(source)
    
    def callback(recognizer, audio):
        try:
            text = recognizer.recognize_google(audio)
            print(f"📝 Live: {text}")
        except sr.UnknownValueError:
            print("🔇 [silence]")
        except sr.RequestError as e:
            print(f"❌ Error: {e}")
    
    # Start background listening
    stop_listening = r.listen_in_background(sr.Microphone(), callback)
    
    print("🎙️ Listening in background... Press Enter to stop")
    input()
    stop_listening(wait_for_stop=False)
def hotword_detect_loop():
    porcupine = pvporcupine.create(keywords=["computer"])
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )

def test_microphone():
    """Test if microphone is working properly"""
    print("🎤 Testing microphone...")
    
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("📊 Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=2)
            
            print("🔊 Say 'test' to verify microphone...")
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            
            text = r.recognize_google(audio)
            print(f"✅ Microphone working! Heard: {text}")
            return True
            
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False

def speech():
    """Main speech function with menu"""
    print("🎙️ Speech-to-Text Tool")
    print("=" * 30)
    
    if not test_microphone():
        print("⚠️ Please check your microphone setup")
        return
    
    print("\nChoose mode:")
    print("1. Simple (one-time recognition)")
    print("2. Continuous (with hotword)")
    print("3. Multiple services")
    print("4. Real-time transcription")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        result = speech_to_text_simple()
        return result
    elif choice == "2":
        return speech_to_text_continuous()
    elif choice == "3":
        return speech_to_text_with_options()
    elif choice == "4":
        speech_to_text_realtime()
    else:
        return speech_to_text_simple()

if __name__ == "__main__":
    # Test the speech function
    result = speech()
    if result:
        print(f"\n🎯 Final result: {result}")