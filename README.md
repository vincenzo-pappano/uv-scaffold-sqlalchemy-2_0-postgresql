# uv-scaffold-postgresql

```
sudo apt update
sudo apt install postgresql postgresql-client
```


## Switch to the postgres superuser
```
sudo -u postgres psql
```
## Inside psql:
```
postgres=# CREATE DATABASE mfr_database;
postgres=# CREATE USER fms_user WITH PASSWORD 'secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE mfr_database TO fms_user;
postgres=# CREATE SCHEMA mfr AUTHORIZATION fms_user;
postgres=# ALTER ROLE fms_user SET search_path TO mfr, public;
```
## Exit psql
```
\q
```

```
psql -h localhost -U fms_user -d mfr_database -W

mfr_database=> CREATE TABLE perm_check (id serial primary key);
mfr_database=> DROP TABLE perm_check;
mfr_database=> quit
```

## Start postgresql server
```
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
```
