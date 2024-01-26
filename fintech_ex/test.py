from flask import Flask, request, jsonify, abort
import os
import sys
from pathlib import Path
import json, os, signal



app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DIRECTORY = Path("./uploads")

@app.route('/', methods=['GET'])
def test():
    return jsonify({'message': 'File received'}), 200

@app.route("/shutdown", methods=['GET'])
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({ "success": True, "message": "Server is shutting down..." })



if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(port=5000, host='0.0.0.0')
