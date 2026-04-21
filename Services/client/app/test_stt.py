import asyncio
import websockets
import wave
import os

async def test_stt():
    # Path to the recorded WAV file (update if needed)
    wav_file = "recording_20260420_195858.wav"
    
    if not os.path.exists(wav_file):
        print(f"Error: {wav_file} not found. Run the mic client first to record audio.")
        return
    
    # Open WAV file and read raw audio data
    with wave.open(wav_file, 'rb') as wf:
        # Check format (should be 16kHz, 16-bit, mono)
        if wf.getframerate() != 16000 or wf.getsampwidth() != 2 or wf.getnchannels() != 1:
            print("Error: WAV file must be 16kHz, 16-bit, mono PCM.")
            return
        
        audio_data = wf.readframes(wf.getnframes())
    
    print(f"Loaded {len(audio_data)} bytes of audio data.")
    
    # Connect to STT WebSocket
    uri = "ws://localhost:8001/stt"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to STT service.")
            
            # Send audio data in chunks (3200 bytes like the client)
            chunk_size = 3200
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await websocket.send(chunk)
                print(f"Sent {len(chunk)} bytes.")
                await asyncio.sleep(0.1)  # Small delay to simulate real-time
            
            # Close the connection to signal end of audio
            await websocket.close()
            print("Closed connection. Check STT logs for transcripts.")
            
    except Exception as e:
        print(f"Error connecting to STT: {e}")

if __name__ == "__main__":
    asyncio.run(test_stt())
