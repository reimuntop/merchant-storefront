from .seed_db import seed_fresh_install


def main() -> None:
    seeded = seed_fresh_install()
    if seeded:
        print("Database initialized and seeded.")
    else:
        print("Database already initialized. Skipping seed.")


if __name__ == "__main__":
    main()
