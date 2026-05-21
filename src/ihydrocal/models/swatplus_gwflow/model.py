from pathlib import Path

from ihydrocal.core import BaseModel, register_model
from .io import SWATPlusGwflowIO


@register_model("swatplus_gwflow")
class SWATPlusGwflowModel(BaseModel):
    """Model adapter for SWAT+ and SWAT+gwflow."""

    def __init__(self, model_dir, output_dir=None, config=None):
        super().__init__(model_dir=model_dir, config=config)

        self.model_dir = Path(model_dir)

        if output_dir is None:
            self.output_dir = self.model_dir
        else:
            self.output_dir = Path(output_dir)

        self.io = SWATPlusGwflowIO(self.output_dir)

    def validate(self):
        """Validate model/output directory."""

        if not self.model_dir.exists():
            return False

        if not self.output_dir.exists():
            return False

        self.io = SWATPlusGwflowIO(self.output_dir)
        return True

    def get_output_file(self, filename):
        return self.output_dir / filename

    def list_output_files(self, pattern="*.txt"):
        if not self.output_dir.exists():
            return []
        return sorted(self.output_dir.glob(pattern))

    def read_outputs(self):
        raise NotImplementedError(
            "SWAT+gwflow output reader is not implemented yet."
        )