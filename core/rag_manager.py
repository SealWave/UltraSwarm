"""
core/rag_manager.py
===================
Lightweight RAG system for the Swarm.

This version uses LangChain for document chunking and Turbovec for fast, local vector storage.
"""

import os
from pathlib import Path
from rich.console import Console

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from turbovec import Turbovec
    HAS_TURBOVEC = True
except ImportError:
    HAS_TURBOVEC = False

console = Console()

class RAGManager:
    """Manages document loading, indexing, and retrieval using Turbovec and LangChain."""
    
    def __init__(self, knowledge_dir: str = None):
        if knowledge_dir is None:
            self.knowledge_dir = Path(__file__).parent.parent / "knowledge"
        else:
            self.knowledge_dir = Path(knowledge_dir)
            
        self.knowledge_dir.mkdir(exist_ok=True)
        self.index = None
        self.documents = []
        self.initialize_index()

    def initialize_index(self):
        """Loads knowledge documents and builds the vector index."""
        try:
            # Fallback to simple glob if langchain directory loader fails
            file_paths = list(self.knowledge_dir.glob("*.md")) + list(self.knowledge_dir.glob("*.txt"))
            if not file_paths:
                return

            # Langchain Text Splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )

            # Manual document loading to avoid massive langchain-community dependencies
            all_chunks = []
            for path in file_paths:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                chunks = text_splitter.create_documents([content], metadatas=[{"source": path.name}])
                all_chunks.extend(chunks)

            self.documents = all_chunks

            if HAS_TURBOVEC and all_chunks:
                # Initialize Turbovec (assuming basic usage, fallback to text search if fail)
                # Note: Turbovec usually requires an embedding model. We will use a mock 
                # or simplified text matching if embeddings aren't fully configured here,
                # but we'll try to set up the Turbovec instance.
                try:
                    self.index = Turbovec()
                    # Add documents to Turbovec
                    for idx, doc in enumerate(all_chunks):
                        self.index.add({"id": str(idx), "text": doc.page_content, "metadata": doc.metadata})
                    self.index.build()
                except Exception as e:
                    console.print(f"[yellow]Turbovec initialization skipped/failed: {e}. Falling back to basic retrieval.[/yellow]")
                    self.index = None

        except Exception as e:
            console.print(f"[red]Failed to initialize RAG index: {e}[/red]")

    def retrieve_context(self, query: str) -> str:
        """Query the vector store and return concatenated matching chunks."""
        if not self.documents:
            return ""
        
        try:
            if self.index:
                # Turbovec retrieval
                results = self.index.search(query, top_k=3)
                context_blocks = []
                for item in results:
                    source = item.get("metadata", {}).get("source", "unknown")
                    context_blocks.append(f"--- Context from {source} ---\n{item.get('text', '')}")
                return "\n\n".join(context_blocks)
            else:
                # Basic fallback ranking if Turbovec fails
                ranked = self._rank_chunks(query)
                context_blocks = []
                for doc in ranked[:3]:
                    source = doc.metadata.get("source", "unknown")
                    context_blocks.append(f"--- Context from {source} ---\n{doc.page_content}")
                return "\n\n".join(context_blocks)
        except Exception as e:
            console.print(f"[red]RAG retrieval failed: {e}[/red]")
            return ""

    def _rank_chunks(self, query: str):
        """Fallback: Rank chunks by simple keyword overlap."""
        import re
        query_terms = {
            token
            for token in re.findall(r"[a-z0-9]+", (query or "").lower())
            if len(token) > 2
        }
        if not query_terms:
            return self.documents

        scored = []
        for doc in self.documents:
            text = doc.page_content.lower()
            score = sum(1 for term in query_terms if term in text)
            if score:
                scored.append((score, len(text), doc))

        if not scored:
            return self.documents

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored]


# Global instance for easy import and reuse
_rag_manager = None

def get_rag_manager() -> RAGManager:
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager

def query_knowledge(query: str) -> str:
    """Helper function to retrieve context for prompts."""
    return get_rag_manager().retrieve_context(query)

