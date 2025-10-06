# MLOps Pipeline - Recolección de Datos y Entrenamiento de Modelos
Este proyecto de MLOps está diseñado para construir un pipeline completo de entrenamiento y despliegue de un modelo de IA, utilizando herramientas como Airflow, MLflow, MinIO y Docker. Todo el entorno ha sido orquestado mediante docker-compose para facilitar su despliegue y asegurar la reproducibilidad.

El propósito principal del taller es recolectar datos proporcionados por una API externa ubicada en: [API](http://10.43.100.103:8080/docs)

Esta API entrega conjuntos de datos aleatorios que cambian cada 5 minutos. Para obtener una muestra representativa, es necesario realizar al menos una solicitud por cada uno de los 10 batches que se publican periódicamente. Los datos recolectados serán utilizados para:

- Entrenar un modelo de IA utilizando MLflow.
- Desplegar una API de inferencia que sirva predicciones basadas en ese modelo.

### Infrestructura del proyecto

La arquitectura del sistema está compuesta por múltiples servicios desplegados en contenedores Docker, cada uno con un rol específico en el flujo de MLOps:

- **MySQL**: Base de datos para almacenar el metadata store de MLflow, donde se guarda información relacionada con los experimentos, ejecuciones, métricas y artefactos.
- **MinIO**: Sistema de almacenamiento de objetos compatible con S3. Aquí se guardan los artefactos (modelos entrenados, datasets, etc.) generados por MLflow. 
- **MLfLOW**: Servidor de seguimiento de experimentos. Permite registrar ejecuciones, visualizar métricas, almacenar modelos y gestionar su ciclo de vida.
- **PostgreSQL**: Base de datos utilizada por Airflow para registrar información sobre la ejecución de los DAGs, tareas, historiales, etc.
- **Airflow** (Webserver & Scheduler): Herramienta de orquestación que permite programar y ejecutar flujos de trabajo (pipelines). En este proyecto, Airflow es responsable de recolectar los datos desde la API cada 5 minutos, procesarlos y activar flujos de entrenamiento.
- **API de interferencia**: Servicio que expone el modelo entrenado para realizar predicciones. Se conecta a MLflow para cargar modelos directamente desde el artifact store (MinIO).
- **UI (Streamlit)**: Aplicación web que permite a los usuarios interactuar de forma visual con el sistema, hacer inferencias, ver resultados y consultar métricas del modelo (TBC)
```
┌─────────────────────────────────────────────────────────┐
│                  Docker Compose                         │
│                                                         │
│  ┌──────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  │
│  │ Airflow  │→ │ MLflow  │→ │ MinIO  │  │  MySQL   │  │
│  │   DAG    │  │Tracking │  │ S3     │  │Metadata  │  │
│  └────┬─────┘  └────┬────┘  └────────┘  └──────────┘  │
│       │             │                                   │
│       ↓             ↓                                   │
│  ┌──────────┐  ┌─────────────┐                        │
│  │Data API  │  │  FastAPI    │← Puerto 8080           │
│  │External  │  │  Inference  │                        │
│  └──────────┘  └─────────────┘                        │
│                                                         │
│  ┌──────────────────┐                                  │
│  │   Streamlit UI   │← Puerto 8503              │
│  └──────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

### Volúmenes
Se han definido volúmenes persistentes para garantizar que los datos de las bases de datos y el almacenamiento de artefactos no se pierdan cuando se detienen los contenedores:

- **mysql_data**: Persistencia de la base de datos MySQL
- **minio_data**: Almacenamiento de objetos en MinIO
- **postgres_data**: Persistencia de la base de datos PostgreSQL

### Variables de Entorno:
* Credenciales de bases de datos
* Usuario y contraseña de MinIO
* Nombre del bucket
* URL de la API externa
* Número del grupo asignado: 6

### Acceso a los Servicios

Los servicios están disponibles en las siguientes direcciones:
| Servicio              | URL                                                       | Credenciales                                       |
|-----------------------|-----------------------------------------------------------|---------------------------------------------------|
| **Airflow**           | [http://10.43.100.103:8080](http://10.43.100.103:8080)     | usuario: `admin` / password: `admin`              |
| **MLflow**            | [http://10.43.100.103:5000](http://10.43.100.103:5000)     | Sin autenticación                                 |
| **MinIO Console**     | [http://10.43.100.103:9001](http://10.43.100.103:9001)     | usuario: `admin` / password: `supersecret`        |
| **Inference API**     | [http://10.43.100.103:8989](http://10.43.100.103:8080)     | Sin autenticación                                 |
| **API Docs**          | [http://10.43.100.103:8989/docs](http://10.43.100.103:8080/docs) | Documentación interactiva                         


### Estructura del Proyecto

```
taller5/
├── docker-compose.yml         # Orquestación de servicios
├── .env                       # Variables de entorno
├── README.md                  # Este archivo
│
├── airflow/                   # Servicio Airflow
│   ├── Dockerfile
│   ├── requirements.txt
│   └── dags/
│       └── training_pipeline.py
│
├── mlflow/                    # Servicio MLflow
│   └── Dockerfile
│
├── inference_api/             # API de Inferencia
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt

```

### Ejecución y Desempeño del Modelo

El proceso de entrenamiento del modelo es orquestado mediante Airflow, el cual se encarga de ejecutar periódicamente un DAG que recolecta datos desde la API externa, entrena distintos modelos como: Regresión Logistica, Random forest y  Gradient boosting registrando los resultados en MLflow.

<img width="1428" height="535" alt="Airflow-batch6" src="https://github.com/user-attachments/assets/c6ec57bf-dea6-4563-b77f-45ae8d0d08f6" />


Cada vez que se ejecuta este pipeline, se lanza una nueva ejecución (run) en MLflow, donde se registran las métricas de desempeño como: accuracy, f1_score, precision y recall y los hiperparámetros del modelo entrenado. Esto permite comparar fácilmente los resultados entre distintas configuraciones y algoritmos.

En la pestaña "Experimental" de MLflow, se puede visualizar el desempeño de cada uno de los modelos entrenados. A continuación se resumen los registros mostrados en la imagen:


### ¿Qué sucede en cada registro?
Cada registro representa la ejecución de un modelo específico:

- **gradient_boosting**: Se ejecuta con parámetros predeterminados dentro del DAG y registra sus métricas de evaluación tras entrenar con los datos recolectados de batch.
- **random_forest**: valúa su rendimiento y guarda el modelo en MinIO vía MLflow
- **Logistic_regression** Funciona como baseline o comparativo frente a modelos más complejos
  
<img width="1434" height="782" alt="Experimentos" src="https://github.com/user-attachments/assets/29a5761f-c543-493a-945d-ebb6fd209024" />

Cada ejecución incluye el tracking automático del modelo, sus hiperparámetros, artefactos y métricas, lo que permite un análisis comparativo robusto.

Al correrse 6 batch exitosamente observamos lo siguiente:

### Observaciones Clave

| Métrica     | Mejor Modelo         | Valor Máximo |
|-------------|----------------------|--------------|
| Accuracy    | Gradient Boosting    | 0.97         |
| F1-Score    | Gradient Boosting    | 0.97         |
| Precision   | Gradient Boosting    | 0.99         |
| Recall      | Gradient Boosting    | 0.97         |

- El modelo **Gradient Boosting** muestra el mejor rendimiento general, con métricas destacadas en todos los indicadores de evaluación.
- **Random Forest** también ofrece un desempeño sólido, con valores cercanos al 0.91–0.96.
- **Logistic Regression**, como modelo base (baseline), tiene un rendimiento menor (~0.74–0.76), siendo útil como punto de comparación.

###  Conclusión
MLflow permite comparar de forma efectiva los modelos generados por el pipeline de MLOps. Con base en estas ejecuciones, **Gradient Boosting** es el modelo con mejor desempeño y se considera el candidato ideal para ser desplegado a través de la API de inferencia.

MLflow permite compar














