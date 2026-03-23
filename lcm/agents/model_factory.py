# -*- coding: utf-8 -*-
"""Model factory extension for LCM.

This module extends Copaw's model_factory with create_model_by_slot function.
The install script will merge this into the original model_factory.py.
"""

# This function will be appended to copaw/agents/model_factory.py


def create_model_by_slot(
    provider_id: str,
    model_id: str,
) -> tuple:
    """Create model and formatter by explicit provider/model slot.

    This is used for secondary/expansion models that should not conflict
    with the main agent model (e.g., LCM compression when main model is busy).

    Args:
        provider_id: Provider ID (e.g., "aliyun-codingplan", "dashscope")
        model_id: Model ID (e.g., "glm-4.7", "qwen3.5-plus")

    Returns:
        Tuple of (model_instance, formatter_instance)

    Raises:
        ValueError: If provider or model not found
    """
    from copaw.providers import ProviderManager
    from copaw.agents.model_factory import _create_formatter_instance
    from copaw.token_usage import TokenRecordingModelWrapper
    from copaw.local_models import create_local_chat_model
    from copaw.providers.retry_chat_model import RetryChatModel

    manager = ProviderManager.get_instance()
    provider = manager.get_provider(provider_id)
    if provider is None:
        raise ValueError(
            f"Provider '{provider_id}' not found. "
            f"Available: {list(manager.builtin_providers.keys())}"
        )

    if provider.is_local:
        model = create_local_chat_model(
            model_id=model_id,
            stream=True,
            generate_kwargs={"max_tokens": None},
        )
    else:
        model = provider.get_chat_model_instance(model_id)

    formatter = _create_formatter_instance(model.__class__)
    wrapped_model = TokenRecordingModelWrapper(provider_id, model)
    wrapped_model = RetryChatModel(wrapped_model)

    return wrapped_model, formatter


# List of functions to add to the original model_factory.py
__all_additions__ = ["create_model_by_slot"]