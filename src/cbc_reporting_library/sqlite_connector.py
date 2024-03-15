import sqlite3
import re
import datetime

class sqlite_connection(object):

    def __init__(self, filename):
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.cursor = self.conn.cursor()

    def _check_if_table_exists(self, table):
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';"
        exists = True if self.execute(query) else False
        return exists

    def _get_all_keys(self, data):
        keys = [key for row in data for key in row.keys()]
        keys = set(keys)
        return keys

    def _normalize_data_rows(self, data):
        keys = self._get_all_keys(data)
        for x, row in enumerate(data):
            for key in keys:
                # make sure every key is in each row
                data[x][key] = data[x].get(key, None)
                # replace ' that break insert/update queries
                if isinstance(data[x][key], str):
                    pass
                    #data[x][key] = data[x][key].replace("'", "''")
        return data

    def _get_column_type(self, data, col):
        values = [row[col] for row in data if row[col] == 0 or row[col]]
        if all([isinstance(val, float) for val in values]):
            if all([str(val).endswith(".0") for val in values]):
                column_type = "INTEGER"
            else:
                column_type = "FLOAT"
        elif all([isinstance(val, datetime.date) for val in values]):
            column_type = "TEXT"
        elif all([str(val).isnumeric() for val in values]):
            # Values look like integers
            column_type = "INTEGER"
        elif all([isinstance(val, bool) for val in values]):
            # values are booleans, store as 0 or 1
            column_type = "INTEGER"
        elif all(type(i) in (int, float) for i in values):
            # values are integers AND floats
            column_type = "FLOAT"
        elif any(["." in val for val in values]):
            if any([re.search(r'(?<!\.)\.\.(?!\.)', val) for val in values]):
                # Look for a period with a period before or after (aka >=two periods)
                column_type = "TEXT"
            elif all([val.replace(".", "").isnumeric() for val in values]):
                # remove the single period and check if it looks like a number
                column_type = "FLOAT"
            else:
                column_type = "TEXT"
        else:
            column_type = "TEXT"
        return column_type

    def _create_table(self, table, data):
        cols = self._get_all_keys(data)
        if not cols: return
        query = f"CREATE table IF NOT EXISTS {table} (\n"
        for col in cols:
            col_type = self._get_column_type(data, col)
            query += f"'{col}' {col_type} CHECK(TYPEOF('{col}') in ('{col_type}', Null)),\n"
        query = query[:-2] + ");"
        self.execute(query)

    def _add_columns(self, table, data, new_cols):
        for col in new_cols:
            col_type = self._get_column_type(data, col)
            query = f"ALTER TABLE {table} ADD COLUMN '{col}' {col_type} CHECK(TYPEOF('{col}') in ('{col_type}', Null))"
            self.execute(query)

    def _check_for_missing_columns(self, table, data):
        query = f"PRAGMA table_info({table});"
        tables = self.execute(query)
        if tables:
            existing = [i[1] for i in self.execute(query)]
            these_columns = self._get_all_keys(data)
            adds = [f for f in these_columns if f not in existing]
        else:
            adds = []
        return adds

    def execute(self, query):
        self.cursor.execute(query)
        self.conn.commit()
        rows = self.cursor.fetchall()
        return rows

    def execute_dict(self, query):
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        rows = []
        if data:
            keys = data[0].keys()
            for row in data:
                rows.append(dict(zip(keys, [i for i in row])))
            self.conn.commit()
            self.conn.row_factory = None
            self.cursor = self.conn.cursor()
        return rows

    def flatten_json(self, item):
        out = {}
        def flatten(subitem, name=''):
            if isinstance(subitem, dict):
                for i in subitem:
                    flatten(subitem[i], name + i + '_')
            elif type(subitem) is list:
                if len(subitem) > 0 and isinstance(subitem[0], dict):
                    for i in subitem[0]:
                        flatten(subitem[0], name + i + '_')
                else:
                    out[name[:-1]] = ", ".join(subitem)
            else:
                out[name[:-1]] = subitem
        flatten(item)
        return out

    def insert(self, table, data):
        '''[
        {"metric1": "value1", "metric2": "value1"},
        {"metric1": "value2", "metric2": "value2"}
        ]
        '''
        # Some items in data are lists.  Flatten
        '''
        for row in data:
            for key in list(row):
                if isinstance(row[key], list):
                    nested = row.pop(key)
                    if nested and isinstance(nested[0], dict):
                        row[key] = str(nested)
                    elif nested and isinstance(nested[0], str):
                        row[key] = ", ".join(nested)
        '''
        for x, row in enumerate(data):
            data[x] = self.flatten_json(row)
        # Make sure every row has all the keys so we dont have to continually check
        data = self._normalize_data_rows(data)
        # Check if the table exists and create if not
        exists = self._check_if_table_exists(table)
        if not exists:
            self._create_table(table, data)
        # Check if all the columns are in the table, add if not
        new_columns = self._check_for_missing_columns(table, data)
        if new_columns:
            self._add_columns(table, data, new_columns)
        # Start actually inserting the data
        question_marks = ",".join("?" * len(data[0]))
        self.cursor.execute("BEGIN TRANSACTION")
        keys = self._get_all_keys(data)
        fields = "'" + "', '".join([i for i in keys]) + "'"
        for row in data:
            query = f"INSERT INTO {table} ({fields}) VALUES ({question_marks})"
            self.cursor.execute(query, [row[key] for key in keys])
        self.cursor.execute("COMMIT")

    def update(self, table, data):
        '''[
        {"metric1": "pk_value1", "metric2": "value1"}, 
        {"metric1": "pk_value2", "metric2": "value2"}
        ] 
        '''
        # Make sure every row has all the keys so we dont have to continually check
        data = self._normalize_data_rows(data)
        # Check if the table exists and create if not
        exists = self._check_if_table_exists(table)
        if not exists:
            self._create_table(table, data)
        # Check if all the columns are in the table, add if not
        new_columns = self._check_for_missing_columns(table, data)
        if new_columns:
            self._add_columns(table, data, new_columns)
        # Start actually inserting the data
        fields = [i for i in data[0].keys()]
        self.cursor.execute("BEGIN TRANSACTION")
        for row in data:
            query = f"UPDATE {table} SET "
            for x, field in enumerate(fields):
                if x == 0: continue # First field is the pk we'll use to update
                query += f"'{field}' = '{row[field]}', "
            query = query[:-2]
            query += f" where \"{fields[0]}\" = '{row[fields[0]]}';"
            self.cursor.execute(query)
        self.cursor.execute("COMMIT")

if __name__ == "__main__":
    db = sql_lite_db("test.db")
    data = [{"Process": "c:\\windows\\syswow64\\cscript.exe", "total": "4696", "perc": "19", "rn": "1"}, {"Process": "c:\\windows\\system32\\msiexec.exe", "total": "3459", "perc": "14", "rn": "2"}, {"Process": "c:\\program files\\safebreach\\safebreach endpoint simulator\\app\\22.4.5\\simulator\\sbsimulator.exe", "total": "3317", "perc": "13", "rn": "3"}, {"Process": "c:\\windows\\microsoft.net\\framework64\\v4.0.30319\\csc.exe", "total": "1178", "perc": "5", "rn": "4"}, {"Process": "c:\\users\\s2083405\\appdata\\local\\temp\\is-tldv5.tmp\\gimp-2.10.24-setup-3.tmp", "total": "1158", "perc": "5", "rn": "5"}]
    data = [{"Process": "c:\\windows\\syswow64\\cscript.exe", "total": None, "perc": "1.9", "rn": "1", "dale": "new"}, {"Process": "c:\\windows\\system32\\msiexec.exe", "total": "3459", "perc": "14", "rn": "2"}, {"Process": "c:\\program files\\safebreach\\safebreach endpoint simulator\\app\\22.4.5\\simulator\\sbsimulator.exe", "total": "3317", "perc": "13", "rn": "3"}, {"Process": "c:\\windows\\microsoft.net\\framework64\\v4.0.30319\\csc.exe", "total": "1178", "perc": "5", "rn": "4"}, {"Process": "c:\\users\\s2083405\\appdata\\local\\temp\\is-tldv5.tmp\\gimp-2.10.24-setup-3.tmp", "total": "1158", "perc": "5", "rn": "5"}]
    db.insert("benjamin", data)
