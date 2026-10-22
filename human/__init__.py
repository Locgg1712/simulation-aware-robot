"""Human-model exports with lazy loading to avoid circular imports."""

_MODULE_EXPORTS = {
    "HumanAgent": (".human_agent", "HumanAgent"),
    "HumanActivity": (".human_agent", "HumanActivity"),
    "SocialContext": (".human_agent", "SocialContext"),
    "HumanGroup": (".groups", "HumanGroup"),
    "GroupType": (".groups", "GroupType"),
    "compute_personal_space_cost": (".social_space", "compute_personal_space_cost"),
    "evaluate_social_violations": (".social_space", "evaluate_social_violations"),
    "get_gaussian_ellipse_axes": (".social_space", "get_gaussian_ellipse_axes"),
    "update_humans_motion": (".motion_model", "update_humans_motion"),
}


def __getattr__(name: str):
    if name in _MODULE_EXPORTS:
        module_name, attribute_name = _MODULE_EXPORTS[name]
        module = __import__(f"{__name__}{module_name}", fromlist=[attribute_name])
        return getattr(module, attribute_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(_MODULE_EXPORTS)