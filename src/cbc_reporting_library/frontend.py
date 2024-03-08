import os
from prompt import Prompt
from sqlite_connector import sqlite_connection


class cbc_reporting_menu(object):
    def __init__(self):
        db_filename = "cbc_reporting.db"
        self.db = sqlite_connection(db_filename)
        self.main_menu()

    def pass_func(self):
        pass

    def alert_reports(self):
        options = {
            "1": self.pass_func(),
            "2": self.pass_func(),
            "3": self.pass_func(),
        }

    def inventory_reports(self):
        options = {
        }

    def polrule_reports(self):
        options = {
        }

    def select_reports(self):
        options = {
            "Alert Reports": self.alert_reports,
            "Inventory Reports": self.inventory_reports,
            "Policy/Rule Reports": self.polrule_reports,
            "Back to Main Menu": self.main_menu,
        }
        title = "Reports"
        selection = Prompt.dict_menu(title, options)

    def set_settings(self, field):
        value = input(f"Enter {' '.join(field.split('_'))}: ")
        self.db.insert("settings", [{field: value}])
        self.settings_menu()

    def settings_menu(self):
        options = {
            "API Identities": self.identities_menu,
            "Report Time Range": self.pass_func,
            "Return to Main Menu": self.main_menu
        }
        selection = Prompt.dict_menu("Settings", options)


    def identities_menu(self):
        query = "select * from settings;"
        sk = ["api_key", "api_secret", "org_key", "org_id"]
        settings = self.db.execute_dict(query)
        #for identity in settings:
        #    for key in sk:
        #        identity[key] = identity.get(key, "Unset")
        options = {"Add New": self.pass_func}
        if settings:
            options.update({identity['api_key']: self.pass_func for identity in settings})
        selection = Prompt.dict_menu("Identities", options)
        
    def new_settings(self):
        options = {
            f"API Key - {settings['api_key']}": lambda: self.set_settings("api_key"),
            f"API Secret - {settings['api_secret']}": lambda: self.set_settings("api_secret"),
            f"Org Key - {settings['org_key']}": self.pass_func(),
            f"Org ID - {settings['org_id']}": self.pass_func(),
            "Back to Main Menu": self.main_menu
        }
        selection = Prompt.dict_menu("Settings", options)

    def quit_function(self):
        print("Thank you for using CCRP!")

    def main_menu(self):
        options = {
            "Report Selection": self.select_reports,
            "Settings": self.settings_menu,
            "Quit": self.quit_function,
        }
        title = "CBC Custom Reporting Platform (CCRP)"
        selection = Prompt.dict_menu(title, options)


if __name__ == "__main__":
    menu = cbc_reporting_menu()
