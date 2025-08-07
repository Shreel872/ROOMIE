import pvporcupine
import pyaudio
import struct
from vosk import Model, KaldiRecognizer
import pyaudio
import json
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
            stream.stop_stream()
            stream.close()
            pa.terminate()
            porcupine.delete()
            return True
def speechrecognition():
    model = Model("/mnt/c/Users/crick/Downloads/vosk-model-en-us-0.22-lgraph/vosk-model-en-us-0.22-lgraph")  # Download from: https://alphacephei.com/vosk/models
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


def main():
    print("TESTING HOTKEY")
    print("8"*50)
    while True:
        try:
            # Wait for hotword
            if hotword_detect_loop():
                # Hotword detected, now listen for speech
                command = speechrecognition()
                if command:
                    print(f"Final command: {command}")
                    break
                else:
                    print("❌ No command detected, listening for hotword again...")
            else:
                break
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break

if __name__ == "__main__":
    main()