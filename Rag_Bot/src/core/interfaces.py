from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

class ILoader(ABC):
    """Block 1: Loads a document into a processing format."""
    @abstractmethod
    def load(self, file_path: Path) -> Any:
        pass

class IAnalyzer(ABC):
    """Block 2: Analyzes document structure to identify regions (tables, text, etc)."""
    @abstractmethod
    def analyze(self, document: Any, **kwargs) -> List[Dict[str, Any]]:
        pass

class IExtractor(ABC):
    """Block 3: Extracts raw content from identified regions."""
    @abstractmethod
    def extract(self, document: Any, regions: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        pass

class IProcessor(ABC):
    """Block 4: Processes raw content into structured semantic data."""
    @abstractmethod
    def process(self, raw_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

class IIndexer(ABC):
    """Block 5: Chunks and stores structured data in a vector database."""
    @abstractmethod
    def index(self, structured_data: Dict[str, Any]) -> List[str]:
        pass

class IRAGEngine(ABC):
    """Block 6: Handles retrieval and generation based on user queries."""
    @abstractmethod
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        pass
