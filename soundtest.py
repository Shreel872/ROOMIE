import pygame
import os
import subprocess 

def play_startup_sound():
    try:
        pygame.mixer.init()
        sound_path = "/mnt/c/Users/crick/Downloads/startup.mp3" #might want to change this later to make it work universally
        
        if os.path.exists(sound_path):
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            print("Startup sound played successfully")
        else:
            print("startup.mp3 not found at:", sound_path)
    except Exception as e:
        print(f"Could not play startup sound: {e}")
    finally:
        pygame.mixer.quit()

def play_startup_sound_ffplay():
    try:
        sound_path = "/mnt/c/Users/crick/Downloads/startup.mp3"
        
        if os.path.exists(sound_path):
            # Use ffplay for high-quality audio playback
            result = subprocess.run([
                'ffplay', '-nodisp', '-autoexit', '-v', 'quiet', sound_path
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                print("Sound played with ffplay")
            else:
                # Fallback to pygame
                play_startup_sound()
        else:
            print("startup.mp3 not found")
            
    except FileNotFoundError:
        print("ffplay not found. Install with: sudo apt install ffmpeg")
        play_startup_sound()  # Fallback
    except Exception as e:
        print(f"Could not play with ffplay: {e}")
        play_startup_sound()  # Fallback

def play_startup_sound_windows():
    try:
        # Use Windows path format for PowerShell
        sound_path = "C:\\Users\\crick\\Downloads\\startup.wav"  # or .mp3
        
        # Use Windows Media Player via PowerShell
        ps_command = f"""
        $player = New-Object -ComObject WMPlayer.OCX;
        $player.URL = '{sound_path}';
        $player.controls.play();
        Start-Sleep 4;
        $player.close();
        """
        
        result = subprocess.run([
            'powershell.exe', '-Command', ps_command
        ], capture_output=True, text=True, timeout=8)
        
        if result.returncode == 0:
            print("Sound played with Windows Media Player")
        else:
            print(f"PowerShell error: {result.stderr}")
            
    except Exception as e:
        print(f"Could not play with Windows Media Player: {e}")

# Test all methods
if __name__ == "__main__":
    print("Testing Windows Media Player method:")
    play_startup_sound_windows()
    
    print("\nTesting ffplay method:")
    play_startup_sound_ffplay()
    
    print("\nTesting pygame method:")

    play_startup_sound()
