# ROOMIE

## Virtual assistant protocol

ROOMIE is a virtual assistant that I have created to act as a central hub for my room that answers questions though an LLM when asked to do so aswell as doing designated tasks such as opening the lock on my door or turning the lights in my room on.

ROOMIE is developed in a LINUX environment and consists of 3 seperate machine learning models aswell as a text to voice model to bring ROOMIE to life. These models consist of a wake word detection model (currently using porcupine's pre made model for an MVP test), an Ollama3 LLM model and openAI's text to speech model.


# MVP criterions:

1. Leverage the ollama3 LLM to get responses to given text ✅
2. integrate a TTS model to get responses in speech instead of text ✅
3. integrate a voice detection protocol and leverage a pre existing speech recognition model to take voice commands that are then given to the LLM ✅
4. integrate a wake word detection protocol to only listen to commands when asked to do so ✅
5. integrate specific functions to open specific function such as open google or open a application based on location (end goal being a method that allows for a easily mappable application opening method) ✅
6. integrate a ngrok server to run a spotify API allowing for full control of spotify throught the voice assistant ✅

## parts under development
ROOMIE is 
