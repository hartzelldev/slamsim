# SlamSim!

### A Fantasy Wrestling Booking Simulator

SlamSim! is a web-based application designed for fantasy wrestling bookers and fans. It provides a comprehensive suite of tools to create and manage your own wrestling promotion, from the roster to the championship lineages. Book events, define match outcomes, and watch as the application automatically updates win/loss records and title histories.

## Core Features

* **Roster Management:** Create and edit detailed profiles for individual wrestlers and tag teams, including personal stats, gimmick details, and contract information.
* **Divisions & Stables:** Organize your roster into logical divisions (e.g., Heavyweight, Women's) to manage rankings and storylines.
* **Championship Tracking:** Create unique championships for your promotion. The system tracks the current holder, status (Active/Vacant), and a complete, detailed reign history for every title.
* **Event Booking:** Build event cards segment by segment. The powerful Match Builder allows for the creation of complex matches with multiple participants and sides.
* **Dynamic Results:** Define match results, including winners, losers, and draws for every participant.
* **Automatic Record Keeping:** The "Event Runner" finalizes past events, automatically updating every wrestler's win/loss record and processing all championship changes based on match outcomes. This makes event results a permanent part of your league's history.

## Getting Started

Follow these instructions to get a local copy of SlamSim! up and running on your system.

### Prerequisites

You will need Python 3 and Pip installed on your system.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/hartzelldev/slamsim.git](https://github.com/hartzelldev/slamsim.git)
    cd slamsim
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  From the project's root directory, run the entry script:
    ```bash
    python run.py
    ```
2.  The application will start and provide a local URL, typically `http://127.0.0.1:5000/`. Open this URL in your web browser if it is not opened automatically.

## Basic Usage

SlamSim! is designed to be used in a logical order to build your promotion from the ground up. A typical workflow would be:

1.  **Create Divisions:** Start by creating the divisions for your promotion (e.g., Men's Heavyweight, Women's, Tag Team).
2.  **Create Belts:** Create the championships that will be contested within your divisions.
3.  **Create Wrestlers & Tag Teams:** Populate your roster with wrestlers and form official tag teams.
4.  **Create an Event:** Book a new show by creating an event and giving it a name and date.
5.  **Add Segments:** From the "Edit Event" page, add segments to your event card. Use the Match Builder to create matches and define the participants for each side.
6.  **Set Results:** In the Match Builder, set the winning side and the results for each individual participant.
7.  **Finalize the Event:** Once the event date has passed and the results are set, change the event's status to "Past" and click the "Finalize Event" button. This will lock the event and permanently update all statistics and championship histories.

**Note on Deletion:** In this alpha version, deleting entities (wrestlers, events, etc.) is an immediate and irreversible action that does **not** have a confirmation prompt. Please use the delete functions with caution, as deleting an entity can have a permanent impact on historical data and records. Deletion will be removed in a later version.

## Project Structure

* `run.py`: The main entry point to start the Flask application.
* `data/`: Contains all of the application's data stored in JSON files.
* `routes/`: Contains the Flask Blueprints that define the application's URL routes.
* `src/`: Contains the core application logic and data-handling functions (services).
* `static/`: Contains the CSS stylesheet.
* `templates/`: Contains all Jinja2 HTML templates, organized into subdirectories by feature.

## License

This software is provided free for personal, educational, and non-commercial use. You may use, modify, and distribute the software under the following conditions:

-   Credit must be given to the original author.
-   This software may not be used, in whole or in part, for any commercial purpose without explicit written permission.
-   All modified versions must retain this license and attribution.

For commercial licensing inquiries, please contact the author (gary@hartzell.us).
