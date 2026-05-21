MODEL_REGISTRY = {}


def register_model(name):
    """Register a model adapter class."""

    def decorator(cls):
        MODEL_REGISTRY[name] = cls
        cls.model_name = name
        return cls

    return decorator


def available_models():
    """Return available registered model names."""
    return sorted(MODEL_REGISTRY.keys())


def create_model(name, model_dir, config=None, **kwargs):
    """Create a model instance from the registry."""

    if name not in MODEL_REGISTRY:
        available = ", ".join(available_models()) or "none"
        raise ValueError(
            f"Unknown model '{name}'. Available models: {available}"
        )

    return MODEL_REGISTRY[name](model_dir=model_dir, config=config, **kwargs)