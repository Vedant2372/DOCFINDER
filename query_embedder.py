from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

class QueryEmbedder:
    """
    Converts text queries and documents into vector embeddings using a sentence transformer.
    """

    def _init_(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            model_name (str): Pretrained model name to load from sentence-transformers.
        """
        print(f"🔍 Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string into a vector.

        Args:
            query (str): The search query text.
        
        Returns:
            np.ndarray: A (1, 384) shaped numpy array vector.
        """
        embedding = self.model.encode([query])
        return np.array(embedding)

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """
        Embed a list of document texts into vectors.

        Args:
            documents (List[str]): A list of document strings.
        
        Returns:
            np.ndarray: An (N, 384) shaped numpy array, where N is the number of documents.
        """
        embeddings = self.model.encode(documents, show_progress_bar=True)
        return np.array(embeddings)