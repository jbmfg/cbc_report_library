# https://medium.com/@homestanrunner/simplifying-the-simple-terminal-menu-1351ed27d7c4
from simple_term_menu import TerminalMenu


class Prompt:
    def menu(title, options):
        # Global options
        cursor = "> "
        cursor_style = ("fg_blue", "bold")
        style = ("bg_red", "fg_yellow")
        terminal_menu = TerminalMenu(
            menu_entries=options,
            title=title,
            menu_cursor=cursor,
            menu_cursor_style=cursor_style,
            menu_highlight_style=style,
            cycle_cursor=True,
            clear_screen=True,)
        menu_entry_index = terminal_menu.show()
        selection = options[menu_entry_index]
        return selection

    def dict_menu(title, dict_options):
        selection = Prompt.menu(title, list(dict_options.keys()))
        selected_function = dict_options.get(selection)
        selected_function()
