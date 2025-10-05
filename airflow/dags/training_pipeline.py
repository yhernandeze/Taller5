from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import json
import requests
import pandas as pd
import sqlalchemy as sa
from io import StringIO

# ML / Metrics / MLflow
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from mlflow.tracking import MlflowClient

# ===== ENV =====
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
GROUP_NUMBER = os.getenv('GROUP_NUMBER', '6')
# Si el profe dio host/IP distinto, cambialo vía DATA_API_URL env en compose
DATA_API_URL = os.getenv('DATA_API_URL', f'http://10.43.100.103:8080')
DATA_ENDPOINT = f"{DATA_API_URL}/data"
DATA_DB_URI = os.getenv('DATA_DB_URI', 'mysql+pymysql://mlflow_user:mlflow_pass@mysql:3306/datasets_db')

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
EXPERIMENT_NAME = "forest_cover_classification"

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
    description='Pipeline medallion: raw -> curated -> train -> promote',
    schedule_interval='*/10 * * * *',
    catchup=False,
    tags=['mlops', 'training', 'forest-cover'],
)

def _engine():
    return sa.create_engine(DATA_DB_URI, pool_pre_ping=True, future=True)

def fetch_data_from_api(**kwargs):
    """T1: Trae JSON de API externa e inserta directo en datasets_db.forest_raw"""
    params = {'group_number': GROUP_NUMBER}
    r = requests.get(DATA_ENDPOINT, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()

    batch = int(payload.get('batch_number', -1))
    data_list = payload.get('data', [])
    if not data_list:
        raise ValueError("API devolvió 0 registros")

    # Columnas del dataset (orden exacto)
    cols = [
        'Elevation','Aspect','Slope',
        'Horizontal_Distance_To_Hydrology','Vertical_Distance_To_Hydrology',
        'Horizontal_Distance_To_Roadways','Hillshade_9am','Hillshade_Noon','Hillshade_3pm',
        'Horizontal_Distance_To_Fire_Points','Wilderness_Area','Soil_Type','Cover_Type'
    ]
    df = pd.DataFrame(data_list, columns=cols)

    # Tipos numéricos
    num_cols = [c for c in cols if c not in ['Wilderness_Area','Soil_Type','Cover_Type']]
    for c in num_cols + ['Cover_Type']:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    df['batch'] = batch
    df['ingested_at'] = pd.Timestamp.utcnow()

    with _engine().begin() as conn:
        df.to_sql('forest_raw', con=conn, schema='datasets_db', if_exists='append', index=False)

    # Dejamos el batch en XCom (ligero) por conveniencia de logging
    kwargs['ti'].xcom_push(key='last_batch', value=batch)
    return f"RAW insertado: {len(df)} filas (batch={batch})"

def preprocess_data(**kwargs):
    """T2: Lee de forest_raw (último batch) → limpia/encodea → upsert en forest_curated"""
    ti = kwargs['ti']
    last_batch = ti.xcom_pull(key='last_batch', task_ids='fetch_data')
    if last_batch is None:
        raise ValueError("No hay batch previo en XCom")

    with _engine().begin() as conn:
        raw = pd.read_sql(
            sa.text("SELECT * FROM datasets_db.forest_raw WHERE batch = :b"),
            conn, params={"b": int(last_batch)}
        )

    if raw.empty:
        raise ValueError(f"batch={last_batch} no tiene filas en forest_raw")

    # Limpieza simple: dropna
    raw = raw.dropna(subset=['Elevation','Aspect','Slope',
                             'Horizontal_Distance_To_Hydrology','Vertical_Distance_To_Hydrology',
                             'Horizontal_Distance_To_Roadways','Hillshade_9am','Hillshade_Noon','Hillshade_3pm',
                             'Horizontal_Distance_To_Fire_Points','Wilderness_Area','Soil_Type','Cover_Type'])

    # Dejamos **curated** igual que raw (sin encodear aún) pero “limpio”
    curated = raw.drop(columns=['ingested_at']).copy()
    curated['processed_at'] = pd.Timestamp.utcnow()

    # Idempotencia por batch: borra si ya existía
    with _engine().begin() as conn:
        conn.execute(sa.text("DELETE FROM datasets_db.forest_curated WHERE batch = :b"), {"b": int(last_batch)})
        curated.to_sql('forest_curated', con=conn, schema='datasets_db', if_exists='append', index=False)

    return f"CURATED upsert: {len(curated)} filas (batch={last_batch})"

def train_models(**kwargs):
    """T3: Lee de forest_curated (toda la historia), entrena y loggea en MLflow"""
    with _engine().begin() as conn:
        df = pd.read_sql(sa.text("SELECT * FROM datasets_db.forest_curated"), conn)

    if df.empty:
        raise ValueError("curated vacío")

    # Split
    X = df.drop(columns=['Cover_Type','processed_at'])
    y = df['Cover_Type'].astype(int)

    # Columnas por tipo (numéricas vs categóricas)
    cat_cols = ['Wilderness_Area','Soil_Type']
    num_cols = [c for c in X.columns if c not in cat_cols + ['batch']]

    # Transformador reproducible (OneHotEncoder con handle_unknown=ignore)
    pre = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', drop=None), cat_cols),
        ],
        remainder='drop'
    )

    # Modelos (dentro del pipeline)
    models = {
        'logistic_regression': LogisticRegression(max_iter=1000, random_state=42),
        'random_forest': RandomForestClassifier(n_estimators=200, random_state=42),
        'gradient_boosting': GradientBoostingClassifier(n_estimators=150, random_state=42),
    }

    mlflow.set_experiment(EXPERIMENT_NAME)
    results = {}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    for name, clf in models.items():
        pipe = Pipeline(steps=[('pre', pre), ('clf', clf)])

        with mlflow.start_run(run_name=f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"):
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)

            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "f1_score": f1_score(y_test, y_pred, average="weighted"),
                "precision": precision_score(y_test, y_pred, average="weighted"),
                "recall": recall_score(y_test, y_pred, average="weighted"),
            }

            mlflow.log_params({
                "model_type": name,
                "n_features_raw": X_train.shape[1],
                "n_classes": int(y.nunique()),
                "train_samples": int(len(X_train)),
                "test_samples": int(len(X_test)),
                "n_batches": int(df['batch'].nunique()),
                "max_batch": int(df['batch'].max()),
            })
            mlflow.log_metrics(metrics)

            # Guarda dataset (pequeña muestra) como artefacto
            sample_csv = df.sample(min(1000, len(df))).to_csv(index=False)
            mlflow.log_text(sample_csv, artifact_file="data/sample_curated.csv")

            # Firma y log de modelo completo (pre + clf)
            mlflow.sklearn.log_model(
                pipe, artifact_path="model",
                registered_model_name=f"forest_cover_{name}"
            )

            results[name] = metrics

    # Guardamos resultados mínimos para la tarea siguiente
    kwargs['ti'].xcom_push(key='results_json', value=json.dumps(results))
    return f"Entrenados: {', '.join(results.keys())}"

def evaluate_and_register_best(**kwargs):
    """T4: Elige el mejor por accuracy y compara con Production; promueve si mejora"""
    ti = kwargs['ti']
    results = json.loads(ti.xcom_pull(key='results_json', task_ids='train_models'))
    best_name, best_metrics = max(results.items(), key=lambda kv: kv[1]['accuracy'])
    target_registered_name = f"forest_cover_{best_name}"

    client = MlflowClient()
    # Última versión que creamos (stage vacío) → la promovemos si mejora
    latest = client.get_latest_versions(target_registered_name, stages=[])
    if not latest:
        return f"No se encontró la última versión registrada de {target_registered_name}"

    # Ordena por version y toma la última
    mv_new = sorted(latest, key=lambda m: int(m.version))[-1]
    new_acc = best_metrics['accuracy']

    # Busca Production vigente (si existe)
    prod = client.get_latest_versions(target_registered_name, stages=["Production"])
    if prod:
        mv_prod = prod[0]
        # Recupera métricas del run Production
        run = mlflow.get_run(mv_prod.run_id)
        old_acc = run.data.metrics.get('accuracy')
        if old_acc is not None and new_acc <= old_acc:
            # No mejora → deja nota y no promueve
            client.set_model_version_tag(
                name=mv_new.name, version=mv_new.version,
                key="promotion_decision",
                value=f"NO_PROMOTE new_acc={new_acc:.4f} <= prod_acc={old_acc:.4f}"
            )
            return f"No promovido ({target_registered_name} v{mv_new.version}). new_acc={new_acc:.4f} <= prod_acc={old_acc:.4f}"

    # Mejora (o no había prod) → promueve y archiva lo demás
    client.transition_model_version_stage(
        name=mv_new.name, version=mv_new.version,
        stage="Production", archive_existing_versions=True
    )
    client.set_model_version_tag(
        name=mv_new.name, version=mv_new.version,
        key="promotion_decision",
        value=f"PROMOTED new_acc={new_acc:.4f}"
    )
    return f"Promovido {mv_new.name} v{mv_new.version} a Production (acc={new_acc:.4f})"

# ==== DAG tasks
task_fetch_data = PythonOperator(task_id='fetch_data', python_callable=fetch_data_from_api, dag=dag)
task_preprocess = PythonOperator(task_id='preprocess_data', python_callable=preprocess_data, dag=dag)
task_train = PythonOperator(task_id='train_models', python_callable=train_models, dag=dag)
task_eval = PythonOperator(task_id='evaluate_and_register_best', python_callable=evaluate_and_register_best, dag=dag)

task_fetch_data >> task_preprocess >> task_train >> task_eval
