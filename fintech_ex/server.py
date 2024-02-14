from flask import Flask, request, jsonify, abort
import json, os, signal, sys, requests, pickle, subprocess
from pathlib import Path
from flask_cors import CORS

# Replace 'ENV_VARIABLE_NAME' with the name of the environment variable you want to extract
api_env_var_name = 'API_URL'
# Get the value of the environment variable
api_url = os.getenv(api_env_var_name)

app = Flask(__name__)
CORS(app)


# Set the path to the directory within our resources (data, model etc.)
home_dir="/fintech_ex"
# Gramine path to the uploads UPLOAD_FOLDER
UPLOAD_FOLDER = Path(f"{home_dir}/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Accuracy and model file path
accuracy_file = f"{home_dir}/accuracy.txt"
model_file = f"{home_dir}/model.pkl"

# Check if there is a '.' in the file name (indicating an extension),
# also check if the extension is among those specified in ALLOWED_EXTENSIONS
ALLOWED_EXTENSIONS = {'csv'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get('/')
def test():
    return jsonify({'message': 'TEST'}), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_files = request.files.getlist('file')  # Get a list of uploaded files
    if not uploaded_files:
        return jsonify({'message': 'No files uploaded'}), 400

    for file in uploaded_files:
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'message': 'Invalid file(s) uploaded'}), 400
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

    return jsonify({'message': 'File received'}), 200



@app.route('/insert_ID', methods=['POST'])
def receive_ID():
    req_data = request.get_json()
    computation_ID = req_data["ID"]

    # Perform computation on the uploaded CSV file
    script_path = 'fintech_src.py'
    # Execute the script
    result = subprocess.run(['python', script_path], stdout=subprocess.PIPE)
    # Extract stdout
    stdout = result.stdout.decode('utf-8')
    print("Output of the script:")
    print(stdout)

    with open(accuracy_file, "r") as file:
        content = file.read()
        print(content)

    data = {'computation_ID': computation_ID, 'result': content}
    print(data)
    response = requests.post(api_url, json=data)

    if response.status_code == 200:
        print('POST request was successful!')
        print('Response content:')
        print(response.text)
    else:
        print(f'POST request failed with status code: {response.status_code}')
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({'message': 'Computation success'}), 200


if __name__ == '__main__':
    
    if not UPLOAD_FOLDER.exists():
        UPLOAD_FOLDER.mkdir(parents=True)
    current_UPLOAD_FOLDER = os.getcwd()
    #app.run(ssl_context=('cert.pem', 'key.pem'), port=9443, host='0.0.0.0') 
    app.run(port=9443, host='0.0.0.0')