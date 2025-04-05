"""
Base model module for AI/ML implementations.
"""
from typing import Any, Dict, Optional
import torch
import torch.nn as nn
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class BaseModel(nn.Module):
    """Base class for all AI/ML models in the project."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the model with optional configuration."""
        super().__init__()
        self.config = config or {}
        self.device = torch.device(os.getenv("DEVICE", "cpu"))
        
    def save(self, path: str) -> None:
        """Save model to disk."""
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), save_path)
        
    def load(self, path: str) -> None:
        """Load model from disk."""
        self.load_state_dict(torch.load(path, map_location=self.device))
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the model."""
        raise NotImplementedError("Subclasses must implement forward()") 