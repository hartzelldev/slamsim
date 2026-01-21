import os
import shutil
import zipfile
from datetime import datetime
from flask import url_for
from src.system import get_project_root, INCLUDES_DIR, LEAGUE_LOGO_FILENAME
from src.wrestlers import load_wrestlers
from src.tagteams import load_tagteams
from src.events import load_events
from src.belts import load_belts
from src.news import load_news_posts
from src.segments import _slugify # Import _slugify for consistent slug generation

STATIC_SITE_OUTPUT_DIR_NAME = 'static_export'
STATIC_SITE_ZIP_DIR_NAME = 'static_site_zips' # Directory to store generated zip files

def _get_static_site_output_path():
    """Returns the path where the static site will be generated."""
    return os.path.join(get_project_root(), STATIC_SITE_OUTPUT_DIR_NAME)

def _get_static_site_zip_path():
    """Returns the path where the static site zip files will be stored."""
    return os.path.join(get_project_root(), STATIC_SITE_ZIP_DIR_NAME)

def _save_static_page(client, url, dest_path):
    """Helper to make a request and save the response."""
    response = client.get(url, headers={'X-Static-Export': 'true'})
    if response.status_code == 200:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(response.data)
    else:
        print(f"Warning: Could not generate static page for {url} (Status: {response.status_code}).")

def generate_static_site(flask_app):
    """
    Generates a static version of the Fan Mode section of the application.
    Returns the path to the generated zip file.
    """
    project_root = get_project_root()
    output_path = _get_static_site_output_path()
    zip_storage_path = _get_static_site_zip_path()

    # 1. Prepare output directories
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(zip_storage_path, exist_ok=True)

    # 2. Copy static assets
    static_src = os.path.join(project_root, 'static')
    static_dest = os.path.join(output_path, 'static')
    if os.path.exists(static_src):
        shutil.copytree(static_src, static_dest)

    # Copy league logo if it exists
    logo_src = os.path.join(project_root, INCLUDES_DIR, LEAGUE_LOGO_FILENAME)
    logo_dest_dir = os.path.join(output_path, INCLUDES_DIR)
    if os.path.exists(logo_src):
        os.makedirs(logo_dest_dir, exist_ok=True)
        shutil.copy2(logo_src, os.path.join(logo_dest_dir, LEAGUE_LOGO_FILENAME))

    # 3. Generate Fan Mode pages
    with flask_app.test_client() as client:
        # Base fan pages
        base_fan_pages = {
            'fan.home': 'index.html',
            'fan.roster': 'roster.html',
            'fan.events_list': 'events.html',
            'fan.champions_list': 'champions.html',
            'fan.news_list': 'news.html',
        }
        for endpoint, filename in base_fan_pages.items():
            with flask_app.app_context():
                url = url_for(endpoint)
            _save_static_page(client, url, os.path.join(output_path, filename))

        # Generate wrestler detail pages
        wrestlers = load_wrestlers()
        for wrestler in wrestlers:
            wrestler_name = wrestler.get('Name')
            if wrestler_name:
                with flask_app.app_context():
                    url = url_for('fan.view_wrestler', wrestler_name=wrestler_name)
                    static_filename = f"wrestler-{_slugify(wrestler_name)}.html"
                _save_static_page(client, url, os.path.join(output_path, static_filename))

        # Generate tagteam detail pages
        tagteams = load_tagteams()
        for tagteam in tagteams:
            tagteam_name = tagteam.get('Name')
            if tagteam_name:
                with flask_app.app_context():
                    url = url_for('fan.view_tagteam', tagteam_name=tagteam_name)
                    static_filename = f"tagteam-{_slugify(tagteam_name)}.html"
                _save_static_page(client, url, os.path.join(output_path, static_filename))

        # Generate event detail pages and archive pages
        events = load_events()
        event_years = set()
        for event in events:
            event_name = event.get('Event_Name')
            event_date_str = event.get('Date')
            if event_name and event_date_str:
                event_slug = _slugify(event_name)
                with flask_app.app_context():
                    url = url_for('fan.view_event', event_slug=event_slug)
                    static_filename = f"event-{event_slug}.html"
                _save_static_page(client, url, os.path.join(output_path, static_filename))
                
                try:
                    event_year = datetime.strptime(event_date_str, '%Y-%m-%d').year
                    event_years.add(event_year)
                except ValueError:
                    pass
        
        for year in sorted(list(event_years)):
            with flask_app.app_context():
                url = url_for('fan.archive_by_year', year=year)
                static_filename = f"events-archive-{year}.html"
            _save_static_page(client, url, os.path.join(output_path, static_filename))

        # Generate belt history pages
        belts = load_belts()
        for belt in belts:
            belt_id = belt.get('ID')
            if belt_id:
                with flask_app.app_context():
                    url = url_for('fan.belt_history', belt_id=belt_id)
                    static_filename = f"belt-{belt_id}.html"
                _save_static_page(client, url, os.path.join(output_path, static_filename))

        # Generate news detail pages and archive pages
        news_posts = load_news_posts()
        news_years = set()
        for post in news_posts:
            news_id = post.get('News_ID')
            news_date_str = post.get('Date')
            if news_id and news_date_str:
                with flask_app.app_context():
                    url = url_for('fan.view_news', news_id=news_id)
                    static_filename = f"news-{news_id}.html"
                _save_static_page(client, url, os.path.join(output_path, static_filename))

                try:
                    news_year = datetime.strptime(news_date_str, '%Y-%m-%d').year
                    news_years.add(news_year)
                except ValueError:
                    pass
        
        for year in sorted(list(news_years)):
            with flask_app.app_context():
                url = url_for('fan.news_archive_by_year', year=year)
                static_filename = f"news-archive-{year}.html"
            _save_static_page(client, url, os.path.join(output_path, static_filename))

    # 4. Create a zip archive of the generated static site
    archive_name = f"slamsim_fan_site_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    archive_path = shutil.make_archive(
        os.path.join(zip_storage_path, archive_name),
        'zip',
        root_dir=output_path # Archive the contents of output_path
    )

    # Clean up the temporary static_export directory
    shutil.rmtree(output_path)

    return archive_path
