from .plot_results import generate_all_plots

__all__ = ["PygameRenderer", "generate_all_plots"]


def __getattr__(name: str):
    if name == "PygameRenderer":
        from .pygame_renderer import PygameRenderer

        return PygameRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")