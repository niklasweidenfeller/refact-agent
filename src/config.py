""" Configuration file for the project. """


SETTINGS = {
    "consider_cyclomatic_complexity": False,
    "make_incremental_changes": False,
    "use_refactoring_tricks": False,
    "get_buddy_feedback": False,
    "use_previous_history": False,
    "make_plan": False,
    "dynamic_plan": False,
    "modify_specific_method": False,
    "clear_error_after_n": False,
    "clip_context_window": False,
}

def get_settings():
    """ Get the settings for the project. """
    return SETTINGS.copy()
