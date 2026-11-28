# Build the DuckDB database by running the SQL files in order.

from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"
SQL_LAYERS = ["01_staging", "02_marts"]       # run order; files inside a layer run by name


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sql_files() -> list[Path]:
    files = [f for layer in SQL_LAYERS for f in sorted((ROOT / "sql" / layer).glob("*.sql"))]
    if not files:
        raise FileNotFoundError("No .sql files under sql/01_staging or sql/02_marts")
    return files


def main() -> None:
    cfg = load_config()
    db_path = ROOT / cfg["duckdb_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        # relative paths inside the SQL ('data/interim/...') resolve from the repo root
        con.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
        for f in sql_files():
            con.execute(f.read_text(encoding="utf-8"))
            print(f"ran {f.relative_to(ROOT).as_posix()}")

        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        print(f"\n{'table':<24}{'rows':>8}")
        for (name,) in tables:
            print(f"{name:<24}{con.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]:>8,}")

    print(f"\nDone -> {db_path}")


if __name__ == "__main__":
    main()