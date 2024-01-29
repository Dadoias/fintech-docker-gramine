from flask import Flask, request, jsonify, abort
import json, os, signal, sys, requests, pickle
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from flask_cors import CORS
import functools

# to flush the print in gramine (sometime it gets stucked)
print = functools.partial(print, flush=True)

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

# Conttrolla se c'è '.' nel nome del file (quindi un estensione), inoltre controlla se l'estenione è tra quelle indicate in ALLOWED_EXTENTIONS
ALLOWED_EXTENSIONS = {'csv'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_in_files():
    map = (
        pd.read_csv(UPLOAD_FOLDER / "ca_relation_typed.csv")[["person_key", "account_key"]]
        .drop_duplicates("account_key", keep="first")
        .drop_duplicates("person_key", keep="first")
    )
    account = pd.read_csv(UPLOAD_FOLDER / "account_typed.csv").join(
        map.set_index("account_key"), on="account_key"
    )
    account = account[~account.person_key.isna()]
    deposit = pd.read_csv(UPLOAD_FOLDER / "deposit_account_typed.csv").join(
        map.set_index("person_key"), on="person_key"
    )
    deposit = deposit[~deposit.account_key.isna()]
    payment = pd.read_csv(UPLOAD_FOLDER / "payment_typed.csv").join(
        map.set_index("account_key"), on="account_key"
    )
    payment = payment[~payment.person_key.isna()]
    person = pd.read_csv(UPLOAD_FOLDER / "person_typed.csv").join(
        map.set_index("person_key"), on="person_key"
    )
    person = person[~person.account_key.isna()]

    return account, deposit, payment, person


def clean_files(account, deposit, payment, person):
    account = account[
        [
            "account_key",
            "base_interest_rate",
            "repay_frequency",
            "number_of_total_installments",
            "delay_days",
            "overdue_expenses",
            "total_balance",
            "collateral_amount",
        ]
    ]

    min_delay = account.delay_days.min()
    max_delay = account.delay_days.max()
    # Create a copy of the DataFrame to avoid chained indexing issues
    account_copy = account.copy()
    account_copy.loc[:, 'delay_days'] = account_copy['delay_days'].apply(
        lambda x: ((x - min_delay) / (max_delay - min_delay)) * 210
    )
    deposit = deposit[
        [
            "account_key",
            "accounting_balance",
            "available_balance",
        ]
    ]
    payment = payment[
        [
            "account_key", 
            "capital_amount", 
            "payinterest", 
            "payexpenses"
        ]
    ]
    person = person[
        [
            "marital_status",
            "gender",
            "account_key",
        ]
    ]
    return account_copy, deposit, payment, person


def join_files(account, deposit, payment, person):
    df = (
        (
            account.join(deposit.set_index("account_key"), on="account_key")
            .join(payment.set_index("account_key"), on="account_key")
            .join(person.set_index("account_key"), on="account_key")
        )
        .drop("account_key", axis=1)
        .reset_index(drop=True)
    )

    df.marital_status.fillna("single", inplace=True)
    df.gender.fillna("M", inplace=True)
    df.fillna(0, inplace=True)

    return df


def feature_engineering_train_test_split(df):
    categorical_columns = ["gender", "marital_status"]
    categories = pd.get_dummies(df[categorical_columns], drop_first=True)
    df[categories.columns] = categories
    df.drop(categorical_columns, axis=1, inplace=True)

    df["target_variable"] = df.delay_days.apply(lambda x: 1 if x > 180 else 0)
    df.drop("delay_days", axis=1, inplace=True)

    X_train, X_test, y_train, y_test = train_test_split(
        df.drop(columns=["target_variable"]),
        df.target_variable,
        test_size=0.2,
        stratify=df.target_variable,
        random_state=42,
    )

    columns_to_scale = [
        "base_interest_rate",
        "repay_frequency",
        "number_of_total_installments",
        "overdue_expenses",
        "total_balance",
        "collateral_amount",
        "accounting_balance",
        "available_balance",
        "capital_amount",
        "payinterest",
        "payexpenses",
    ]

    scaler = StandardScaler().fit(X_train[columns_to_scale])
    X_train[columns_to_scale] = scaler.transform(X_train[columns_to_scale])
    X_test[columns_to_scale] = scaler.transform(X_test[columns_to_scale])
    #print( 'variabili', X_train, X_test, y_train, y_test)
    return X_train, X_test, y_train, y_test


def fit_model(X_train, y_train):
    rf = RandomForestClassifier(random_state=42).fit(X_train, y_train)
    return rf


def write_accuracy_to_file(rf, X_test, y_test):
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    try:
        with open(accuracy_file, "w") as file:
            file.write(f"The accuracy of the model was: {accuracy:.4f}")
            print('writing the file')
    except:
        print ("Could not open/read file:", "accuracy.txt")
        sys.exit()




@app.get('/')
def test():
    return jsonify({'message': 'PROVA'}), 200

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
    accounts, deposits, payments, persons = read_in_files()
    accounts, deposits, payments, persons = clean_files(accounts, deposits, payments, persons)
    full_df = join_files(accounts, deposits, payments, persons)
    X_train, X_test, y_train, y_test = feature_engineering_train_test_split(full_df)
    model = fit_model(X_train, y_train)
    write_accuracy_to_file(model, X_test, y_test)

    with open(accuracy_file, "r") as file:
        content = file.read()
        print(content)

    pickle.dump(model, open(model_file, "wb"))

    url = 'http://10.0.0.6:9000/computation_output'
    data = {'computation_ID': computation_ID, 'result': content}
    print(data)
    response = requests.post(url, json=data)

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