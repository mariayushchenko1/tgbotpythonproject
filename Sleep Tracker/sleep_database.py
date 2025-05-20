import sqlite3


def init_db():
    conn = sqlite3.connect(sleep.db) # type: ignore
    cursor = conn.cursor()

    # Таблица для статистики
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS sleep (
        user_id INTEGER,
        date TEXT,
        sleep_time TEXT,
        wake_time TEXT
    )
    """
    )

    # Таблица времени напоминаний
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS notification_times (
        user_id INTEGER PRIMARY KEY,
        morning_time TEXT,
        evening_time TEXT
    )
    """
    )

    conn.commit()
    conn.close()
