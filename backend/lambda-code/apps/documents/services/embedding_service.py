"""
Embedding Service

Handles text embedding generation using multiple providers:
- OpenAI (text-embedding-3-small/large)
- Sentence Transformers (local, free)
"""
import hashlib
import logging
from typing import List, Optional
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Lazy loading for sentence_transformers to avoid OOM on low-memory servers
SENTENCE_TRANSFORMERS_AVAILABLE = None  # Will be set on first use
_sentence_transformer_model = None

def _check_sentence_transformers():
    """Lazily check if sentence_transformers is available."""
    global SENTENCE_TRANSFORMERS_AVAILABLE
    if SENTENCE_TRANSFORMERS_AVAILABLE is None:
        try:
            from sentence_transformers import SentenceTransformer
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except ImportError:
            SENTENCE_TRANSFORMERS_AVAILABLE = False
    return SENTENCE_TRANSFORMERS_AVAILABLE


class EmbeddingService:
    """
    Service for generating text embeddings.

    Supports multiple embedding providers with caching.
    """

    # Default models
    OPENAI_MODEL = 'text-embedding-3-small'
    LOCAL_MODEL = 'all-MiniLM-L6-v2'

    # Chunk settings
    MAX_CHUNK_SIZE = 1000  # characters
    CHUNK_OVERLAP = 200

    def __init__(self, provider: str = 'auto'):
        """
        Initialize the embedding service.

        Args:
            provider: 'openai', 'local', or 'auto' (tries openai first)
        """
        self.provider = self._determine_provider(provider)
        self._local_model = None
        self._openai_client = None

    def _determine_provider(self, provider: str) -> str:
        """Determine which provider to use."""
        if provider == 'auto':
            if OPENAI_AVAILABLE and getattr(settings, 'OPENAI_API_KEY', None):
                return 'openai'
            elif _check_sentence_transformers():
                return 'local'
            else:
                raise ImportError(
                    "No embedding provider available. Install openai or sentence-transformers."
                )
        return provider

    @property
    def openai_client(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None and OPENAI_AVAILABLE:
            self._openai_client = openai.OpenAI(
                api_key=getattr(settings, 'OPENAI_API_KEY', None)
            )
        return self._openai_client

    @property
    def local_model(self):
        """Lazy load local model."""
        if self._local_model is None and _check_sentence_transformers():
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.LOCAL_MODEL)
        return self._local_model

    def get_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> List[float]:
        """
        Get embedding for a single text.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            List of floats (embedding vector)
        """
        if use_cache:
            cached = self._get_cached_embedding(text)
            if cached is not None:
                return cached

        if self.provider == 'openai':
            embedding = self._openai_embed([text])[0]
        else:
            embedding = self._local_embed([text])[0]

        if use_cache:
            self._cache_embedding(text, embedding)

        return embedding

    def get_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use cached embeddings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Check cache for each text
        embeddings = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []

        if use_cache:
            for i, text in enumerate(texts):
                cached = self._get_cached_embedding(text)
                if cached is not None:
                    embeddings[i] = cached
                else:
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
        else:
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))

        # Embed remaining texts
        if texts_to_embed:
            if self.provider == 'openai':
                new_embeddings = self._openai_embed(texts_to_embed)
            else:
                new_embeddings = self._local_embed(texts_to_embed)

            for idx, embedding in zip(indices_to_embed, new_embeddings):
                embeddings[idx] = embedding
                if use_cache:
                    self._cache_embedding(texts[idx], embedding)

        return embeddings

    def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.OPENAI_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def _local_embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        try:
            embeddings = self.local_model.encode(texts)
            # Pad to 1536 dimensions to match OpenAI
            padded = []
            for emb in embeddings:
                emb_list = emb.tolist()
                if len(emb_list) < 1536:
                    emb_list.extend([0.0] * (1536 - len(emb_list)))
                padded.append(emb_list[:1536])
            return padded
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            raise

    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        from apps.documents.models import EmbeddingCache

        text_hash = self._get_text_hash(text)
        try:
            cache = EmbeddingCache.objects.get(text_hash=text_hash)
            return list(cache.embedding)
        except EmbeddingCache.DoesNotExist:
            return None

    def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache an embedding."""
        from apps.documents.models import EmbeddingCache

        text_hash = self._get_text_hash(text)
        model = self.OPENAI_MODEL if self.provider == 'openai' else self.LOCAL_MODEL

        EmbeddingCache.objects.update_or_create(
            text_hash=text_hash,
            defaults={
                'embedding': embedding,
                'model': model,
            }
        )

    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.MAX_CHUNK_SIZE
        overlap = overlap or self.CHUNK_OVERLAP

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                for sep in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def embed_document(
        self,
        document_id: int,
        chunk_size: int = None
    ) -> int:
        """
        Embed all chunks of a document.

        Args:
            document_id: Document ID to embed
            chunk_size: Optional chunk size override

        Returns:
            Number of chunks embedded
        """
        from apps.documents.models import Document, DocumentChunk

        document = Document.objects.get(id=document_id)

        # Delete existing chunks
        document.chunks.all().delete()

        # Create new chunks
        chunks = self.chunk_text(document.content, chunk_size)
        embeddings = self.get_embeddings(chunks)

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            DocumentChunk.objects.create(
                document=document,
                content=chunk_text,
                chunk_index=i,
                embedding=embedding,
                token_count=len(chunk_text.split()),
            )

        logger.info(f"Embedded document {document_id}: {len(chunks)} chunks")
        return len(chunks)
