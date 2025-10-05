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
│  │Data API  │  │  FastAPI    │← Puerto 8989           │
│  │External  │  │  Inference  │                        │
│  └──────────┘  └─────────────┘                        │
│                                                         │
│  ┌──────────────────┐                                  │
│  │   Streamlit UI   │← Puerto 8503 (BONO)             │
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
| **Inference API**     | [http://10.43.100.103:8989](http://10.43.100.103:8989)     | Sin autenticación                                 |
| **API Docs**          | [http://10.43.100.103:8989/docs](http://10.43.100.103:8080/docs) | Documentación interactiva                         |
| **Streamlit UI**      | [http://10.43.100.103:8503](http://10.43.100.103:8503)   | Sin autenticación                                 |


### Estructura del Proyecto

```
Proyecto2/
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

└── ui/                        # Interfaz Gráfica (BONO)
    ├── Dockerfile
    ├── app.py
    └── requirements.txt
```








