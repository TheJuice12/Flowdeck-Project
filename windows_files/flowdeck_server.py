import json
import threading
from flask import Flask, jsonify, request
from comtypes import CoInitialize
import audio_controls

# --- Globals ---
config = {}
app = Flask(__name__)

# --- Configuration Loading ---
def load_config():
    """Loads the main configuration and initializes the voice FX state file."""
    global config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            # Initialize the fx_state.json with the first preset's values on startup
            if config.get("voice_presets"):
                with open("fx_state.json", 'w') as fx_file:
                    json.dump(config["voice_presets"][0]["values"], fx_file)
            print("Config loaded and fx_state.json initialized.")
    except Exception as e:
        print(f"FATAL: Could not load config.json: {e}")
        exit()

# --- API Endpoints ---
@app.route('/state', methods=['GET'])
def get_state():
    """API endpoint for the Raspberry Pi to poll for the current system audio state."""
    state = { "audio": {"master": {}, "groups": []}, "voice": {} }
    com_thread = threading.Thread(target=audio_controls.update_full_state, args=(state, config))
    com_thread.start()
    com_thread.join()
    return jsonify(state)

@app.route('/config', methods=['GET'])
def get_config():
    """API endpoint for the Pi to fetch the initial configuration data."""
    return jsonify(config)

@app.route('/control', methods=['POST'])
def control():
    """API endpoint to receive and process all commands from the Raspberry Pi."""
    data = request.get_json()
    if not data or not data.get("action"):
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    
    action_thread = threading.Thread(target=audio_controls.handle_command, args=(data, config))
    action_thread.start()
    
    return jsonify({"status": "success", "action_triggered": data.get("action")})

# --- Main Execution ---
if __name__ == '__main__':
    CoInitialize()
    load_config()
    print("FlowDeck Flask Server starting at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)

