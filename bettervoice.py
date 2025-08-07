import edge_tts
import asyncio
import pygame
import os

async def speak_edge_tts(text, voice="en-GB-RyanNeural"):
    output_file = "/home/patel/roomie/roomie_response.wav"
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    
    if not os.path.exists(output_file):
        print(f"❌ WAV file not created")
        return
    
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=6, buffer=1024)
        
        # Use Sound instead of music for better compatibility
        sound = pygame.mixer.Sound(output_file)
        sound.play()
        
        # Wait for sound to finish
        while pygame.mixer.get_busy():
            pygame.time.wait(50)
        
        print("✅ Audio played successfully")
        
    except Exception as e:
        print(f"❌ Audio error: {e}")
    finally:
        pygame.mixer.quit()

# Test
asyncio.run(speak_edge_tts("what are you TAAAAAALking about"))