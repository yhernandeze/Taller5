# MLOps Pipeline - Recolección de Datos y Entrenamiento de Modelos
Este proyecto de MLOps está diseñado para construir un pipeline completo de entrenamiento y despliegue de un modelo de IA, utilizando herramientas como Airflow, MLflow, MinIO y Docker. Todo el entorno ha sido orquestado mediante docker-compose para facilitar su despliegue y asegurar la reproducibilidad.

El propósito principal del taller es recolectar datos proporcionados por una API externa ubicada en: [Link](http://10.43.100.103:8080/docs)

Esta API entrega conjuntos de datos aleatorios que cambian cada 5 minutos. Para obtener una muestra representativa, es necesario realizar al menos una solicitud por cada uno de los 10 batches que se publican periódicamente. Los datos recolectados serán utilizados para:

- Entrenar un modelo de IA utilizando MLflow.
- Desplegar una API de inferencia que sirva predicciones basadas en ese modelo.

### Infrestructura del proyecto

La arquitectura del sistema está compuesta por múltiples servicios desplegados en contenedores Docker, cada uno con un rol específico en el flujo de MLOps:

MySQL: Base de datos para almacenar el metadata store de MLflow, donde se guarda información relacionada con los experimentos, ejecuciones, métricas y artefactos.
  
MinIO: Sistema de almacenamiento de objetos compatible con S3. Aquí se guardan los artefactos (modelos entrenados, datasets, etc.) generados por MLflow.
  
MLfLOW: Servidor de seguimiento de experimentos. Permite registrar ejecuciones, visualizar métricas, almacenar modelos y gestionar su ciclo de vida.
  
PostgreSQL: Base de datos utilizada por Airflow para registrar información sobre la ejecución de los DAGs, tareas, historiales, etc.

Airflow (Webserver & Scheduler): Herramienta de orquestación que permite programar y ejecutar flujos de trabajo (pipelines). En este proyecto, Airflow es responsable de recolectar los datos desde la API cada 5 minutos, procesarlos y activar flujos de entrenamiento.

API de interferencia: Servicio que expone el modelo entrenado para realizar predicciones. Se conecta a MLflow para cargar modelos directamente desde el artifact store (MinIO).

UI (Streamlit): Aplicación web que permite a los usuarios interactuar de forma visual con el sistema, hacer inferencias, ver resultados y consultar métricas del modelo (TBC)




