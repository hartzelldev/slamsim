import json
import os
from src.segments import _slugify, _get_segments_file_path, load_segments, delete_summary_file

EVENTS_FILE_RELATIVE_TO_ROOT = 'data/events.json'

def _get_events_file_path():
    """Constructs the absolute path to the events JSON file."""
    # Assumes the script is run from the project root or src directory
    current_dir = os.path.dirname(__file__)
    # Go up one level from 'src' to the project root, then into 'data'
    project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
    return os.path.join(project_root, EVENTS_FILE_RELATIVE_TO_ROOT)

def load_events():
    """Loads events from the JSON file."""
    file_path = _get_events_file_path()
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        # Check if file is empty before loading JSON
        content = f.read()
        if not content:
            return []
        f.seek(0) # Reset file pointer to the beginning if content was read
        events = json.loads(content)
    
    # Ensure 'Event_Name' field is always a string
    for event in events:
        event_name = event.get('Event_Name')
        if isinstance(event_name, list):
            event['Event_Name'] = ' '.join(event_name) # Join list elements into a string
        elif not isinstance(event_name, str):
            event['Event_Name'] = '' # Default to empty string if not list or string
    return events

def save_events(events_list):
    """Saves events to the JSON file."""
    file_path = _get_events_file_path()
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(events_list, f, indent=4)

def get_event_by_name(event_name):
    """Retrieves a single event by its name."""
    events = load_events()
    for event in events:
        if event.get('Event_Name') == event_name:
            return event
    return None

def get_event_by_slug(event_slug):
    """Retrieves a single event by its slugified name."""
    events = load_events()
    for event in events:
        if _slugify(event.get('Event_Name', '')) == event_slug:
            return event
    return None

def add_event(event_data):
    """Adds a new event to the list."""
    events = load_events()
    if get_event_by_name(event_data['Event_Name']):
        return False # Event with this name already exists
    events.append(event_data)
    save_events(events)
    return True

def update_event(original_name, updated_data):
    """Updates an existing event."""
    events = load_events()
    for i, event in enumerate(events):
        if event.get('Event_Name') == original_name:
            # Check if name changed and new name already exists (and it's not the same event)
            if updated_data['Event_Name'] != original_name and get_event_by_name(updated_data['Event_Name']):
                return False # New name conflicts with another existing event
            events[i] = updated_data
            save_events(events)
            return True
    return False # Event not found

def load_event_summary_content(relative_summary_path):
    """Loads the content of a consolidated event summary file."""
    if not relative_summary_path:
        return ""
    
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
    file_path = os.path.join(project_root, relative_summary_path)

    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_event_summary(event_slug, content):
    """Saves the consolidated event summary to a Markdown file."""
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
    
    # The directory for event-specific data files (e.g., segments, matches, summaries)
    event_data_dir = os.path.join(project_root, 'data', 'events')
    os.makedirs(event_data_dir, exist_ok=True)
    
    filename = f'{event_slug}_summary.md'
    file_path = os.path.join(event_data_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    # Return the relative path from the project root
    return os.path.join('data', 'events', filename)

def delete_event(event_name):
    """Deletes an event by its name."""
    events = load_events()
    initial_len = len(events)
    events = [event for event in events if event.get('Event_Name') != event_name]
    if len(events) < initial_len:
        save_events(events)
        return True
    return False # Event not found
