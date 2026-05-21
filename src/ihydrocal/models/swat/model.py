from ihydrocal.core import BaseModel, register_model


@register_model("swat")
class SWATModel(BaseModel):
    """Model adapter for SWAT."""

    def validate(self):
        """Validate SWAT model directory."""

        if not self.exists():
            return False

        return True

    def read_outputs(self):
        """Read SWAT outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "SWAT output reader is not implemented yet."
        )