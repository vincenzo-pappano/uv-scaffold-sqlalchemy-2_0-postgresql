
# Postgresql + SALAlchemy
A project to run a postgresql database with sqlalchemy integration

## Initial Setup
<details>
<summary>Show/Hide</summary>

### Update name and email in git 
```
git config --global user.email "vincenzo.pappano@gmail.com"
git config --global user.name "Vincenzo Pappano"
```
### Clone repo
```
git clone git@github.com:vincenzo-pappano/uv-scaffold-postgresql.git
```

### Install uv
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Source .bashrc
```
source ~/.bashrc
```

### Install postgresql

```
sudo apt update
sudo apt install postgresql postgresql-client -y
```
</details>

<!------------------------------------------------------------------------------->

## Configure and Test Postgresql
<details>
<summary>Show/Hide</summary>

### Create database
```
sudo -u postgres psql
```
```
CREATE DATABASE mfr_database;
CREATE USER fms_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mfr_database TO fms_user;
\q
```
### Grant permissions
```
sudo -u postgres psql -d mfr_database
```
```
CREATE SCHEMA mfr AUTHORIZATION fms_user;
ALTER ROLE fms_user SET search_path TO mfr, public;
\q
```
### Start postgresql server
```
sudo systemctl start postgresql
```
```
sudo systemctl enable postgresql
sudo systemctl status postgresql
```
### Test postgresql
```
psql -h localhost -U fms_user -d mfr_database -W
```
```
CREATE TABLE mfr.perm_check (id serial primary key);
DROP TABLE mfr.perm_check;
\q
```
</details>


<!------------------------------------------------------------------------------->

## Run Application
<details>
<summary>Show/Hide</summary>

### One-time setup
```
uv sync 
```

### Run **fms-client**
```
uv run fms-client
```

### Run **fms-database-shell**
```
uv run fms-database-shell
```
</details>

<!------------------------------------------------------------------------------->

## Run Tests
<details>
<summary>Show/Hide</summary>

### One-time setup
```
uv sync --group dev
```

### Run **pytest**
```
uv run pytest -q
```

</details>


<!------------------------------------------------------------------------------->

## Build Application
<details>
<summary>Show/Hide</summary>

### Build
```
uv build
```

### Verify Build Output
The terminal should show something similar
```
Building source distribution...
Building wheel from source distribution...
Successfully built dist/fms_client-0.1.0.tar.gz
Successfully built dist/fms_client-0.1.0-py3-none-any.whl
```
</details>


<!------------------------------------------------------------------------------->

## Create .tar.gz
<details>
<summary>Show/Hide</summary>

### Create tarball
```
tar \
  --exclude="__pycache__" \
  --exclude=".pytest_cache" \
  --exclude=".git" \
  --exclude="dist" \
  --exclude="build" \
  --exclude="*.egg-info" \
  -czf project_snapshot.tar.gz .
```
### Verify
List initial 20 entries to sanity-check structure
```
tar -tzf project_snapshot.tar.gz | head -n 20
```
### Integrity check
```
# Verify gzip integrity
gunzip -t project_snapshot.tar.gz && echo "Gzip integrity OK"
```
</details>
