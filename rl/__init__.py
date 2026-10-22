"""RL exports with optional Gymnasium dependencies loaded on demand."""

_EXPORTS = {
    "StateBuilder": (".state_builder", "StateBuilder"),
    "RewardCalculator": (".reward_calculator", "RewardCalculator"),
    "ContextAwareNavEnv": (".gym_env", "ContextAwareNavEnv"),
    "RLPolicyAgent": (".train_eval", "RLPolicyAgent"),
    "train_model": (".train_eval", "train_model"),
    "evaluate_saved_model": (".train_eval", "evaluate_saved_model"),
}


def __getattr__(name: str):
    if name in _EXPORTS:
        module_name, attribute_name = _EXPORTS[name]
        module = __import__(f"{__name__}{module_name}", fromlist=[attribute_name])
        return getattr(module, attribute_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(_EXPORTS)