import os
import time
from datetime import datetime
from prompt import Prompt
from sqlite_connector import sqlite_connection
from cbc_connector import cbc_connection
from cbc_data_import import cbc_data_import
from report_library import cbc_reports


class cbc_reporting_menu(object):

    def __init__(self):
        db_filename = "cbc_reporting.db"
        self.db = sqlite_connection(db_filename)
        self.org_key = None
        if self.db._check_if_table_exists("settings"):
            self.main_menu()
        else:
            self.settings_menu()

    def pass_func(self):
        pass

    def create_report_menu(self, title, report_names):
        title += "\nSpace to select, enter when finished"
        if not self.db._check_if_table_exists("selected_reports"):
            pre_sel = []
        else:
            query = f"select report from selected_reports where org_key = '{self.org_key}';"
            pre_sel = [i[0] for i in self.db.execute(query) if i[0] in report_names]
            delete_sql = "'" + "', '".join(pre_sel) + "'"
            query = f"delete from selected_reports where org_key = '{self.org_key}' and report in ({delete_sql});"
            self.db.execute(query)
        selection = Prompt.menu(title, report_names, multi=True, pre_sel=pre_sel)
        if selection:
            for report in selection:
                data = [{"org_key": self.org_key, "report": report}]
                self.db.insert("selected_reports", data)

    def alert_reports(self):
        options = ["False vs True Positives", "Alert Workflow Metrics", "Closed Alert Metrics", "Alert Severity Breakdown"]
        options += ["Blocks Reputation"]
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
        query = f"select report from selected_reports where org_key = '{self.org_key}'"
        data = self.db.execute(query)
        options = [i[0] for i in data] if data else []
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
        query = "select distinct org_key from settings;"
        org_keys = [i[0] for i in self.db.execute(query)]
        for org_key in org_keys:
            query = f"""
            select backend, api_id, api_secret, org_key, org_id, time_range
            from settings
            where org_key = '{org_key}';
            """
            api = list(self.db.execute(query)[0])
            time_range = api.pop(-1)
            query = f"select report from selected_reports where org_key = '{org_key}';"
            data = self.db.execute(query)
            if data:
                reports_to_run = [i[0] for i in data]
                data_pull = cbc_data_import(api, reports_to_run, [time_range])
                data_pull.make_calls()
                reports = cbc_reports(self.db, org_key, reports_to_run)
                reports.run_reports()
                reports.wb.close()

    def run_reports_menu(self):
        options = {
            "Review Configured Reports": self.select_api_key_menu,
            "Run Reports": self.run_reports
        }
        selection = Prompt.dict_menu("Run Reports", options)

    def settings_menu(self):
        def return_to_main():
            if self.db._check_if_table_exists("settings"):
                self.main_menu()
            else:
                print("Please enter an API key pair first")
                time.sleep(1)
                self.settings_menu()
        options = {}
        if self.db._check_if_table_exists("settings"):
            query = "select backend, api_id, api_secret, org_key, org_id, time_range from settings;"
            settings = self.db.execute_dict(query)
            if settings:
                options.update(
                    {f"{x+1}. {identity['api_id']}":
                     lambda identity=identity: self.single_identity_menu(identity) for x, identity in enumerate(settings)
                    }
                )
        options.update({
            "Add New API Key": self.add_identity,
            "Return to Main Menu": return_to_main,
            "Exit Program": self.quit_function
        })
        selection = Prompt.dict_menu("Settings", options)

    def time_range_menu(self, api_id, cur_time_range):
        def validate_date(d1, d2=None):
            try: datetime.fromisoformat(d1)
            except Exception as e:
                print(e.title())
                time.sleep(3)
                return self.time_range_menu(api_id)
            if d2:
                diff = datetime.fromisoformat(d1) - datetime.fromisoformat(d2)
                if diff.total_seconds() <= 0:
                    print("ERROR: End date must be after start date")
                    time.sleep(3)
                    return self.time_range_menu(api_id)
        options = ["Three Hours", "One Day", "One Week", "Two Weeks"]
        options += ["One Month", "Three Months", "All", "Custom"]
        title = f"Report Time Range\nCurrent: {cur_time_range}"
        selection = Prompt.menu(title, options)
        if selection == "Custom":
            start_date = input("Enter UTC/GMT start date (YYYY-MM-DD HH:MM:SS): ")
            validate_date(start_date)
            end_date = input("Enter UTC/GMT end date (YYYY-MM-DD HH:MM:SS): ")
            validate_date(end_date)
            validate_date(end_date, d2=start_date)
            start_date = start_date.replace(" ", "T") + ".000Z"
            end_date = end_date.replace(" ", "T") + ".000Z"
            time_range = f"{start_date}--{end_date}"
        else:
            time_range = selection
        self.db.update("settings", [{"api_id": api_id, "time_range": time_range}])
        input(f"Set time range to {time_range}. Enter to continue")
        return time_range

    def check_if_exists(self, api_id):
        exists = False
        if self.db._check_if_table_exists("settings"):
            existing = self.db.execute("select api_id from settings;")
            if existing and api_id in [i[0] for i in existing]:
                print(f"API Key '{api_id}' already entered")
                exists = True
        return exists

    def add_identity(self):
        api_id = input("Enter API Key: ")
        api_secret = input("Enter API Secret: ")
        if not self.check_if_exists(api_id):
            # Get backend, org_key, and org_id
            api_details = cbc_connection(None, api_id, api_secret, None, None).get_api_details()
            if api_details:
                prod, org_key, org_id, name = api_details
                data = [{
                    "backend": prod,
                    "api_id": api_id,
                    "api_secret": api_secret,
                    "org_key": org_key,
                    "org_id": org_id,
                    "time_range": "One Month"
                }]
                self.db.insert("settings", data)
            else:
                print(f"API Key '{api_id}' is not valid, please try again")
                time.sleep(2)
                self.settings_menu()
        return self.settings_menu()

    def edit_identity_secret(self, identity):
        tr = identity.pop("time_range")
        old_sec = identity["api_secret"]
        identity["api_secret"] = input("Enter new API Secret: ")
        api_details = cbc_connection(*list(identity.values())).get_api_details()
        if not api_details:
            input("API Secret was not accepted, please try again. Enter to continue")
            identity["api_secret"] = old_sec
        else:
            self.db.update("settings", [{"api_id": identity["api_id"], "api_secret": identity["api_secret"]}])
        identity["time_range"] = tr
        return identity

    def single_identity_menu(self, identity):
        options = ["Delete", "Edit API Secret",]
        options += [f"Select Report Time Window ({identity['time_range']})", "Return to Settings Menu"]
        selection = Prompt.menu(f"Options for {identity['api_id']}", options)
        if selection == "Delete":
            confirm = input(f"Are you sure you want to delete {identity['api_id']} from program? (Y/N)")
            if confirm.lower() == "y":
                query = f"DELETE from settings where api_id = '{identity['api_id']}';"
                self.db.execute(query)
                input(f"Deleted {identity['api_id']} from program. Press enter to continue")
                return self.settings_menu()
        elif selection == "Edit API Secret":
            identity = self.edit_identity_secret(identity)
            return self.single_identity_menu(identity)
        elif selection == f"Select Report Time Window ({identity['time_range']})":
            identity["time_range"] = self.time_range_menu(identity["api_id"], identity["time_range"])
            return self.single_identity_menu(identity)
        elif selection == "Return to Settings Menu":
            return self.settings_menu()

    def quit_function(self):
        print("Thank you for using CCRP!")

    def select_api_key_menu(self):
        query = "select api_id, org_key from settings;"
        api_keys = self.db.execute(query)
        if len(api_keys) > 1:
            options = [f"{x + 1}. API ID: {i[0]} Org Key: {i[1]}" for x, i in enumerate(api_keys)]
            selection = Prompt.menu("Select reports for which API key?", options)
            selection = int(selection.split(".")[0]) - 1
            selection = api_keys[selection][1]
        else:
            selection = api_keys[0][1]
        self.org_key = selection
        return self.reports_menu()

    def main_menu(self):
        self.org_key = None
        options = {
            "Report Selection": self.select_api_key_menu,
            "Run Reports": self.run_reports_menu,
            "Settings": self.settings_menu,
            "Quit": self.quit_function,
        }
        title = "CBC Custom Reporting Platform (CCRP)"
        selection = Prompt.dict_menu(title, options)

if __name__ == "__main__":
    menu = cbc_reporting_menu()
