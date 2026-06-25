from pathlib import Path

from ihydrocal.core import BaseModel, register_model
from .io import SWATModflowIO


@register_model("swat_modflow")
class SWATModflowModel(BaseModel):
    """Model adapter for SWAT-MODFLOW."""

    def __init__(self, model_dir, output_dir=None, config=None):
        super().__init__(model_dir=model_dir, config=config)

        self.model_dir = Path(model_dir)
        self.output_dir = Path(output_dir) if output_dir is not None else self.model_dir
        self.io = SWATModflowIO(self.output_dir)

    def validate(self):
        """Validate SWAT-MODFLOW model directory."""

        if not self.model_dir.exists():
            return False

        if not self.output_dir.exists():
            return False

        if not (self.output_dir / "file.cio").exists():
            return False

        self.io = SWATModflowIO(self.output_dir)
        return True

    def get_output_file(self, filename):
        return self.output_dir / filename

    def list_output_files(self, pattern="*"):
        if not self.output_dir.exists():
            return []
        return sorted(self.output_dir.glob(pattern))

    def read_outputs(self):
        """Read SWAT-MODFLOW outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "SWAT-MODFLOW output reader is not implemented yet."
        )
