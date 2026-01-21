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
from src.static_site_generator import STATIC_SITE_OUTPUT_DIR_NAME # Import for static_url_map

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

# Before request handler to set static_export_mode based on a custom header
@app.before_request
def set_static_export_mode():
    g.static_export_mode = request.headers.get('X-Static-Export') == 'true'

# Context processor to make static_export_mode and a static_url_for available in templates
@app.context_processor
def inject_static_export_mode_and_urls():
    static_export = getattr(g, 'static_export_mode', False)
    
    def static_url_for_func(endpoint, **values):
        # If in static export mode, try to map to a static filename
        if static_export:
            # Base fan pages
            if endpoint == 'fan.home': return 'index.html'
            if endpoint == 'fan.roster': return 'roster.html'
            if endpoint == 'fan.events_list': return 'events.html'
            if endpoint == 'fan.champions_list': return 'champions.html'
            if endpoint == 'fan.news_list': return 'news.html'

            # Detail pages
            if endpoint == 'fan.view_wrestler' and 'wrestler_name' in values:
                return f"wrestler-{_slugify(values['wrestler_name'])}.html"
            if endpoint == 'fan.view_tagteam' and 'tagteam_name' in values:
                return f"tagteam-{_slugify(values['tagteam_name'])}.html"
            if endpoint == 'fan.view_event' and 'event_slug' in values:
                return f"event-{values['event_slug']}.html"
            if endpoint == 'fan.belt_history' and 'belt_id' in values:
                return f"belt-{values['belt_id']}.html"
            if endpoint == 'fan.view_news' and 'news_id' in values:
                return f"news-{values['news_id']}.html"
            
            # Archive pages
            if endpoint == 'fan.archive_by_year' and 'year' in values:
                return f"events-archive-{values['year']}.html"
            if endpoint == 'fan.news_archive_by_year' and 'year' in values:
                return f"news-archive-{values['year']}.html"

            # For static assets, ensure url_for('static', ...) still works correctly
            if endpoint == 'static':
                return url_for(endpoint, **values)
            
            # Fallback for any other endpoint during static export (should ideally not happen for fan mode)
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
    app.run(debug=True)

