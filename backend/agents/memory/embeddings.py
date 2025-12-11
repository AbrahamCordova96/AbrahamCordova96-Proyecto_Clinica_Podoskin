"""
Embeddings Generation - Fase 3
==============================

Genera embeddings vectoriales para búsqueda semántica usando
sentence-transformers/all-MiniLM-L6-v2.

Características del modelo:
- Dimensiones: 384
- Idiomas: Multi-idioma (español incluido)
- Velocidad: ~400 textos/segundo en CPU
- Tamaño: ~22MB

Autor: Sistema
Fecha: 11 de Diciembre, 2025
Fase: 3 - Memoria Semántica
"""

import logging
from typing import List, Union
from functools import lru_cache

logger = logging.getLogger(__name__)

# Global model cache
_model = None


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Obtiene el modelo de embeddings (singleton con cache).
    
    Usa sentence-transformers para generar embeddings de 384 dimensiones.
    El modelo se carga una sola vez y se reutiliza.
    
    Returns:
        SentenceTransformer model
    """
    global _model
    
    if _model is not None:
        return _model
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info("🔧 Cargando modelo de embeddings: all-MiniLM-L6-v2")
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("✅ Modelo de embeddings cargado correctamente")
        
        return _model
    
    except ImportError:
        logger.error(
            "❌ sentence-transformers no está instalado. "
            "Instalar con: pip install sentence-transformers"
        )
        raise
    except Exception as e:
        logger.error(f"❌ Error cargando modelo de embeddings: {e}")
        raise


def generate_embedding(text: str) -> List[float]:
    """
    Genera embedding vectorial para un texto.
    
    Args:
        text: Texto para generar embedding
        
    Returns:
        Lista de 384 floats representando el embedding
        
    Example:
        >>> embedding = generate_embedding("paciente diabético")
        >>> len(embedding)
        384
        >>> isinstance(embedding[0], float)
        True
    """
    if not text or not text.strip():
        logger.warning("⚠️ Texto vacío para embedding, retornando vector cero")
        return [0.0] * 384
    
    try:
        model = get_embedding_model()
        
        # Generar embedding
        embedding = model.encode(text, convert_to_numpy=True)
        
        # Convertir a lista de floats
        embedding_list = embedding.tolist()
        
        logger.debug(f"✅ Embedding generado: {len(embedding_list)} dimensiones")
        
        return embedding_list
    
    except Exception as e:
        logger.error(f"❌ Error generando embedding: {e}")
        # Retornar vector cero en caso de error
        return [0.0] * 384


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Genera embeddings para múltiples textos de forma eficiente.
    
    Args:
        texts: Lista de textos
        batch_size: Tamaño del batch para procesamiento
        
    Returns:
        Lista de embeddings (cada uno es lista de 384 floats)
        
    Example:
        >>> texts = ["diabetes", "hipertensión", "podología"]
        >>> embeddings = generate_embeddings_batch(texts)
        >>> len(embeddings)
        3
        >>> all(len(e) == 384 for e in embeddings)
        True
    """
    if not texts:
        return []
    
    # Filtrar textos vacíos
    valid_texts = [t if t and t.strip() else " " for t in texts]
    
    try:
        model = get_embedding_model()
        
        # Generar embeddings en batch (más eficiente)
        embeddings = model.encode(
            valid_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
        
        # Convertir a lista de listas
        embeddings_list = [emb.tolist() for emb in embeddings]
        
        logger.info(f"✅ {len(embeddings_list)} embeddings generados en batch")
        
        return embeddings_list
    
    except Exception as e:
        logger.error(f"❌ Error generando embeddings en batch: {e}")
        # Retornar vectores cero en caso de error
        return [[0.0] * 384 for _ in texts]


def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calcula similitud coseno entre dos embeddings.
    
    Args:
        embedding1: Primer embedding (384 dims)
        embedding2: Segundo embedding (384 dims)
        
    Returns:
        Similitud entre 0 (no relacionado) y 1 (idéntico)
        
    Example:
        >>> e1 = generate_embedding("diabetes")
        >>> e2 = generate_embedding("diabético")
        >>> similarity = cosine_similarity(e1, e2)
        >>> similarity > 0.8  # Muy similar
        True
    """
    import numpy as np
    
    # Convertir a arrays numpy
    a = np.array(embedding1)
    b = np.array(embedding2)
    
    # Calcular coseno
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    similarity = dot_product / (norm_a * norm_b)
    
    return float(similarity)
