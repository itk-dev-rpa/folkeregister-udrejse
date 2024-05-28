"""This module is reponsible for migrating data from the old robot to the new one."""

import os
from hashlib import sha256

import pyodbc
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection


def migrate(orchestrator_connection):
    """Migrate the data from the old database to the new one.
    Create a hashed id of the person and get the date the person was last checked.
    Ignore everything else.

    Args:
        orchestrator_connection: The connection to Orchestrator
    """
    db_cred = orchestrator_connection.get_credential("Udrejse Database")
    old_conn = pyodbc.connect(f'Server=srvweb13;Database=rpa;UID={db_cred.username};PWD={db_cred.password};Driver={{ODBC Driver 17 for SQL Server}}')

    new_conn = pyodbc.connect("Server=SRVSQLHOTEL03;Database=MKB-ITK-RPA;Trusted_Connection=Yes;Driver={ODBC Driver 17 for SQL Server}")

    old_records = old_conn.execute(
        """SELECT cpr, first_name, created_date FROM rpa.dbo.udrejse_kontrol
        WHERE created_date is not NULL
        AND first_name is not NULL"""
    ).fetchall()

    cursor = new_conn.cursor()

    for record in old_records:
        id_hash = sha256((record[0]+record[1]).encode()).hexdigest()
        cursor.execute("INSERT INTO [MKB-ITK-RPA].[dbo].[Udrejsekontrol] (id, check_date, manual_control) VALUES (?, ?, ?)", id_hash, record[2], None)

    cursor.commit()


if __name__ == '__main__':
    conn_string = os.getenv("OpenOrchestratorConnString")
    crypto_key = os.getenv("OpenOrchestratorKey")
    oc = OrchestratorConnection("Udrejse Migration", conn_string, crypto_key, "")
    migrate(oc)
