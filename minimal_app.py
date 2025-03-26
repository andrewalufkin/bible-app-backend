# minimal_app.py
from flask import Flask, jsonify
import os

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'Hello from Bible App Backend!'})

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Test endpoint is working!'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': 'current_time'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 