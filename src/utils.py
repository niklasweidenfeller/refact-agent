""" General utility functions that don't fit anywhere else. """

NEWLINE = "\n"

def prettify_list(l: list[str]) -> str:
    """Prettify a list of strings with bullet points and newlines."""
    list_items_w_tab_and_bullet = ["\t- " + step for step in l]
    return NEWLINE.join(list_items_w_tab_and_bullet)
