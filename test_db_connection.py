from app.database.connection import get_connection


def main():
    connection = None

    try:
        connection = get_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT VERSION(), DATABASE()")

        result = cursor.fetchone()

        print("MySQL connection successful!")
        print("MySQL Version:", result[0])
        print("Database:", result[1])

        cursor.close()

    except Exception as error:
        print("Connection failed:", error)

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()