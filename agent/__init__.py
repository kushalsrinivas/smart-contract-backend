try:
    from . import agent
except ImportError:
    # Fallback for when running as script or when relative import fails
    import agent