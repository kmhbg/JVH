# JVH Puzzle Collection

A web application for managing and sharing your collection of Jan van Haasteren puzzles.

## Features

- Track which puzzles you own and have completed
- Share your collection with friends
- Lend puzzles to friends
- Upload puzzle images
- Export your collection to Excel
- Automatic import of new puzzles from official sources
- Automatic matching of existing puzzle images

## Installation

To install the project in a Proxmox to a LXC container, follow these steps from the host:

```bash
wget https://raw.githubusercontent.com/kmhbg/JVH/main/install_jvh_lxc.sh
chmod +x get_site.sh
./get_site.sh
```

To update to the latest version:

Run the following in the LXC container:

```bash
wget https://raw.githubusercontent.com/kmhbg/JVH/main/install_jvh_lxc.sh
chmod +x install_jvh_lxc.sh
./install_jvh_lxc.sh
```

### Manual Installation

1. Clone the repo:

   ```bash
   git clone https://github.com/your-username/jvh-puzzle-collection.git
   cd jvh-puzzle-collection
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate --database=default
   python manage.py migrate --database=puzzles_db
   ```

5. Create admin user:
   ```bash
   python manage.py create_admin_user
   ```

6. Import puzzles and images:
   ```bash
   python manage.py import_puzzles
   python manage.py match_existing_images
   ```

7. Start the development server:

```bash
python manage.py runserver
```

## Deployment

For production environment, use the included `get_site.sh` script which:

- Sets up an LXC container
- Installs all necessary packages
- Configures Nginx and Supervisor
- Sets up the databases
- Automatically imports puzzles and images

## Technical Stack

- Django (web framework)
- SQLite (separate databases for user data and puzzle data)
- Tailwind CSS (styling)
- Selenium (for automatic data collection)
- Nginx (web server)
- Supervisor (process management)
- Gunicorn (WSGI server)

## Commands

- `import_puzzles`: Imports puzzle data from official sources
- `match_existing_images`: Matches existing images with puzzles in the database
- `create_admin_user`: Creates/updates admin user
- `export_puzzles`: Exports a user's puzzle collection to Excel

## License

This project is licensed under the MIT License.

