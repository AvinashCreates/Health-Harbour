g
[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose ps -a
docker compose logs --tail=150 backend
docker compose logs --tail=80 db
NAME                            IMAGE                         COMMAND                  SERVICE   CREATED         STATUS                          PORTS
healthcare-exchange-backend-1   healthcare-exchange-backend   "sh -c 'alembic upgr…"   backend   2 minutes ago   Restarting (1) 22 seconds ago   
healthcare-exchange-db-1        postgres:16-alpine            "docker-entrypoint.s…"   db        2 minutes ago   Up 2 minutes (healthy)          127.0.0.1:5432->5432/tcp
backend-1  |     return self._create_connection()
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 390, in _create_connection
backend-1  |     return _ConnectionRecord(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 674, in __init__
backend-1  |     self.__connect()
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 900, in __connect
backend-1  |     with util.safe_reraise():
backend-1  |          ^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py", line 146, in __exit__
backend-1  |     raise exc_value.with_traceback(exc_tb)
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 896, in __connect
backend-1  |     self.dbapi_connection = connection = pool._invoke_creator(self)
backend-1  |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/create.py", line 643, in connect
backend-1  |     return dialect.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 621, in connect
backend-1  |     return self.loaded_dbapi.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
backend-1  |     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  | sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "db" to address: Temporary failure in name resolution
backend-1  | 
backend-1  | (Background on this error at: https://sqlalche.me/e/20/e3q8)
backend-1  | Traceback (most recent call last):
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 146, in __init__
backend-1  |     self._dbapi_connection = engine.raw_connection()
backend-1  |                              ^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 3302, in raw_connection
backend-1  |     return self.pool.connect()
backend-1  |            ^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 449, in connect
backend-1  |     return _ConnectionFairy._checkout(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 1263, in _checkout
backend-1  |     fairy = _ConnectionRecord.checkout(pool)
backend-1  |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 712, in checkout
backend-1  |     rec = pool._do_get()
backend-1  |           ^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/impl.py", line 308, in _do_get
backend-1  |     return self._create_connection()
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 390, in _create_connection
backend-1  |     return _ConnectionRecord(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 674, in __init__
backend-1  |     self.__connect()
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 900, in __connect
backend-1  |     with util.safe_reraise():
backend-1  |          ^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py", line 146, in __exit__
backend-1  |     raise exc_value.with_traceback(exc_tb)
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 896, in __connect
backend-1  |     self.dbapi_connection = connection = pool._invoke_creator(self)
backend-1  |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/create.py", line 643, in connect
backend-1  |     return dialect.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 621, in connect
backend-1  |     return self.loaded_dbapi.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
backend-1  |     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  | psycopg2.OperationalError: could not translate host name "db" to address: Temporary failure in name resolution
backend-1  | 
backend-1  | 
backend-1  | The above exception was the direct cause of the following exception:
backend-1  | 
backend-1  | Traceback (most recent call last):
backend-1  |   File "/usr/local/bin/alembic", line 8, in <module>
backend-1  |     sys.exit(main())
backend-1  |              ^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/config.py", line 636, in main
backend-1  |     CommandLine(prog=prog).main(argv=argv)
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/config.py", line 626, in main
backend-1  |     self.run_cmd(cfg, options)
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/config.py", line 603, in run_cmd
backend-1  |     fn(
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/command.py", line 406, in upgrade
backend-1  |     script.run_env()
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/script/base.py", line 586, in run_env
backend-1  |     util.load_python_file(self.dir, "env.py")
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/util/pyfiles.py", line 95, in load_python_file
backend-1  |     module = load_module_py(module_id, path)
backend-1  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/alembic/util/pyfiles.py", line 113, in load_module_py
backend-1  |     spec.loader.exec_module(module)  # type: ignore
backend-1  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "<frozen importlib._bootstrap_external>", line 999, in exec_module
backend-1  |   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
backend-1  |   File "/app/migrations/env.py", line 44, in <module>
backend-1  |     run_migrations_online()
backend-1  |   File "/app/migrations/env.py", line 35, in run_migrations_online
backend-1  |     with connectable.connect() as connection:
backend-1  |          ^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 3278, in connect
backend-1  |     return self._connection_cls(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 148, in __init__
backend-1  |     Connection._handle_dbapi_exception_noconnection(
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2442, in _handle_dbapi_exception_noconnection
backend-1  |     raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 146, in __init__
backend-1  |     self._dbapi_connection = engine.raw_connection()
backend-1  |                              ^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 3302, in raw_connection
backend-1  |     return self.pool.connect()
backend-1  |            ^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 449, in connect
backend-1  |     return _ConnectionFairy._checkout(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 1263, in _checkout
backend-1  |     fairy = _ConnectionRecord.checkout(pool)
backend-1  |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 712, in checkout
backend-1  |     rec = pool._do_get()
backend-1  |           ^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/impl.py", line 308, in _do_get
backend-1  |     return self._create_connection()
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 390, in _create_connection
backend-1  |     return _ConnectionRecord(self)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 674, in __init__
backend-1  |     self.__connect()
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 900, in __connect
backend-1  |     with util.safe_reraise():
backend-1  |          ^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py", line 146, in __exit__
backend-1  |     raise exc_value.with_traceback(exc_tb)
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 896, in __connect
backend-1  |     self.dbapi_connection = connection = pool._invoke_creator(self)
backend-1  |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/create.py", line 643, in connect
backend-1  |     return dialect.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 621, in connect
backend-1  |     return self.loaded_dbapi.connect(*cargs, **cparams)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/usr/local/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
backend-1  |     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
backend-1  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  | sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "db" to address: Temporary failure in name resolution
backend-1  | 
backend-1  | (Background on this error at: https://sqlalche.me/e/20/e3q8)
db-1  | 
db-1  | PostgreSQL Database directory appears to contain a database; Skipping initialization
db-1  | 
db-1  | 2026-11-25 12:03:53.545 UTC [1] LOG:  starting PostgreSQL 16.16 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
db-1  | 2026-11-25 12:03:53.545 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
db-1  | 2026-11-25 12:03:53.545 UTC [1] LOG:  listening on IPv6 address "::", port 5432
db-1  | 2026-11-25 12:03:53.547 UTC [1] LOG:  listening on Unix socket "/run/postgresql/.s.PGSQL.5432"
db-1  | 2026-11-25 12:03:53.555 UTC [29] LOG:  database system was shut down at 2026-11-25 12:03:52 UTC
db-1  | 2026-11-25 12:03:53.565 UTC [1] LOG:  database system is ready to accept connections
[pamarthi-avinash@archlinux healthcare-exchange]$ 
