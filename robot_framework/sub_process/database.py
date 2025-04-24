"""This module handles interactions with databases."""

import hashlib
from collections import Counter
from dataclasses import dataclass

import pyodbc
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework import config


@dataclass
class Person:
    """A dataclass representing a person."""
    cpr: str
    name: str
    address: str
    address_count: int


def get_candidate_list(orchestrator_connection: OrchestratorConnection, udrejse_conn: pyodbc.Connection) -> list[Person]:
    """Create a prioritized list of candidates that should be checked for activity.
    The list is filtered to remove candidates that has been checked in the past and then sorted
    on the amount of people living on the same address.

    Args:
        orchestrator_connection: The connection to Orchestrator.

    Returns:
        A list of candidates as Person objects.
    """
    faelles_sql_creds = orchestrator_connection.get_credential(config.FAELLES_SQL)
    faelles_sql_conn = pyodbc.connect(f'Server=FaellesSQL;Database=Dataintegration;UID={faelles_sql_creds.username};PWD={faelles_sql_creds.password};Driver={{ODBC Driver 17 for SQL Server}}')

    checked_people = udrejse_conn.execute("SELECT id FROM [MKB-ITK-RPA].dbo.Udrejsekontrol").fetchall()
    checked_people = {p[0] for p in checked_people}

    candidates = faelles_sql_conn.execute(
        """SELECT CPR, Fornavn, Adresseringsadresse FROM Dataintegration.kmdIndkomst.[Udenlandske borgere i AAK]
        WHERE SenestIndrejseDatoDK < dateadd(month, -18, getdate())
        AND Vejkode NOT IN (9901, 9902, 9903, 9904, 9906, 9910, 9920)
        """
    )
    candidates = [list(c) for c in candidates]

    # Filter out already checked people
    for candidate in candidates[:]:
        cpr, name, _ = candidate
        id_hash = _create_id(cpr, name)

        if id_hash in checked_people:
            candidates.remove(candidate)

    # Sort on amount of people on their address
    adresse_conn = pyodbc.connect("Server=FaellesSQL;Database=DWH;Trusted_Connection=Yes;Driver={ODBC Driver 17 for SQL Server}")
    address_keys = adresse_conn.execute("SELECT CPR, Adressenoegle FROM DWH.Mart.AdresseAktuel").fetchall()

    address_count = Counter(ak[1] for ak in address_keys)
    address_keys = {ak[0]: ak[1] for ak in address_keys}

    for candidate in candidates:
        candidate.append(address_count[address_keys[candidate[0]]])

    candidates.sort(key=lambda c: c[3], reverse=True)

    # Convert to Person objects
    candidates = [Person(*c) for c in candidates]

    return candidates


def _create_id(cpr: str, first_name: str) -> str:
    """Create a hashed id for a person by using their cpr and first name.

    Args:
        cpr: The cpr number of the person.
        first_name: The first name of the person.

    Returns:
        A 64 character hex string.
    """
    return hashlib.sha256((cpr+first_name).encode()).hexdigest()


def update_person(connection: pyodbc.Connection, candidate: Person, has_income: bool):
    """Add a person to the database of checked people.

    Args:
        connection: The connection to the database.
        candidate: The candidate person object.
        has_income: Whether the candidate had any income.
    """
    id_hash = _create_id(candidate.cpr, candidate.name)
    cursor = connection.execute("INSERT INTO [MKB-ITK-RPA].dbo.Udrejsekontrol (id, check_date, manual_control) VALUES (?, CURRENT_TIMESTAMP, ?)", id_hash, not has_income)
    cursor.commit()
