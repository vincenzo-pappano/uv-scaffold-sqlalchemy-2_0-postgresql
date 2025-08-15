```
git config --global user.email "vincenzo.pappano@gmail.com"
```
```
git config --global user.name "Vincenzo Pappano"
```
mkdir $HOME/database
```

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```
source ~/.bashrc
```

# uv-scaffold-postgresql

```
sudo apt update
```
```
sudo apt install postgresql postgresql-client
```


## Switch to the postgres superuser
```
sudo -u postgres psql
```
## Inside psql: (prompt: **postgres=#**)
```
CREATE DATABASE mfr_database;
```
```
CREATE USER fms_user WITH PASSWORD 'secure_password';
```
```
GRANT ALL PRIVILEGES ON DATABASE mfr_database TO fms_user;
```
```
CREATE SCHEMA mfr AUTHORIZATION fms_user;
```
```
ALTER ROLE fms_user SET search_path TO mfr, public;
```
```
\q
```

```
sudo systemctl start postgresql
```


```
psql -h localhost -U fms_user -d mfr_database -W
```

## Prompt **mfr_database=> **
```
CREATE TABLE perm_check (id serial primary key);
```
```
DROP TABLE perm_check;
```
```
quit
```

## Start postgresql server
```
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
```
