try:
    import MySQLdb  # mysqlclient — linked to ServBay MySQL
except ImportError:
    try:
        import pymysql

        # PyMySQL advertises 1.4.6 for mysqlclient compatibility.
        # Django 6 rejects anything older than 2.2.1.
        pymysql.version_info = (2, 2, 7, "final", 0)
        pymysql.__version__ = "2.2.7"
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
