```
git config --global user.email "vincenzo.pappano@gmail.com"
git config --global user.name "Vincenzo Pappano"
git clone git@github.com:vincenzo-pappano/uv-scaffold-postgresql.git
```

```
mkdir $HOME/database
```

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```
source ~/.bashrc
```

# Install postgresql

```
sudo apt update
sudo apt install postgresql postgresql-client -y
```


# Configure postgresql

```
sudo -u postgres psql
```
```
CREATE DATABASE mfr_database;
CREATE USER fms_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mfr_database TO fms_user;
\q
```

```
sudo -u postgres psql -d mfr_database
```
```
CREATE SCHEMA mfr AUTHORIZATION fms_user;
ALTER ROLE fms_user SET search_path TO mfr, public;
\q
```

## Start postgresql server
```
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
```

# Test postgresql
```
psql -h localhost -U fms_user -d mfr_database -W
```

```
CREATE TABLE mfr.perm_check (id serial primary key);
DROP TABLE mfr.perm_check;
\q
```
