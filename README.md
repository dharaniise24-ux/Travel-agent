# Voyager Travel Agent

Voyager is a lightweight Flask-based travel concierge that evaluates trip requests, checks whether a destination and trip length fit a user's budget, and guides the user through a booking confirmation flow.

This project combines a simple web interface with an autonomous reasoning layer that extracts destination, budget, and duration from natural-language prompts.

## Features

- Travel request parsing from natural-language messages
- Destination detection for common Indian travel destinations such as Goa, Darjeeling, Manali, Jaipur, and Kerala
- Budget feasibility checks based on realistic trip costs
- Day-count extraction for trip planning
- Human-in-the-loop authorization flow before confirming bookings
- In-memory agent state for destination, budget, trip length, feasibility, and authorization
- Interactive frontend built with Flask templates and HTML/CSS

## Project Structure

```text
travel_agent_project/
├── app.py
├── templates/
│   └── index.html
└── README.md
```

## Tech Stack

- Python
- Flask
- HTML/CSS
- JavaScript (for the frontend interaction)

## Prerequisites

- Python 3.9+
- Flask installed in your environment

## Installation

1. Open a terminal in the project folder.
2. Create and activate a virtual environment if desired.
3. Install dependencies:

```bash
pip install flask
```

## Run the Application

From the project root, start the app:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## Example Usage

The app accepts travel requests like:

- "Plan a Goa trip under 20000 for 4 days"
- "Travel to Manali for 5 days within 25000"
- "Book a Jaipur vacation for 3 days budget 15000"

The agent extracts:

- destination
- budget
- trip duration
- whether the budget is realistic
- whether the user is eligible to authorize the booking

## Backend API

### GET /

Serves the frontend chat page.

### POST /agent-chat

Sends a natural-language travel request to the agent.

Request body example:

```json
{
  "message": "Plan a Goa trip under 20000 for 4 days"
}
```

Response example:

```json
{
  "response": "✅ <b>Itinerary Verified & Feasible!</b> ...",
  "requires_approval": true,
  "destination": "Goa",
  "estimated_total": "₹18500",
  "is_feasible": true,
  "memory": {
    "destination": "Goa",
    "budget": 20000,
    "days": 4,
    "authorized": false,
    "is_feasible": true
  }
}
```

## Notes

- The app stores agent memory in memory only while the server is running.
- It is a demo travel planning assistant and does not persist bookings or user data.
- Destination and pricing logic are configured in the Python file and can be extended easily.

## License

This project is provided as a sample/demo application for educational and prototype use.
