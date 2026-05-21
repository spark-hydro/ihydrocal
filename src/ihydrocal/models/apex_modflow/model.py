from ihydrocal.core import BaseModel, register_model


@register_model("apex_modflow")
class APEXModflowModel(BaseModel):
    """Model adapter for APEX-MODFLOW."""

    def validate(self):
        """Validate APEX-MODFLOW model directory."""

        if not self.exists():
            return False

        return True

    def read_outputs(self):
        """Read APEX-MODFLOW outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "APEX-MODFLOW output reader is not implemented yet."
        )