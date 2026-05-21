from ihydrocal.core import BaseModel, register_model


@register_model("daycent")
class DayCentModel(BaseModel):
    """Model adapter for DayCent."""

    def validate(self):
        """Validate DayCent model directory."""

        if not self.exists():
            return False

        return True

    def read_outputs(self):
        """Read DayCent outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "DayCent output reader is not implemented yet."
        )