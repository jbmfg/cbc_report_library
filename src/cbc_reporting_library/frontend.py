import os
import uuid
import time
from datetime import datetime
from prompt import Prompt
from sqlite_connector import sqlite_connection
from cbc_connector import cbc_connection
from cbc_data_import import cbc_data_import


class cbc_reporting_menu(object):

    def __init__(self):
        db_filename = "cbc_reporting.db"
        self.db = sqlite_connection(db_filename)
        self.time_range = ["One Month"]
        self.reports_to_run= set()

    def pass_func(self):
        pass

    def create_report_menu(self, title, report_names):
        title += "\nSpace to select, enter when finished"
        pre_sel = [i for i in report_names if i in self.reports_to_run]
        selection = Prompt.menu(title, report_names, multi=True, pre_sel=pre_sel)
        not_selected_reports = report_names if not selection else [i for i in report_names if i not in selection]
        for nsr in list(not_selected_reports):
            if self.reports_to_run and nsr in self.reports_to_run:
                self.reports_to_run.remove(nsr)
        if selection: [self.reports_to_run.add(i) for i in selection]

    def alert_reports(self):
        options = ["Alert Workflow", "Alert Count Over Time", "Alert Severity Breakdown"]
        self.create_report_menu("Alert Reports", options)
        return self.reports_menu()

    def inventory_reports(self):
        options = ["Endpoints Deployed", "Version Breakdown", "Current Bypass/Quarantine"]
        self.create_report_menu("Alert Reports", options)
        return self.reports_menu()

    def polrule_reports(self):
        options = ["Policy Last Modified Counts", "Policy Summary"]
        self.create_report_menu("Alert Reports", options)
        return self.reports_menu()

    def view_selected_reports_menu(self):
        options = self.reports_to_run
        self.create_report_menu("Reports Selected to Run", options)
        return self.reports_menu()

    def reports_menu(self):
        options = {
            "Add Alert Reports": self.alert_reports,
            "Add Inventory Reports": self.inventory_reports,
            "Add Policy/Rule Reports": self.polrule_reports,
            "View/Remove Selected Reports": self.view_selected_reports_menu,
            "Back to Main Menu": self.main_menu,
        }
        title = "Reports"
        selection = Prompt.dict_menu(title, options)

    def run_reports(self):
        query = "select uuid, backend, api_id, api_secret, org_key, org_id from settings;"
        apis = self.db.execute(query)
        for api_params in apis:
            runner = cbc_data_import(api_params, self.reports_to_run, self.time_range)
            runner.make_calls()

    def run_reports_menu(self):
        options = {
            "Review Configured Reports": self.view_selected_reports_menu,
            "Run Reports": self.run_reports
        }
        selection = Prompt.dict_menu("Run Reports", options)

    def settings_menu(self):
        options = {
            "API Identities": self.identities_menu,
            f"Report Time Range ({', '.join(self.time_range)})": self.time_range_menu,
            "Return to Main Menu": self.main_menu
        }
        selection = Prompt.dict_menu("Settings", options)

    def time_range_menu(self):
        def validate_date(d1, d2=None):
            try: datetime.fromisoformat(d1)
            except Exception as e:
                print(e.title())
                time.sleep(3)
                return self.time_range_menu()
            if d2:
                diff = datetime.fromisoformat(d1) - datetime.fromisoformat(d2)
                if diff.total_seconds() <= 0:
                    print("ERROR: End date must be after start date")
                    time.sleep(3)
                    return self.time_range_menu()
        options = ["Three Hours", "One Day", "One Week", "Two Weeks"]
        options += ["One Month", "Three Months", "All", "Custom"]
        title = f"Report Time Range\nCurrent: {self.time_range}"
        selection = Prompt.menu(title, options)
        if selection == "Custom":
            start_date = input("Enter UTC/GMT start date (YYYY-MM-DD HH:MM:SS): ")
            validate_date(start_date)
            end_date = input("Enter UTC/GMT end date (YYYY-MM-DD HH:MM:SS): ")
            validate_date(end_date)
            validate_date(end_date, d2=start_date)
            start_date = start_date.replace(" ", "T") + ".000Z"
            end_date = end_date.replace(" ", "T") + ".000Z"
            self.time_range = [start_date, end_date]
        else:
            self.time_range = [selection]
        print(f"Set time range to {', '.join(self.time_range)}")
        time.sleep(2)
        self.settings_menu()

    def check_if_exists(self, api_id):
        exists = False
        if self.db._check_if_table_exists("settings"):
            existing = self.db.execute("select api_id, uuid from settings;")
            if existing and api_id in [i[0] for i in existing]:
                print(f"API Key '{api_id}' already entered")
                exists = True
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
        return self.identities_menu()

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
                     lambda: self.single_identity_menu(identity) for x, identity in enumerate(settings)
                    }
                )
        options.update({"Add New": self.add_identity})
        options.update({"Return to settings": self.settings_menu})
        selection = Prompt.dict_menu("Identities", options)

    def single_identity_menu(self, identity):
        options = ["Delete", "Edit API Secret"]
        selection = Prompt.menu(f"Options for {identity['api_id']}", options)
        if selection == "Delete":
            confirm = input(f"Are you sure you want to delete {identity['id']} from program? (Y/N)")
            if confirm.lower() == "y":
                query = f"DELETE from settings where api_id = '{identity['api_id']}';"
                self.db.execute(query)
                print(f"Deleted {identity['api_id']} from program")
                time.sleep(1)
        elif selection == "Edit API Secret":
            self.edit_identity(identity)
        return self.identities_menu()

    def quit_function(self):
        print("Thank you for using CCRP!")

    def main_menu(self):
        options = {
            "Report Selection": self.reports_menu,
            "Run Reports": self.run_reports_menu,
            "Settings": self.settings_menu,
            "Quit": self.quit_function,
        }
        title = "CBC Custom Reporting Platform (CCRP)"
        selection = Prompt.dict_menu(title, options)

if __name__ == "__main__":
    menu = cbc_reporting_menu()
    menu.main_menu()
