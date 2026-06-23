try:
    import MySQLdb  # mysqlclient — production MySQL
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
