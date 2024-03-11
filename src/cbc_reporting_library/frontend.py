import os
import uuid
import time
from prompt import Prompt
from sqlite_connector import sqlite_connection
from cbc_connector import cbc_connection


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

    def check_if_exists(self, api_id):
        if self.db._check_if_table_exists("settings"):
            existing = self.db.execute("select api_id, uuid from settings;")
            if existing and api_id in [i[0] for i in existing]:
                print(f"API Key '{api_id}' already entered")
                exists = True
        else:
            exists = False
        return exists

    def add_identity(self):
        api_id = input("Enter API Key: ")
        api_secret = input("Enter API Secret: ")
        if not self.check_if_exists(api_id):
            # Get backend, org_key, and org_id
            api_details = cbc_connection(None, None, api_id, api_secret, None, None).get_api_details()
            if api_details:
                customer_uuid = str(uuid.uuid4())
                prod, org_key, org_id, name = api_details
                data = [{
                    "uuid": customer_uuid,
                    "backend": prod,
                    "api_id": api_id,
                    "api_secret": api_secret,
                    "org_key": org_key,
                    "org_id": org_id
                }]
                self.db.insert("settings", data)
            else:
                print(f"API Key '{api_id}' is not valid, please try again")
                time.sleep(2)
                self.identities_menu()

    def edit_identity(self, identity):
        api_secret = input("Enter new API Secret: ")
        identity["api_secret"] = api_secret
        api_details = cbc_connection(*list(identity.values())).get_api_details()
        if not api_details:
            print("API Secret was not accepted, please try again.")
            time.sleep(2)
            self.identities_menu()
        else:
            self.db.update("settings", [{"uuid": identity['uuid'], "api_secret": api_secret}])
            self.identities_menu()


    def identities_menu(self):
        options = {}
        if self.db._check_if_table_exists("settings"):
            query = "select uuid, backend, api_id, api_secret, org_key, org_id from settings;"
            settings = self.db.execute_dict(query)
            if settings:
                options.update(
                    {f"{x+1}. {identity['api_id']}":
                     lambda: self.edit_identity(identity) for x, identity in enumerate(settings)
                    }
                )
        options.update({"Add New": self.add_identity})
        options.update({"Return to settings": self.settings_menu})
        selection = Prompt.dict_menu("Identities", options)

    def new_settings(self):
        options = {
            f"API Key - {settings['api_id']}": lambda: self.set_settings("api_id"),
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
