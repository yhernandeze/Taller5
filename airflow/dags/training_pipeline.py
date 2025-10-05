from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import os
import json
from io import StringIO

# ENV
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
GROUP_NUMBER = os.getenv('GROUP_NUMBER', '6')
DATA_API_URL = os.getenv('DATA_API_URL', f'http://10.43.100.103:8080/data?group_number={GROUP_NUMBER}')

#Test
url = "http://10.43.100.103:8080/data?group_number=6"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

default_args = {
    'owner': 'mlops_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 30),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'forest_cover_training_pipeline',
    default_args=default_args,
    description='Pipeline completo de entrenamiento para Forest Cover Type',
    schedule_interval='*/10 * * * *',  # cada 10 min
    catchup=False,
    tags=['mlops', 'training', 'forest-cover'],
)

def fetch_data_from_api(**kwargs):
    #print(f"[fetch] URL={DATA_API_URL} group={GROUP_NUMBER}")
    r = requests.get(url, timeout=10)
    data = r.json()
    #print(f"\nGrupo: {data['group_number']}")
    #print(f"Batch: {data['batch_number']}")
    #print(f"Número de registros: {len(data['data'])}")
    
    # Convierte la lista de datos a DataFrame
    print("logramos tener un json")
    df = pd.DataFrame(data['data'])
    print("logramos tener un df")
    #df_ = df.to_csv(df)
    #print("logramos tener un csv")
    print(f"la longitud del df es: {len(df)}")
    #-----------
    #kwargs['ti'].xcom_push(key='raw_data_csv', value=df)
    #print("mandamos el csv en xcom")
    #return f"OK: {len(df)} chars"

def preprocess_data(**kwargs):
    ti = kwargs['ti']
    raw = ti.xcom_pull(key='raw_data_csv', task_ids='fetch_data')
    if not raw:
        raise ValueError("No data from API")
    df = pd.read_csv(StringIO(raw))
    df = df.dropna()
    if 'Cover_Type' not in df.columns:
        raise ValueError("Missing target 'Cover_Type'")
    X = df.drop('Cover_Type', axis=1)
    y = df['Cover_Type']
    # OHE si hubiera categóricas (dataset suele ser numérico, pero dejamos genérico)
    X = pd.get_dummies(X, drop_first=True)
    ti.xcom_push(key='X_json', value=X.to_json())
    ti.xcom_push(key='y_json', value=y.to_json())
    ti.xcom_push(key='feature_names', value=list(X.columns))
    return f"X={X.shape}, y={y.shape}"

def train_models(**kwargs):
    ti = kwargs['ti']
    X = pd.read_json(StringIO(ti.xcom_pull(key='X_json', task_ids='preprocess_data')))
    y = pd.read_json(StringIO(ti.xcom_pull(key='y_json', task_ids='preprocess_data')), typ='series')

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    experiment = "forest_cover_classification"
    mlflow.set_experiment(experiment)

    # Modelos como Pipelines (scaler + modelo)
    models = {
        'logistic_regression': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(max_iter=1000, random_state=42)),
        ]),
        'random_forest': Pipeline([
            ('scaler', StandardScaler(with_mean=False)),  # evita warnings con features binarias
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42)),
        ]),
        'gradient_boosting': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ]),
    }

    results = {}
    for name, pipe in models.items():
        with mlflow.start_run(run_name=f"{name}_{datetime.utcnow().isoformat()}"):
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'f1_score': f1_score(y_test, y_pred, average='weighted'),
                'precision': precision_score(y_test, y_pred, average='weighted'),
                'recall': recall_score(y_test, y_pred, average='weighted'),
            }
            mlflow.log_params({
                'model_type': name,
                'n_features': X_train.shape[1],
                'n_classes': y.nunique(),
                'train_samples': len(X_train),
                'test_samples': len(X_test),
            })
            mlflow.log_metrics(metrics)

            # registramos con un nombre estable por modelo
            mlflow.sklearn.log_model(
                pipe,
                artifact_path="model",
                registered_model_name=f"forest_cover_{name}"
            )
            results[name] = metrics

    ti.xcom_push(key='training_results', value=json.dumps(results))
    best = max(results.items(), key=lambda kv: kv[1]['accuracy'])
    return f"Best={best[0]} acc={best[1]['accuracy']:.4f}"

def evaluate_and_register_best(**kwargs):
    ti = kwargs['ti']
    results = json.loads(ti.xcom_pull(key='training_results', task_ids='train_models'))
    best_name = max(results.items(), key=lambda kv: kv[1]['accuracy'])[0]
    # (Opcional) Promoción a Production aquí si quieres centralizar
    return f"Selected model: {best_name}"

task_fetch_data = PythonOperator(task_id='fetch_data', python_callable=fetch_data_from_api, dag=dag)
task_preprocess = PythonOperator(task_id='preprocess_data', python_callable=preprocess_data, dag=dag)
task_train = PythonOperator(task_id='train_models', python_callable=train_models, dag=dag)
task_eval = PythonOperator(task_id='evaluate_and_register_best', python_callable=evaluate_and_register_best, dag=dag)

task_fetch_data >> task_preprocess >> task_train >> task_eval
 