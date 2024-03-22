import constants
import xlsxwriter
from datetime import datetime, timedelta

class cbc_reports(object):
    def __init__(self, db, org_key, report_list):
        self.db = db
        self.org_key = org_key
        self.report_list = report_list
        self.wb = xlsxwriter.Workbook(f"CBC_Reports_{org_key}.xlsx")

    def run_reports(self):
        self.toc()
        report_lookup = constants.REPORT_LOOKUP
        for report in self.report_list:
            f = getattr(self, report_lookup[report][1])
            f(report)
        self.charting_settings()

    def _method_template(self):
        sheet_name = ""
        sheet = self.wb.add_worksheet(sheet_name)
        query = f"""
        """
        data = self.db.execute(query)

    def toc(self):
        sheet_name = "Charts Table of Contents"
        sheet = self.wb.add_worksheet(sheet_name)
        #query = f"select report from selected_reports where org_key = '{self.org_key}';"
        #reports = [["Report Name"]] + [[i[0]] for i in self.db.execute(query)]
        reports = [["Report Name"]] + [[i] for i in self.report_list]
        write_rows(self.wb, sheet, reports, col1url=True)

    def charting_settings(self):
        sheet_name = "Charting Settings"
        sheet = self.wb.add_worksheet(sheet_name)
        query = f"select * from settings where org_key = '{self.org_key}';"
        settings = self.db.execute_dict(query)
        settings = [list(settings[0].keys())] + [list(settings[0].values())]
        write_rows(self.wb, sheet, settings)

    def fp_vs_tp(self, sheet_name):
        sheet = self.wb.add_worksheet(sheet_name)
        query = f"""
        select determination_value, count(*) as count
        from alert_data
        where org_key = '{self.org_key}'
        group by determination_value
        """
        data = dict(self.db.execute(query))
        fields = ("TRUE_POSITIVE", "FALSE_POSITIVE", "NONE")
        for f in fields:
            data[f] = data.get(f, 0)
        header = ("Determination", "Count")
        data = [header] + [[i, data[i]] for i in data]
        write_rows(self.wb, sheet, data)
        titles = ("False vs True Postitives", "Determination", "Count")
        column_chart(self.wb, sheet, sheet_name, titles, data, (0, 4))

    def closed_alert_metrics(self, sheet_name):
        sheet = self.wb.add_worksheet(sheet_name)
        query = f"""
        select workflow_closure_reason,
        backend_timestamp,
        workflow_change_timestamp
        from alert_data where
        workflow_status = 'CLOSED'
        and org_key = '{self.org_key}';
        """
        data = self.db.execute(query)
        dt_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        times_to_close = []
        reason_counts = {}
        for reason, alert_open, alert_close in data:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            open_dt = datetime.strptime(alert_open, dt_format)
            close_dt = datetime.strptime(alert_close, dt_format)
            minutes_to_close = int((close_dt - open_dt).total_seconds()/60)
            times_to_close.append(minutes_to_close)
        avg_time_to_close = round(sum(times_to_close) / len(times_to_close))
        rows = [["Closure Reason", "Count"]] + [[reason, reason_counts[reason]] for reason in reason_counts]
        rows.append([])
        rows.append(["Average time to close: ", f"{avg_time_to_close} minutes"])
        write_rows(self.wb, sheet, rows)
        pie_chart(self.wb, sheet, sheet_name, rows, (0, 4))

def write_rows(wb, sheet, data, linkBool=False, setwid=True, col1url=False, bolder=False):
    bold = wb.add_format({"bold": True})
    # first get the length of the longest sting to set column widths
    numCols = len(data[0])
    widest = [10 for _ in range(numCols)]
    if setwid:
        try:
            for i in data:
                for x in range(len(data[0])):
                    if type(i[x]) == int:
                        pass
                    elif i[x] is None:
                        pass
                    elif not isinstance(i[x], float) and widest[x] < len(i[x].encode("ascii", "ignore")):
                        if len(str(i[x])) > 50:
                            widest[x] = 50
                        else:
                            widest[x] = len(str(i[x])) #+ 4
        except IndexError:
            pass
            # print ("--INFO-- Index Error when setting column widths")
        except TypeError:
            print ("type error")
        #except AttributeError:
            # Added check for floats above so this probably isnt needed any more
            # print ("\n--INFO-- Can't encode a float\n")

    for x, i in enumerate(widest):
        sheet.set_column(x, x, i)

    # Then write the data
    for r in data:
        for i in r:
            if type(i) == str:
                i = i.encode("ascii", "ignore")
    counter = 0
    for x, r in enumerate(data):
        counter += 1
        cell = "A" +str(counter)
        if bolder and (data[x-1] == "" or x==0):
            sheet.write_row(cell, r, bold)
        else:
            sheet.write_row(cell, r)
        if col1url:
            if x == 0:
                pass
            else:
                sheet_name = f"{r[0]}"[:31]
                sheet.write_url(cell, f"internal:'{sheet_name}'!A1", string=r[0])
        if linkBool:
            sheet.write_url(0, 6, "internal:Master!A1", string="Mastersheet")
    return True

def column_chart(wb, sheet, sheet_name, titles, data, chart_loc):
    chart_title, x_title, y_title = titles
    chart = wb.add_chart({"type": "column"})
    for col in range(len(data[0])):
        if col == 0: continue
        chart_data = {
            "name": [sheet_name, 0, col],
            "categories": [sheet_name, 1, 0, len(data) - 1, 0],
            "values": [sheet_name, 1, 1, len(data) -1, 1],
        }
        chart.add_series(chart_data)
    chart.set_title({"name": chart_title})
    chart.set_x_axis({"name": x_title})
    chart.set_y_axis({"name": y_title})
    sheet.insert_chart(*chart_loc, chart)

def pie_chart(wb, sheet, sheet_name, data, chart_loc):
    chart = wb.add_chart({"type": "pie"})
    end_of_data = data.index([]) - 1
    chart_data = {
        "name": data[0][0],
        "categories": [sheet_name, 1, 0, end_of_data, 0],
        "values": [sheet_name, 1, 1, end_of_data, 1]
    }
    chart.add_series(chart_data)
    sheet.insert_chart(*chart_loc, chart)

if __name__ == "__main__":
    from sqlite_connector import sqlite_connection
    db = sqlite_connection('cbc_reporting.db')
    reports = cbc_reports(db, '7PESY63N', ["False vs True Positives", "Closed Alert Metrics"])
    reports.run_reports()
    reports.wb.close()


