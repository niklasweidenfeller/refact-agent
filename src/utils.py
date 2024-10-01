NEWLINE = "\n"

def prettify_list(l: list[str]) -> str:
    list_items_w_tab_and_bullet = ["\t- " + step for step in l]
    return NEWLINE.join(list_items_w_tab_and_bullet)
