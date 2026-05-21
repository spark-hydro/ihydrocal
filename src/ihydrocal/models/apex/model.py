from ihydrocal.core import BaseModel, register_model


@register_model("apex")
class APEXModel(BaseModel):
    """Model adapter for APEX."""

    def validate(self):
        """Validate APEX model directory."""

        if not self.exists():
            return False

        return True

    def read_outputs(self):
        """Read APEX outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "APEX output reader is not implemented yet."
        )