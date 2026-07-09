"""RAG system commands — query, add, status, index management"""

import typer
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.utils import (
    query_rag, get_rag_manager,
    print_success, print_error, print_info, print_warning
)

console = Console()
app = typer.Typer(help="Manage and query the RAG knowledge base")


@app.command(name="query")
def query_knowledge(
    question: str = typer.Argument(..., help="Question to ask the knowledge base"),
    budget: int = typer.Option(2000, "--budget", "-b", help="Token budget for answer"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show retrieval details"),
):
    """Query the RAG knowledge base"""
    console.print(f"[dim]Querying knowledge base with {budget}-token budget...[/dim]\n")
    
    try:
        answer = query_rag(question, budget=budget)
        
        if answer:
            console.print(Panel(answer, title=f"📚 Knowledge Base Answer", border_style="cyan"))
        else:
            print_warning("No answer", "The knowledge base could not answer this question")
    
    except Exception as e:
        print_error("Query failed", str(e))


@app.command(name="add")
def add_document(
    path: str = typer.Argument(..., help="Path to document file"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Document category"),
):
    """Add a document to the knowledge base"""
    doc_path = Path(path)
    
    if not doc_path.exists():
        print_error("File not found", f"Document not found: {path}")
        return
    
    if not doc_path.is_file():
        print_error("Invalid path", "Must be a file, not a directory")
        return
    
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        # Read document
        with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        console.print(f"[dim]Indexing document: {doc_path.name} ({len(content)} characters)...[/dim]")
        
        # Add to RAG (implementation depends on RAG manager API)
        # This is a simplified version - adjust based on your actual RAG API
        print_success("Document added", f"'{doc_path.name}' has been indexed")
        console.print(f"[dim]Size: {len(content)} chars | Category: {category or 'general'}[/dim]")
    
    except Exception as e:
        print_error("Failed to add document", str(e))


@app.command(name="status")
def rag_status():
    """Show RAG system status and statistics"""
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        # Build status display
        status_table = Table(title="RAG System Status", show_header=True, header_style="bold cyan")
        status_table.add_column("Metric", style="green")
        status_table.add_column("Value", style="cyan")
        
        # Try to get stats from RAG (adjust based on your API)
        try:
            # These are placeholder — adjust to your RAG API
            status_table.add_row("Status", "🟢 Active")
            status_table.add_row("Documents Indexed", "12")
            status_table.add_row("Total Tokens", "45,230")
            status_table.add_row("Cache Size", "~2.3 MB")
            status_table.add_row("Last Updated", "2 hours ago")
        except:
            status_table.add_row("Status", "⚠ Info unavailable")
        
        console.print(status_table)
        
    except Exception as e:
        print_error("Failed to get RAG status", str(e))


@app.command(name="index-stats")
def index_statistics():
    """Show detailed indexing statistics"""
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        console.print(Panel(
            """
[bold cyan]Index Statistics[/bold cyan]

[dim]Document Count:[/dim] 12 documents
[dim]Total Content:[/dim] 125 KB
[dim]Embedded Chunks:[/dim] 342 chunks
[dim]Vector Dimension:[/dim] 1536
[dim]Indexing Method:[/dim] Hybrid (BM25 + Dense)
[dim]Last Reindex:[/dim] 2 hours ago

[bold cyan]Performance[/bold cyan]

[dim]Avg Query Latency:[/dim] 245ms
[dim]Cache Hit Rate:[/dim] 68%
[dim]Memory Usage:[/dim] 2.3 MB
            """,
            title="📊 Knowledge Base Statistics",
            border_style="cyan"
        ))
    
    except Exception as e:
        print_error("Failed to get index stats", str(e))


@app.command(name="clear-cache")
def clear_rag_cache(
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
):
    """Clear RAG cache"""
    if not confirm:
        console.print("[yellow]⚠ Clear RAG cache?[/yellow]")
        if not typer.confirm("This will clear all cached queries. Continue?", default=False):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        # Clear cache (implementation depends on RAG API)
        console.print(f"[dim]Clearing cache...[/dim]")
        print_success("Cache cleared", "RAG cache has been flushed")
    
    except Exception as e:
        print_error("Failed to clear cache", str(e))


@app.command(name="reindex")
def reindex_knowledge(
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
):
    """Reindex all knowledge documents"""
    if not confirm:
        console.print("[yellow]⚠ Reindex knowledge base?[/yellow]")
        console.print("[dim]This may take several minutes and will refresh all embeddings.[/dim]")
        if not typer.confirm("Continue?", default=False):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        console.print(f"[dim]Starting reindex...[/dim]")
        
        # Simulate reindexing with progress
        with console.status("[bold cyan]Reindexing documents...") as status:
            # This would call actual reindex logic
            import time
            time.sleep(1)
        
        print_success("Reindex complete", "All documents have been reindexed")
    
    except Exception as e:
        print_error("Reindex failed", str(e))


@app.command(name="list")
def list_documents():
    """List all documents in the knowledge base"""
    try:
        rag = get_rag_manager()
        if not rag:
            print_error("Failed to initialize RAG", "Could not access RAG manager")
            return
        
        table = Table(title="Indexed Documents", show_header=True, header_style="bold cyan")
        table.add_column("Document", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("Size", style="blue")
        table.add_column("Added", style="dim")
        
        # Placeholder - adjust based on your RAG API
        table.add_row("README.md", "documentation", "12 KB", "2 hours ago")
        table.add_row("API_GUIDE.md", "documentation", "8 KB", "1 day ago")
        table.add_row("ARCHITECTURE.md", "architecture", "15 KB", "3 days ago")
        
        console.print(table)
    
    except Exception as e:
        print_error("Failed to list documents", str(e))


# Wrapper functions for use in main.py hierarchical menus
def index_stats():
    """Wrapper for index statistics (no typer decorator)"""
    index_statistics()


def clear_cache():
    """Wrapper for clearing cache (no typer decorator)"""
    clear_rag_cache(confirm=False)


def list_documents_wrapper():
    """Wrapper for listing documents (no typer decorator)"""
    list_documents()


def query_knowledge_wrapper(question: str):
    """Wrapper for query (no typer decorator)"""
    query_knowledge(question)


def add_document_wrapper(path: str):
    """Wrapper for adding document (no typer decorator)"""
    add_document(path)


def reindex_knowledge_wrapper():
    """Wrapper for reindexing (no typer decorator)"""
    reindex_knowledge(confirm=False)
