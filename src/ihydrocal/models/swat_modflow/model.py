from ihydrocal.core import BaseModel, register_model


@register_model("swat_modflow")
class SWATModflowModel(BaseModel):
    """Model adapter for SWAT-MODFLOW."""

    def validate(self):
        """Validate SWAT-MODFLOW model directory."""

        if not self.exists():
            return False

        return True

    def read_outputs(self):
        """Read SWAT-MODFLOW outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "SWAT-MODFLOW output reader is not implemented yet."
        )