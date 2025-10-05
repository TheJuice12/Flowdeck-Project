import sounddevice as sd
from pedalboard import Pedalboard, Reverb, Delay, PitchShift
import json
import time
import os

STATE_FILE = 'fx_state.json'

def audio_processing_thread():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        input_device = config['audio_devices']['input_device_name']
        output_device = config['audio_devices']['output_device_name']
    except Exception as e:
        print(f"FATAL: Could not read audio devices from config.json: {e}")
        input("Press Enter to exit...")
        return
    
    board = Pedalboard([
        Reverb(room_size=0.1),
        Delay(delay_seconds=0.0, mix=0.0),
        PitchShift(semitones=0)
    ])

    print("--- Voice FX Processor Started ---")
    print(f"Input: {input_device}")
    print(f"Output: {output_device}")
    print("----------------------------------")

    def callback(indata, outdata, frames, time, status):
        if status: print(status)
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f: fx_state = json.load(f)
            else:
                fx_state = {}
        except (FileNotFoundError, json.JSONDecodeError): fx_state = {}

        board[0].room_size = fx_state.get('reverb', 0.0)
        board[1].delay_seconds = fx_state.get('echo', 0.0) * 0.5
        board[1].mix = 1.0 if fx_state.get('echo', 0.0) > 0.05 else 0.0
        board[2].semitones = (fx_state.get('pitch', 0.5) - 0.5) * 24
        
        outdata[:] = board(indata, 48000)

    try:
        with sd.Stream(device=(input_device, output_device),
                       samplerate=48000, blocksize=1024,
                       dtype='float32', channels=1, callback=callback):
            while True: time.sleep(1)
    except Exception as e:
        print(f"\n--- FATAL AUDIO ERROR ---")
        print(f"Voice FX Processor failed: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    audio_processing_thread()


