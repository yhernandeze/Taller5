import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(
    page_title="MLOps Forest Cover - UI",
    page_icon="🌲",
    layout="wide"
)

# URLs de los servicios
INFERENCE_API_URL = os.getenv('INFERENCE_API_URL', 'http://inference_api:8989')
MLFLOW_URL = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
AIRFLOW_URL = os.getenv('AIRFLOW_URL', 'http://airflow-webserver:8080')

# Título principal
st.title("🌲 Forest Cover Type Prediction System")
st.markdown("---")

# Sidebar para navegación
st.sidebar.title("Navegación")
page = st.sidebar.radio(
    "Selecciona una opción:",
    ["🏠 Inicio", "🔮 Predicción Individual", "📊 Predicción por Lote", "🤖 Gestión de Modelos", "📈 Monitoreo"]
)

# Funciones auxiliares
def get_available_models():
    """Obtener modelos disponibles"""
    try:
        response = requests.get(f"{INFERENCE_API_URL}/models", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener modelos: {str(e)}")
        return []

def load_model(model_name, version=None, stage="Production"):
    """Cargar modelo específico"""
    try:
        params = {}
        if version:
            params['version'] = version
        if stage:
            params['stage'] = stage
        
        response = requests.post(
            f"{INFERENCE_API_URL}/models/{model_name}/load",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return True, response.json()
    except Exception as e:
        return False, str(e)

def make_prediction(data):
    """Realizar predicción"""
    try:
        response = requests.post(
            f"{INFERENCE_API_URL}/predict",
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error en predicción: {str(e)}")
        return None

def get_current_model():
    """Obtener modelo actual"""
    try:
        response = requests.get(f"{INFERENCE_API_URL}/current-model", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

# Página: Inicio
if page == "🏠 Inicio":
    st.header("Sistema de Predicción de Cobertura Forestal")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📊 MLflow")
        st.markdown(f"[Abrir MLflow]({MLFLOW_URL})")
        st.info("Gestión de experimentos y modelos")
    
    with col2:
        st.subheader("🔄 Airflow")
        st.markdown(f"[Abrir Airflow]({AIRFLOW_URL})")
        st.info("Orquestación de pipelines")
    
    with col3:
        st.subheader("🚀 API Status")
        try:
            response = requests.get(f"{INFERENCE_API_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ API Online")
            else:
                st.error("❌ API Error")
        except:
            st.error("❌ API Offline")
    
    st.markdown("---")
    st.subheader("Modelo Actual en Uso")
    current_model = get_current_model()
    if current_model and 'model_name' in current_model:
        st.success(f"**Modelo:** {current_model['model_name']}")
        if 'loaded_at' in current_model:
            st.info(f"**Cargado:** {current_model['loaded_at']}")
    else:
        st.warning("No hay modelo cargado")
    
    st.markdown("---")
    st.subheader("Información del Sistema")
    st.markdown("""
    Este sistema permite:
    - ✅ Realizar predicciones de tipos de cobertura forestal
    - ✅ Gestionar múltiples modelos de ML
    - ✅ Monitorear experimentos y métricas
    - ✅ Orquestar pipelines de entrenamiento
    """)

# Página: Predicción Individual
elif page == "🔮 Predicción Individual":
    st.header("Predicción Individual")
    st.markdown("Ingresa los datos de un área forestal para predecir su tipo de cobertura")
    
    col1, col2 = st.columns(2)
    
    with col1:
        elevation = st.number_input("Elevación (metros)", min_value=0, value=2596)
        aspect = st.number_input("Aspecto (grados azimuth)", min_value=0, max_value=360, value=51)
        slope = st.number_input("Pendiente (grados)", min_value=0, max_value=90, value=3)
        horiz_hydro = st.number_input("Distancia Horiz. al Agua (m)", min_value=0, value=258)
        vert_hydro = st.number_input("Distancia Vert. al Agua (m)", value=0)
    
    with col2:
        horiz_road = st.number_input("Distancia Horiz. a Carreteras (m)", min_value=0, value=510)
        hillshade_9am = st.slider("Hillshade 9am", 0, 255, 221)
        hillshade_noon = st.slider("Hillshade Noon", 0, 255, 232)
        hillshade_3pm = st.slider("Hillshade 3pm", 0, 255, 148)
        horiz_fire = st.number_input("Distancia a Puntos de Fuego (m)", min_value=0, value=6279)
    
    if st.button("🔮 Realizar Predicción", type="primary"):
        with st.spinner("Realizando predicción..."):
            prediction_data = {
                "Elevation": elevation,
                "Aspect": aspect,
                "Slope": slope,
                "Horizontal_Distance_To_Hydrology": horiz_hydro,
                "Vertical_Distance_To_Hydrology": vert_hydro,
                "Horizontal_Distance_To_Roadways": horiz_road,
                "Hillshade_9am": hillshade_9am,
                "Hillshade_Noon": hillshade_noon,
                "Hillshade_3pm": hillshade_3pm,
                "Horizontal_Distance_To_Fire_Points": horiz_fire
            }
            
            result = make_prediction(prediction_data)
            
            if result:
                st.success("✅ Predicción realizada exitosamente")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Tipo de Cobertura", result['prediction'])
                
                with col2:
                    st.metric("Clasificación", result['prediction_label'])
                
                with col3:
                    if result.get('confidence'):
                        st.metric("Confianza", f"{result['confidence']:.2%}")
                    else:
                        st.metric("Confianza", "N/A")
                
                st.info(f"**Modelo usado:** {result['model_used']}")
                st.caption(f"Timestamp: {result['timestamp']}")

# Página: Predicción por Lote
elif page == "📊 Predicción por Lote":
    st.header("Predicción por Lote")
    st.markdown("Sube un archivo CSV para realizar predicciones masivas")
    
    # Plantilla de ejemplo
    st.subheader("📥 Formato del archivo")
    st.markdown("El archivo CSV debe tener las siguientes columnas:")
    
    example_df = pd.DataFrame({
        'Elevation': [2596],
        'Aspect': [51],
        'Slope': [3],
        'Horizontal_Distance_To_Hydrology': [258],
        'Vertical_Distance_To_Hydrology': [0],
        'Horizontal_Distance_To_Roadways': [510],
        'Hillshade_9am': [221],
        'Hillshade_Noon': [232],
        'Hillshade_3pm': [148],
        'Horizontal_Distance_To_Fire_Points': [6279]
    })
    
    st.dataframe(example_df)
    
    # Descargar plantilla
    csv = example_df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar Plantilla CSV",
        data=csv,
        file_name="template_forest_cover.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    # Subir archivo
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Archivo cargado: {len(df)} registros")
        st.dataframe(df.head())
        
        if st.button("🚀 Realizar Predicciones", type="primary"):
            with st.spinner("Procesando predicciones..."):
                data_list = df.to_dict('records')
                
                try:
                    response = requests.post(
                        f"{INFERENCE_API_URL}/predict/batch",
                        json={"data": data_list},
                        timeout=60
                    )
                    response.raise_for_status()
                    results = response.json()
                    
                    st.success("✅ Predicciones completadas")
                    
                    # Crear DataFrame con resultados
                    predictions_df = pd.DataFrame(results['predictions'])
                    
                    # Combinar con datos originales
                    result_df = pd.concat([df, predictions_df[['prediction', 'prediction_label']]], axis=1)
                    
                    st.dataframe(result_df)
                    
                    # Descargar resultados
                    csv_result = result_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar Resultados",
                        data=csv_result,
                        file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"Error en predicción por lote: {str(e)}")

# Página: Gestión de Modelos
elif page == "🤖 Gestión de Modelos":
    st.header("Gestión de Modelos")
    
    st.subheader("Modelos Disponibles")
    models = get_available_models()
    
    if models:
        st.success(f"✅ {len(models)} modelo(s) disponible(s)")
        
        for model in models:
            with st.expander(f"📦 {model}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Nombre:** {model}")
                    
                    # Opciones de carga
                    load_option = st.radio(
                        "Cargar como:",
                        ["Production", "Staging", "Latest"],
                        key=f"radio_{model}"
                    )
                
                with col2:
                    if st.button("Cargar Modelo", key=f"btn_{model}"):
                        with st.spinner(f"Cargando {model}..."):
                            success, result = load_model(model, stage=load_option)
                            
                            if success:
                                st.success(f"✅ Modelo {model} cargado")
                                st.rerun()
                            else:
                                st.error(f"❌ Error: {result}")
    else:
        st.warning("No hay modelos disponibles en MLflow")
        st.info("💡 Ejecuta el DAG de Airflow para entrenar modelos")
    
    st.markdown("---")
    
    st.subheader("Modelo Actual")
    current = get_current_model()
    if current and 'model_name' in current:
        st.success(f"**Modelo activo:** {current['model_name']}")
        if 'loaded_at' in current:
            st.info(f"**Cargado en:** {current['loaded_at']}")
    else:
        st.warning("No hay modelo cargado actualmente")

# Página: Monitoreo
elif page == "📈 Monitoreo":
    st.header("Monitoreo del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔗 Enlaces Rápidos")
        st.markdown(f"- [MLflow UI]({MLFLOW_URL})")
        st.markdown(f"- [Airflow UI]({AIRFLOW_URL})")
        st.markdown(f"- [API Docs]({INFERENCE_API_URL}/docs)")
    
    with col2:
        st.subheader("📊 Estado de Servicios")
        
        # Verificar API
        try:
            response = requests.get(f"{INFERENCE_API_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Inference API: Online")
            else:
                st.error("❌ Inference API: Error")
        except:
            st.error("❌ Inference API: Offline")
        
        # Verificar MLflow
        try:
            response = requests.get(f"{MLFLOW_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ MLflow: Online")
            else:
                st.error("❌ MLflow: Error")
        except:
            st.error("❌ MLflow: Offline")
    
    st.markdown("---")
    
    st.subheader("💡 Instrucciones de Uso")
    st.markdown("""
    ### Flujo de Trabajo Completo
    
    1. **Entrenamiento**
       - Accede a Airflow para ejecutar el DAG de entrenamiento
       - El DAG recolecta datos, entrena modelos y los registra en MLflow
    
    2. **Gestión de Modelos**
       - Ve a la pestaña "Gestión de Modelos" para seleccionar y cargar un modelo
       - Puedes cambiar entre diferentes modelos según necesites
    
    3. **Predicción**
       - Usa "Predicción Individual" para casos únicos
       - Usa "Predicción por Lote" para múltiples predicciones
    
    4. **Monitoreo**
       - Revisa MLflow para ver métricas y comparar modelos
       - Revisa Airflow para ver el historial de ejecuciones
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.info("""
**MLOps Project 2**  
Pontificia Universidad Javeriana  
Grupo 6
""")
