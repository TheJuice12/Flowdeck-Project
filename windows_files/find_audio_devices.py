import sounddevice as sd
import json

print("\n--- Finding Default Audio Devices ---")
try:
    default_input = sd.query_devices(kind='input')
    default_output = sd.query_devices(kind='output')
    
    print("\n[SUCCESS] Found your default devices!")
    print("\nCOPY and PASTE the following names into 'config.json':\n")
    
    config_update = {
        "input_device_name": default_input['name'],
        "output_device_name": default_output['name']
    }
    
    print(json.dumps(config_update, indent=2))
    
    print("\n--------------------------------------------------------------")
    print("1. Open config.json")
    print("2. Replace the placeholder names under 'audio_devices' with the names printed above.")
    print("3. For voice effects to work, you need VB-Audio Cable.")
    print("4. Set your REAL microphone as the default Recording device in Windows.")
    print("5. Set 'CABLE Input' as the default Playback device in Windows.")
    print("--------------------------------------------------------------\n")
    
except Exception as e:
    print(f"\n[ERROR] Could not find default devices: {e}")
    print("Please make sure your devices are plugged in and set as default")
    print("in Windows Sound settings, then try again.")
