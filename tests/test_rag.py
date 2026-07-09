"""
tests/test_rag.py
=================
Tests for RAG (Retrieval-Augmented Generation) functionality.
Tests document loading, indexing, and retrieval.
"""

import pytest
import os
import tempfile
from pathlib import Path

try:
    from core.rag_manager import RAGManager, get_rag_manager, query_knowledge
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    RAGManager = None
    get_rag_manager = None
    query_knowledge = None


class TestRAGManager:
    """Test RAG manager functionality"""

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_rag_manager_creation(self):
        """Test that RAG manager can be created"""
        rag = RAGManager()
        assert rag is not None

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_rag_manager_with_custom_dir(self):
        """Test RAG manager with custom knowledge directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test knowledge file
            test_file = Path(tmpdir) / "test_knowledge.txt"
            test_file.write_text("This is test knowledge content for RAG testing.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            assert rag.knowledge_dir == Path(tmpdir)
            assert len(rag.documents) > 0

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_rag_manager_empty_dir(self):
        """Test RAG manager with empty knowledge directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGManager(knowledge_dir=tmpdir)
            
            # Should handle gracefully
            assert rag.documents == []

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_retrieve_context_from_documents(self):
        """Test retrieving context from loaded documents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test documents
            test_file = Path(tmpdir) / "python_guide.txt"
            test_file.write_text("""
            Python Programming Guide
            ========================
            
            Python is a high-level programming language known for its simplicity
            and readability. It supports multiple programming paradigms including
            procedural, object-oriented, and functional programming.
            
            Key features of Python:
            - Easy to learn and use
            - Extensive standard library
            - Dynamic typing
            - Automatic memory management
            """)
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            # Query for Python-related content
            context = rag.retrieve_context("What is Python?")
            
            # Should return relevant context
            assert context is not None
            assert isinstance(context, str)

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_retrieve_context_empty_documents(self):
        """Test retrieving context when no documents are loaded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGManager(knowledge_dir=tmpdir)
            
            context = rag.retrieve_context("any query")
            
            assert context == ""

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_document_chunking(self):
        """Test that documents are properly chunked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a longer document
            long_content = "Test content. " * 500  # Create content that will be chunked
            test_file = Path(tmpdir) / "long_document.txt"
            test_file.write_text(long_content)
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            # Documents should be chunked
            assert len(rag.documents) > 0
            # Each chunk should have page_content attribute
            for doc in rag.documents:
                assert hasattr(doc, 'page_content')
                assert hasattr(doc, 'metadata')

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_multiple_documents(self):
        """Test loading multiple documents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple test files
            for i in range(3):
                test_file = Path(tmpdir) / f"doc_{i}.txt"
                test_file.write_text(f"Document {i} content for testing.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            assert len(rag.documents) >= 3

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_markdown_document_loading(self):
        """Test loading markdown documents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "test_guide.md"
            md_file.write_text("""
            # Test Guide
            
            This is a markdown document for testing.
            
            ## Section 1
            Content in section 1.
            
            ## Section 2
            Content in section 2.
            """)
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            assert len(rag.documents) > 0

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_query_knowledge_function(self):
        """Test the query_knowledge helper function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test knowledge for query.")
            
            # Create a new RAG manager with the test directory
            global _rag_manager
            from core import rag_manager
            rag_manager._rag_manager = None
            
            rag = RAGManager(knowledge_dir=tmpdir)
            rag_manager._rag_manager = rag
            
            result = query_knowledge("test query")
            
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_fallback_ranking(self):
        """Test fallback keyword ranking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create documents with different keywords
            docs = [
                ("python_intro.txt", "Python is a programming language."),
                ("java_intro.txt", "Java is another programming language."),
                ("python_advanced.txt", "Advanced Python topics include decorators.")
            ]
            
            for filename, content in docs:
                (Path(tmpdir) / filename).write_text(content)
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            # Use the internal ranking method
            ranked = rag._rank_chunks("Python programming")
            
            # Should return documents
            assert len(ranked) > 0

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_retrieve_with_no_match(self):
        """Test retrieval with query that doesn't match any documents"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "specific.txt"
            test_file.write_text("This document is about apples and oranges.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            # Query about something completely unrelated
            context = rag.retrieve_context("quantum entanglement in black holes")
            
            # Should return something (even if not highly relevant)
            # The fallback ranking still returns documents
            assert isinstance(context, str)

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_metadata_preservation(self):
        """Test that document metadata is preserved"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "metadata_test.txt"
            test_file.write_text("Content for metadata test.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            for doc in rag.documents:
                assert "source" in doc.metadata
                assert doc.metadata["source"] is not None


class TestRAGManagerEdgeCases:
    """Test edge cases for RAG manager"""

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_empty_file(self):
        """Test handling of empty files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.txt"
            empty_file.write_text("")
            
            # Should not crash
            rag = RAGManager(knowledge_dir=tmpdir)
            assert rag is not None

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_special_characters_in_content(self):
        """Test handling of special characters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            special_file = Path(tmpdir) / "special.txt"
            special_file.write_text("Content with special chars: @#$%^&*(){}[]|\\;':\",./<>?`~")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            assert rag is not None

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_unicode_content(self):
        """Test handling of unicode content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            unicode_file = Path(tmpdir) / "unicode.txt"
            unicode_file.write_text("Unicode content: 你好世界 مرحبا العالم Привет мир")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            assert rag is not None

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_very_long_query(self):
        """Test handling of very long queries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Short content.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            long_query = "test " * 1000
            context = rag.retrieve_context(long_query)
            
            assert isinstance(context, str)

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_nonexistent_directory(self):
        """Test handling of non-existent directory"""
        # Should create the directory
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            rag = RAGManager(knowledge_dir=str(nonexistent))
            
            assert rag.knowledge_dir.exists()

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_concurrent_access(self):
        """Test concurrent access to RAG manager"""
        import threading
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Concurrent access test.")
            
            rag = RAGManager(knowledge_dir=tmpdir)
            
            results = []
            
            def query_rag():
                result = rag.retrieve_context("test")
                results.append(result)
            
            threads = [threading.Thread(target=query_rag) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # All queries should complete
            assert len(results) == 5


class TestRAGIntegration:
    """Test RAG integration with other components"""

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_rag_with_base_agent(self):
        """Test RAG integration with BaseAgent"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "agent_knowledge.txt"
            test_file.write_text("Knowledge for agent testing.")
            
            # Reset global RAG manager
            from core import rag_manager
            rag_manager._rag_manager = None
            
            rag = RAGManager(knowledge_dir=tmpdir)
            rag_manager._rag_manager = rag
            
            # The query_knowledge function should work
            result = query_knowledge("agent knowledge")
            
            assert result is not None

    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG not available due to missing dependencies")
    def test_global_rag_manager(self):
        """Test global RAG manager singleton"""
        rag1 = get_rag_manager()
        rag2 = get_rag_manager()
        
        # After first call, should return the same instance
        assert rag1 is rag2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
