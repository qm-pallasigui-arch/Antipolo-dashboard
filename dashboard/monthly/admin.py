"""First-run administrator creation; never ships a default password."""
import argparse
import getpass
import sqlite3

from .security import create_user
from .store import Store


def main():
    parser = argparse.ArgumentParser(description='Create the first monthly-system administrator.')
    parser.add_argument('username', help='Administrator username or email')
    args = parser.parse_args()
    password = getpass.getpass('Password (at least 12 characters): ')
    if password != getpass.getpass('Confirm password: '):
        parser.error('Passwords do not match.')
    try:
        create_user(Store(), args.username, password, bootstrap=True)
    except (ValueError, sqlite3.IntegrityError) as exc:
        parser.error(str(exc))
    print('Administrator created. Start the application and sign in at /login.')


if __name__ == '__main__':
    main()
