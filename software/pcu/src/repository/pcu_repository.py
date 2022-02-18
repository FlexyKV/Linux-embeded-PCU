import sqlite3
from sqlite3 import Error
from datetime import datetime

def bitmap_to_port_state(bitmap: int, port_id: int):
    record_binary_states = [1 if digit == '1' else 0 for digit in bin(bitmap)[2:]]
    while len(record_binary_states) < 8:
        record_binary_states.insert(0, 0)
    return int(record_binary_states[port_id])


class PcuRepository:
    def __init__(self, db):
        self.db = db
        self.conn = None

    def open_connection(self):
        try:
            self.conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        except Error as e:
            print(e)
            return -1
        return self.conn

    def close_connexion(self):
        self.conn.close()

    def __get_records(self, start_time: datetime, end_time: datetime):
        try:
            cur = self.conn.cursor()
            get_timeframe_query = """SELECT id, record_datetime as "[timestamp]", record_port_states FROM record 
            WHERE record_datetime >= ? AND record_datetime < ?"""
            cur.execute(get_timeframe_query, [start_time, end_time])
            records = cur.fetchall()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return records

    def __insert_record(self, record_datetime: datetime):
        try:
            cur = self.conn.cursor()
            get_states_query = """SELECT port_state FROM port"""
            cur.execute(get_states_query)
            port_states = list(map(lambda st: st[0], cur.fetchall()))
            int_state = 0
            for state in port_states:
                int_state = (int_state << 1) | state
            insert_record_query = """INSERT INTO record VALUES (NULL, ?, ?)"""
            cur.execute(insert_record_query, [record_datetime, int_state])
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return cur.lastrowid

    def __get_measures(self, port_id: int, record_ids: list):
        try:
            cur = self.conn.cursor()
            get_measures = """SELECT measure.current, measure.voltage FROM measure WHERE record_id IN ({records})
             AND port_id = ?""".format(records=','.join(['?'] * len(record_ids)))
            query_args = record_ids + [port_id]
            cur.execute(get_measures, query_args)
            measures = cur.fetchall()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return measures

    def __insert_measure(self, record_id: int, port_id: int, current: float, voltage: float):
        try:
            cur = self.conn.cursor()
            get_port_query = """INSERT INTO measure VALUES (NULL, ?, ?, ?, ?)"""
            cur.execute(get_port_query, [record_id, port_id, current, voltage])
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return cur.lastrowid

    def __get_port_measures_from_datetimes(self, port_id: int, start_time: datetime, end_time: datetime) -> list:

        try:
            cur = self.conn.cursor()
            port_data_query = """
                       SELECT measure.current, measure.voltage, record.record_datetime as "[timestamp]", 
                       record.record_port_states FROM measure
                       INNER JOIN record ON measure.record_id = record.id
                       WHERE record.record_datetime >= ? AND record.record_datetime < ?
                       AND measure.port_id = ?
                       """
            cur.execute(port_data_query, [start_time, end_time, port_id])
            port_data = cur.fetchall()
            self.conn.commit()
        except Error as e:
            print(e)
            return [-1]
        return port_data

    def __get_port_states(self):
        try:
            cur = self.conn.cursor()
            get_port_query = """SELECT port_state FROM port"""
            cur.execute(get_port_query)
            port_states = cur.fetchall()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return port_states

    def __get_last_measures(self):
        try:
            cur = self.conn.cursor()
            get_port_query = """SELECT record.record_datetime as "[timestamp]", measure.current, measure.voltage 
            FROM measure
            INNER JOIN record ON record.id = measure.id 
            ORDER BY record.id DESC LIMIT 1"""
            cur.execute(get_port_query)
            last_measures  = cur.fetchall()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        return last_measures

    def get_port_state(self, port_id: int):
        self.open_connection()
        try:
            cur = self.conn.cursor()
            get_port_query = """SELECT port_state FROM port WHERE id = ?"""
            cur.execute(get_port_query, [port_id])
            port_state = cur.fetchone()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        self.close_connexion()
        if port_state is None:
            return port_state
        return port_state[0]

    def update_port_state(self, port_id: int, port_state: int):
        self.open_connection()
        try:
            cur = self.conn.cursor()
            get_port_query = """UPDATE port SET port_state = ? WHERE id = ?"""
            cur.execute(get_port_query, [port_state, port_id])
            get_port_query = """SELECT port_state FROM port WHERE id = ?"""
            cur.execute(get_port_query, [port_id])
            new_port_state = cur.fetchone()
            self.conn.commit()
        except Error as e:
            print(e)
            return -1
        self.close_connexion()
        return new_port_state[0]

    def insert_port_measures(self, record_datetime: datetime, current: list, voltage: list):

        self.open_connection()
        record_id = self.__insert_record(record_datetime)
        measure_ids = []
        for port_id in range(8):
            measure_ids.append(self.__insert_measure(record_id, port_id, current[port_id], voltage[port_id]))
        self.close_connexion()
        return measure_ids

    def get_port_measures(self, port_id: int, start_time: datetime, end_time: datetime):

        self.open_connection()

        record_data = self.__get_port_measures_from_datetimes(port_id, start_time, end_time)
        if not record_data:
            return -1

        record_measures = list(map(lambda r_measure: (r_measure[0], r_measure[1]), record_data))
        record_datetime = list(map(lambda r_vo: r_vo[2], record_data))
        record_port_states = list(map(lambda ps: bitmap_to_port_state(ps[3], port_id), record_data))

        self.close_connexion()

        return record_datetime, record_port_states, record_measures

    def get_instant_measures(self):
        self.open_connection()

        # should I manually get the present port states or return the port states of the last measure records ?
        port_states = self.__get_port_states()
        last_measures = self.__get_last_measures()

        self.close_connexion()

        return last_measures, port_states

    def create_ports(self):
        if self.get_port_state(2) is None:
            self.open_connection()
            try:
                new_port_query = "INSERT INTO port VALUES (?, 0)"
                for port in range(8):
                    cur = self.conn.cursor()
                    cur.execute(new_port_query, [port])
                self.conn.commit()
            except Error as e:
                print(e)
                return -1
            self.close_connexion()
        return 0

    def create_tables(self):
        """create tables"""

        self.open_connection()

        sql_create_record = """CREATE TABLE IF NOT EXISTS "record" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "record_datetime" DATETIME NOT NULL,
        "record_port_states" INTEGER NOT NULL
        );"""

        sql_create_port = """CREATE TABLE IF NOT EXISTS "port" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "port_state" INTEGER NOT NULL
        );"""

        sql_create_measure = """ CREATE TABLE IF NOT EXISTS "measure" (
        "id" INTEGER NOT NULL PRIMARY KEY,
        "record_id" INTEGER NOT NULL,
        "port_id" INTEGER NOT NULL,
        "current" REAL NOT NULL,
        "voltage" REAL NOT NULL,
        FOREIGN KEY ("record_id") REFERENCES "record" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY ("port_id") REFERENCES "port" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        );"""

        sql_create_bookmaking = """ CREATE TABLE IF NOT EXISTS "bookkeepings" (
        bk_name TEXT PRIMARY KEY, bk_value INTEGER NOT NULL);"""

        try:
            cur = self.conn.cursor()
            cur.execute(sql_create_record)
            cur.execute(sql_create_port)
            cur.execute(sql_create_measure)
            cur.execute(sql_create_bookmaking)
            self.conn.commit()
        except Error as e:
            print(e)
            return -1

        self.close_connexion()
        return 0

    def create_triggers(self):

        delete_old_records_trigger = """CREATE TRIGGER log_entries_limit_trigger BEFORE INSERT ON record
          FOR EACH ROW
          WHEN (SELECT bk_value FROM bookkeepings WHERE bk_name = 'Qty Entries')
            >= (SELECT bk_value FROM bookkeepings WHERE bk_name = 'Max Entries')
          BEGIN
            DELETE FROM log_entries
              WHEN timestamp = (SELECT timestamp FROM record ORDER BY timestamp LIMIT 1);
          END;
        """

        increment_bookkeeping_trigger = """CREATE TRIGGER log_entries_count_insert_trigger AFTER INSERT ON record
        FOR EACH ROW
        BEGIN
            UPDATE bookkeepings SET bk_value = bk_value + 1 WHERE bk_name = 'Qty Entries';
        end;
        """

        decrement_bookkeeping_trigger = """CREATE TRIGGER log_entries_count_delete_trigger AFTER DELETE ON record
        FOR EACH ROW
        BEGIN
            UPDATE bookkeepings SET bk_value = bk_value - 1 WHERE bk_name = 'Qty Entries';
        end;
        """

        initialise_bookkeeping = """INSERT into bookkeepings values ('Max Entries', 50);
        insert into bookkeepings values ('Qty Entries', 0);"""

