import os
import markdown
from flask import Flask, render_template, url_for, g, request # Import g and request
from routes.divisions import divisions_bp
from routes.prefs import prefs_bp
from routes.wrestlers import wrestlers_bp
from routes.tagteams import tagteams_bp
from routes.events import events_bp
from routes.segments import segments_bp, _slugify # Import _slugify
from routes.belts import belts_bp
from routes.news import news_bp
from routes.booker import booker_bp # Import the new booker blueprint
from routes.fan import fan_bp       # Import the new fan blueprint
from routes.tools import tools_bp   # Import the new tools blueprint
from src.system import INCLUDES_DIR, LEAGUE_LOGO_FILENAME # Import INCLUDES_DIR and LEAGUE_LOGO_FILENAME
from src.static_site_generator import (
    STATIC_SITE_OUTPUT_DIR_NAME, # Import for context
    WRESTLERS_SUBDIR, TAGTEAMS_SUBDIR, EVENTS_SUBDIR, CHAMPIONSHIPS_SUBDIR, NEWS_SUBDIR, ARCHIVE_SUBDIR
)

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = 'a_very_secret_key_for_flash_messages'
# Configure UPLOAD_FOLDER to be the 'includes' directory within the project root
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, INCLUDES_DIR)

# Register blueprints
app.register_blueprint(divisions_bp)
app.register_blueprint(prefs_bp)
app.register_blueprint(wrestlers_bp)
app.register_blueprint(tagteams_bp)
app.register_blueprint(events_bp)
app.register_blueprint(segments_bp)
app.register_blueprint(belts_bp)
app.register_blueprint(news_bp)
app.register_blueprint(booker_bp) # Register the booker blueprint
app.register_blueprint(fan_bp)     # Register the fan blueprint
app.register_blueprint(tools_bp)   # Register the tools blueprint

# Register a custom Jinja2 filter for markdown
@app.template_filter('markdown')
def markdown_filter(text):
    return markdown.markdown(text)

# Mapping Flask endpoints to their static file paths (relative to STATIC_SITE_OUTPUT_DIR_NAME)
# Use placeholders for dynamic parts that will be filled by static_url_for_func
STATIC_PATH_MAP = {
    'fan.home': 'index.html',
    'fan.roster': os.path.join(WRESTLERS_SUBDIR, 'index.html'),
    'fan.events_list': os.path.join(EVENTS_SUBDIR, 'index.html'),
    'fan.champions_list': os.path.join(CHAMPIONSHIPS_SUBDIR, 'index.html'),
    'fan.news_list': os.path.join(NEWS_SUBDIR, 'index.html'),
    'fan.view_wrestler': os.path.join(WRESTLERS_SUBDIR, '{wrestler_name_slug}.html'),
    'fan.view_tagteam': os.path.join(TAGTEAMS_SUBDIR, '{tagteam_name_slug}.html'),
    'fan.view_event': os.path.join(EVENTS_SUBDIR, '{event_slug}.html'),
    'fan.belt_history': os.path.join(CHAMPIONSHIPS_SUBDIR, '{belt_id_slug}.html'),
    'fan.view_news': os.path.join(NEWS_SUBDIR, '{news_id}.html'),
    'fan.archive_by_year': os.path.join(EVENTS_SUBDIR, ARCHIVE_SUBDIR, '{year}.html'),
    'fan.news_archive_by_year': os.path.join(NEWS_SUBDIR, ARCHIVE_SUBDIR, '{year}.html'),
}

# Before request handler to set static_export_mode and current_static_path
@app.before_request
def set_static_export_mode():
    g.static_export_mode = request.headers.get('X-Static-Export') == 'true'
    # Get the static path of the page currently being rendered from the header
    g.current_static_path = request.headers.get('X-Static-Path')
    if g.static_export_mode and not g.current_static_path:
        # Fallback if header is missing (shouldn't happen if generator is updated)
        print("Warning: X-Static-Path header missing during static export. Assuming root path.")
        g.current_static_path = 'index.html' # Default to root for relative path calculation

# Context processor to make static_export_mode and a static_url_for available in templates
@app.context_processor
def inject_static_export_mode_and_urls():
    static_export = getattr(g, 'static_export_mode', False)
    current_static_path = getattr(g, 'current_static_path', 'index.html') # Default to root if not set

    def _get_relative_url(current_page_static_path, target_static_file_path):
        """Calculates the relative path from current_page_static_path to target_static_file_path."""
        # current_page_static_path example: 'wrestlers/john-cena.html'
        # target_static_file_path example: 'static/style.css' or 'index.html'

        # Get the directory of the current page
        current_dir = os.path.dirname(current_page_static_path)
        
        # Calculate the relative path
        return os.path.relpath(target_static_file_path, start=current_dir)

    def static_url_for_func(endpoint, **values):
        if static_export:
            target_static_file_path = None
            
            if endpoint == 'static':
                filename = values.get('filename')
                if filename:
                    target_static_file_path = os.path.join('static', filename)
            elif endpoint in STATIC_PATH_MAP:
                path_template = STATIC_PATH_MAP[endpoint]
                # Fill in dynamic parts for detail pages
                if endpoint == 'fan.view_wrestler':
                    target_static_file_path = path_template.format(wrestler_name_slug=_slugify(values.get('wrestler_name', '')))
                elif endpoint == 'fan.view_tagteam':
                    target_static_file_path = path_template.format(tagteam_name_slug=_slugify(values.get('tagteam_name', '')))
                elif endpoint == 'fan.view_event':
                    target_static_file_path = path_template.format(event_slug=values.get('event_slug', ''))
                elif endpoint == 'fan.belt_history':
                    belt_id = values.get('belt_id', '')
                    belt_id_slug = _slugify(str(belt_id)) # Consistent slug generation
                    target_static_file_path = path_template.format(belt_id_slug=belt_id_slug)
                elif endpoint == 'fan.view_news':
                    target_static_file_path = path_template.format(news_id=values.get('news_id', ''))
                elif endpoint in ['fan.archive_by_year', 'fan.news_archive_by_year']:
                    target_static_file_path = path_template.format(year=values.get('year', ''))
                else: # For base fan pages like home, roster, events_list, etc.
                    target_static_file_path = path_template
            
            if target_static_file_path:
                return _get_relative_url(current_static_path, target_static_file_path)
            else:
                # Fallback for unmapped fan endpoints during static export
                print(f"Warning: Unhandled endpoint '{endpoint}' during static export. Using dynamic URL.")
                return url_for(endpoint, **values)
        
        # If not in static_export_mode, or if the endpoint is not a fan mode endpoint, use regular url_for
        return url_for(endpoint, **values)

    return dict(static_export_mode=static_export, static_url_for=static_url_for_func)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html')

@app.route('/goodbye')
def goodbye():
    """Renders the goodbye page."""
    return render_template('goodbye.html')

if __name__ == '__main__':
    # This block is for direct execution, e.g., python src/app.py
    # In this scenario, we don't want to open a browser automatically.
    # The run.py script handles the browser opening and port selection.
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('FLASK_RUN_PORT', 5000))


