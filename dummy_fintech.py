import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DIRECTORY = Path("./data")


def read_in_files():
    map = (
        pd.read_csv(DIRECTORY / "ca_relation_typed.csv")[["person_key", "account_key"]]
        .drop_duplicates("account_key", keep="first")
        .drop_duplicates("person_key", keep="first")
    )

    account = pd.read_csv(DIRECTORY / "account_typed.csv").join(
        map.set_index("account_key"), on="account_key"
    )
    account = account[~account.person_key.isna()]
    deposit = pd.read_csv(DIRECTORY / "deposit_account_typed.csv").join(
        map.set_index("person_key"), on="person_key"
    )
    deposit = deposit[~deposit.account_key.isna()]
    payment = pd.read_csv(DIRECTORY / "payment_typed.csv").join(
        map.set_index("account_key"), on="account_key"
    )
    payment = payment[~payment.person_key.isna()]
    person = pd.read_csv(DIRECTORY / "person_typed.csv").join(
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

    payment = payment[["account_key", "capital_amount", "payinterest", "payexpenses"]]

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

    return X_train, X_test, y_train, y_test


def fit_model(X_train, y_train):
    rf = RandomForestClassifier(random_state=42).fit(X_train, y_train)
    return rf


def write_accuracy_to_file(rf, X_test, y_test):
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    with open("accuracy.txt", "w") as file:
        file.write(f"The accuracy of the model was: {accuracy:.4f}")


if __name__ == "__main__":
    accounts, deposits, payments, persons = read_in_files()
    accounts, deposits, payments, persons = clean_files(
        accounts, deposits, payments, persons
    )
    full_df = join_files(accounts, deposits, payments, persons)
    X_train, X_test, y_train, y_test = feature_engineering_train_test_split(full_df)
    model = fit_model(X_train, y_train)
    write_accuracy_to_file(model, X_test, y_test)
    pickle.dump(model, open("model.pkl", "wb"))