from abc import ABC, abstractmethod
from pathlib import Path


class BaseModel(ABC):
    """Base class for all iHydroCal model adapters."""

    model_name: str = "base"

    def __init__(self, model_dir, config=None):
        self.model_dir = Path(model_dir)
        self.config = config or {}

    def exists(self):
        """Check whether the model directory exists."""
        return self.model_dir.exists()

    @abstractmethod
    def validate(self):
        """Validate required model files."""
        pass

    @abstractmethod
    def read_outputs(self):
        """Read model outputs."""
        pass

    def run(self):
        """Run model executable. Optional for now."""
        raise NotImplementedError(
            f"Run method is not implemented for {self.model_name}."
        )