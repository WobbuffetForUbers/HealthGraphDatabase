from neo4j import GraphDatabase

def ingest_data(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    patients_query = """
    LOAD CSV WITH HEADERS FROM 'file:///patients.csv' AS row
    MERGE (p:Patient {id: row.Id})
    SET p.first = row.FIRST,
        p.last = row.LAST,
        p.birthdate = row.BIRTHDATE
    """
    
    encounters_query = """
    LOAD CSV WITH HEADERS FROM 'file:///encounters.csv' AS row
    MERGE (e:Encounter {id: row.Id})
    SET e.start = row.START,
        e.stop = row.STOP,
        e.description = row.DESCRIPTION
    WITH e, row
    MATCH (p:Patient {id: row.PATIENT})
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    """

    with driver.session() as session:
        print("Ingesting patients...")
        session.run(patients_query)
        print("Ingesting encounters...")
        session.run(encounters_query)
        print("Ingestion complete.")

    driver.close()

if __name__ == "__main__":
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = "password"
    ingest_data(URI, USER, PASSWORD)
