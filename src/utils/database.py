from src.database.db_manager import DBManager

def get_db():
    """
    Inicjalizuje menedżera bazy danych i upewnia się, że tabele istnieją.
    """
    db = DBManager()
    db.create_tables()
    return db