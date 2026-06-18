try:
    import MySQLdb  # mysqlclient — dipakai di Docker/production
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
