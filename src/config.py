
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
    return SETTINGS.copy()

IMPLEMENTED_SETTINGS = [
    "consider_cyclomatic_complexity",
    "make_incremental_changes",
    "use_refactoring_tricks",
    "get_buddy_feedback",
    "use_previous_history",
    "make_plan",
    "modify_specific_method",
    "clip_context_window",
    "clear_error_after_n",
    "dynamic_plan",
]

def check_all_settings_implemented(settings = get_settings(), implemented_settings = IMPLEMENTED_SETTINGS):
    missing_settings = []
    for setting in settings:
        if setting not in implemented_settings:
            missing_settings.append(setting)
    
    if len(missing_settings) > 0:
        raise NotImplementedError(f"Setting {', '.join(missing_settings)} is not implemented.")
