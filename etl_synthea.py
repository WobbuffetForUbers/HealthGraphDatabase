from neo4j import GraphDatabase
import os

# Database connection credentials
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

def run_etl():
    # 1. Load Patients
    patient_query = """
    LOAD CSV WITH HEADERS FROM 'file:///patients.csv' AS row
    MERGE (p:Patient {id: row.Id})
    SET p.first = row.FIRST,
        p.last = row.LAST,
        p.birthdate = row.BIRTHDATE,
        p.gender = row.GENDER,
        p.race = row.RACE,
        p.ethnicity = row.ETHNICITY,
        p.city = row.CITY
    """

    # 2. Load Providers
    provider_query = """
    LOAD CSV WITH HEADERS FROM 'file:///providers.csv' AS row
    MERGE (pr:Provider {id: row.Id})
    SET pr.name = row.NAME,
        pr.specialty = row.SPECIALITY,
        pr.gender = row.GENDER
    """

    # 3. Load Encounters
    encounter_query = """
    LOAD CSV WITH HEADERS FROM 'file:///encounters.csv' AS row
    MERGE (e:Encounter {id: row.Id})
    SET e.start = row.START,
        e.stop = row.STOP,
        e.description = row.DESCRIPTION,
        e.type = row.ENCOUNTERCLASS,
        e.reason_description = row.REASONDESCRIPTION
    WITH e, row
    MATCH (p:Patient {id: row.PATIENT})
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    WITH e, row
    MATCH (pr:Provider {id: row.PROVIDER})
    MERGE (e)-[:PERFORMED_BY]->(pr)
    """

    # 4. Load Conditions
    condition_query = """
    LOAD CSV WITH HEADERS FROM 'file:///conditions.csv' AS row
    MERGE (c:Condition {code: row.CODE, patient: row.PATIENT, start: row.START})
    SET c.description = row.DESCRIPTION,
        c.stop = row.STOP
    WITH c, row
    MATCH (p:Patient {id: row.PATIENT})
    MERGE (p)-[:HAS_CONDITION]->(c)
    WITH c, row
    MATCH (e:Encounter {id: row.ENCOUNTER})
    MERGE (e)-[:DIAGNOSED_WITH]->(c)
    """

    # 5. Load Medications
    medication_query = """
    LOAD CSV WITH HEADERS FROM 'file:///medications.csv' AS row
    MERGE (m:Medication {code: row.CODE, patient: row.PATIENT, start: row.START})
    SET m.description = row.DESCRIPTION,
        m.stop = row.STOP,
        m.total_cost = toFloat(row.TOTALCOST)
    WITH m, row
    MATCH (p:Patient {id: row.PATIENT})
    MERGE (p)-[:PRESCRIBED]->(m)
    WITH m, row
    MATCH (e:Encounter {id: row.ENCOUNTER})
    MERGE (e)-[:MEDICATION_ORDERED]->(m)
    """

    # 6. Load Observations
    observation_query = """
    LOAD CSV WITH HEADERS FROM 'file:///observations.csv' AS row
    WITH row LIMIT 100000
    MERGE (o:Observation {patient: row.PATIENT, date: row.DATE, code: row.CODE})
    SET o.description = row.DESCRIPTION,
        o.value = row.VALUE,
        o.units = row.UNITS,
        o.category = row.CATEGORY
    WITH o, row
    MATCH (p:Patient {id: row.PATIENT})
    MERGE (p)-[:HAS_OBSERVATION]->(o)
    WITH o, row
    MATCH (e:Encounter {id: row.ENCOUNTER})
    MERGE (e)-[:OBSERVATION_RECORDED]->(o)
    """

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        print("Loading Patients...")
        driver.execute_query(patient_query)
        print("Loading Providers...")
        driver.execute_query(provider_query)
        print("Loading Encounters...")
        driver.execute_query(encounter_query)
        print("Loading Conditions...")
        driver.execute_query(condition_query)
        print("Loading Medications...")
        driver.execute_query(medication_query)
        print("Loading Observations...")
        driver.execute_query(observation_query)
        print("ETL Audit & Update Complete!")

if __name__ == "__main__":
    run_etl()
