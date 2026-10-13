from flask import Flask, request, jsonify, render_template
import re

app = Flask(__name__)

# ==============================================================
# AGENT MEMORY STORE
# ==============================================================
agent_memory = {
    "destination": None,
    "budget": None,
    "days": None,
    "authorized": False,
    "is_feasible": None
}

DESTINATION_COST_MODELS = {
    "goa": {"transport_min": 3500, "stay_nightly_min": 1200, "daily_living": 800, "climate": "29°C, Coastal sunny breeze 🌊"},
    "darjeeling": {"transport_min": 4200, "stay_nightly_min": 1500, "daily_living": 700, "climate": "13°C, Mountain fog & cool tea gardens 🌲"},
    "manali": {"transport_min": 4500, "stay_nightly_min": 1400, "daily_living": 750, "climate": "14°C, Crisp Alpine air 🏔️"},
    "jaipur": {"transport_min": 2800, "stay_nightly_min": 1100, "daily_living": 650, "climate": "27°C, Clear sunny skies ☀️"},
    "kerala": {"transport_min": 3800, "stay_nightly_min": 1300, "daily_living": 750, "climate": "28°C, Tropical backwaters 🌴"},
}

DEFAULT_COST_MODEL = {"transport_min": 3500, "stay_nightly_min": 1200, "daily_living": 700, "climate": "24°C, Pleasant weather"}

def tool_calculate_minimum_realistic_cost(destination, days):
    dest_key = destination.lower()
    model = DESTINATION_COST_MODELS.get(dest_key, DEFAULT_COST_MODEL)
    
    nights = max(1, days - 1)
    transport = model["transport_min"]
    stay = nights * model["stay_nightly_min"]
    living = days * model["daily_living"]
    
    floor_total = transport + stay + living
    return {
        "transport": transport,
        "stay": stay,
        "living": living,
        "floor_total": floor_total,
        "climate": model["climate"],
        "nightly_rate": model["stay_nightly_min"]
    }

# ==============================================================
# ROBUST EXTRACTION ENGINE
# ==============================================================
def extract_entities(user_msg):
    dest = None
    budget = None
    days = None

    clean = user_msg.strip()
    clean_lower = clean.lower()

    # 1. Destination Extraction
    # Pattern A: "<City> trip", "<City> vacation", "<City> tour"
    m_city_first = re.search(r"\b([a-zA-Z]{3,20})\s+(?:trip|tour|vacation|holiday|travel|getaway)\b", clean, re.IGNORECASE)
    if m_city_first and m_city_first.group(1).lower() not in ["plan", "make", "book", "this", "that"]:
        dest = m_city_first.group(1).title()

    # Pattern B: "trip to <City>", "travel to <City>", "visit <City>"
    if not dest:
        m_to_city = re.search(r"(?:to|for|in|visit)\s+([a-zA-Z]{3,20})", clean, re.IGNORECASE)
        if m_to_city:
            candidate = m_to_city.group(1).strip()
            if candidate.lower() not in ["days", "budget", "under", "within", "around", "trip", "plan"]:
                dest = candidate.title()

    # 2. Budget Extraction (matches: under, within, below, budget, rs, inr, ₹, etc.)
    m_budget = re.search(r"(?:under|within|below|budget|max|around|rs\.?|inr|₹)\s*[:=]?\s*(\d{3,7})", clean_lower)
    if not m_budget:
        # Fallback: single monetary number (e.g. "5000", "15000") that is not days
        all_nums = re.findall(r"\b\d{4,7}\b", clean_lower)
        if all_nums:
            budget = int(all_nums[0])
    else:
        budget = int(m_budget.group(1))

    # 3. Days Extraction (matches: 5days, 5 days, 5 nights, 5d)
    m_days = re.search(r"(\d+)\s*(?:days?|nights?|d\b)", clean_lower)
    if m_days:
        days = int(m_days.group(1))

    return dest, budget, days

# ==============================================================
# AUTONOMOUS AGENT REASONING ENGINE
# ==============================================================
def run_autonomous_agent(user_message):
    global agent_memory
    msg = user_message.strip()
    msg_lower = msg.lower()
    reasoning_steps = []

    # Reset command
    if "reset" in msg_lower:
        agent_memory = {"destination": None, "budget": None, "days": None, "authorized": False, "is_feasible": None}
        return {
            "response": "Agent memory reset. Please specify your travel destination, duration, and budget.",
            "reasoning_steps": [{"tool": "memory_clear()", "observation": "Purged destination, budget, and authorization state."}],
            "requires_approval": False,
            "is_feasible": None,
            "memory": agent_memory
        }

    # Human-in-the-Loop Confirmation
    if "approved" in msg_lower or "confirm booking" in msg_lower:
        if agent_memory.get("is_feasible") is False:
            return {
                "response": "⚠️ Cannot authorize booking: This itinerary exceeds your budget and is marked unfeasible. Please adjust your budget or days first.",
                "reasoning_steps": [{"tool": "guardrail_block()", "observation": "Blocked booking on unfeasible plan."}],
                "requires_approval": False,
                "destination": agent_memory.get("destination"),
                "estimated_total": "Blocked ❌",
                "is_feasible": False,
                "memory": agent_memory
            }

        if agent_memory.get("destination"):
            agent_memory["authorized"] = True
            return {
                "response": f"🎉 <b>Trip Authorized & Confirmed!</b><br><br>Bookings finalized for <b>{agent_memory['destination']}</b>. Confirmation vouchers generated.",
                "reasoning_steps": [{"tool": "booking_authorization()", "observation": "User authorization confirmed. Locked reservation."}],
                "requires_approval": False,
                "destination": agent_memory["destination"],
                "estimated_total": "Confirmed ✅",
                "is_feasible": True,
                "memory": agent_memory
            }

    # Revoke previous authorization whenever a new query is submitted
    agent_memory["authorized"] = False

    # Extract Entities
    dest_found, budget_found, days_found = extract_entities(msg)
    if dest_found:
        agent_memory["destination"] = dest_found
    if budget_found:
        agent_memory["budget"] = budget_found
    if days_found:
        agent_memory["days"] = days_found

    dest = agent_memory.get("destination")
    budget = agent_memory.get("budget")
    days = agent_memory.get("days") or 3

    if not dest:
        return {
            "response": "Please specify which destination you'd like to travel to.",
            "reasoning_steps": [],
            "requires_approval": False,
            "is_feasible": None,
            "memory": agent_memory
        }

    # Run Feasibility Tool
    calc = tool_calculate_minimum_realistic_cost(dest, days)
    minimum_required = calc["floor_total"]

    reasoning_steps.append({
        "tool": f"cost_feasibility_check(dest='{dest}', days={days})",
        "observation": (
            f"Calculated baseline expenses: Transit ₹{calc['transport']:,} + "
            f"Lodging ({days-1} nights @ ₹{calc['nightly_rate']:,}) ₹{calc['stay']:,} + "
            f"Meals/Commute ₹{calc['living']:,} = <b>Absolute Floor: ₹{minimum_required:,}</b>."
        )
    })

    # Unfeasible Scenario
    if budget and budget < minimum_required:
        agent_memory["is_feasible"] = False
        deficit = minimum_required - budget
        suggested_days = max(1, int((budget - calc["transport"]) / (calc["nightly_rate"] + 600)))
        
        reasoning_steps.append({
            "tool": "replan_budget_deficit()",
            "observation": f"Target budget ₹{budget:,} is lower than realistic minimum ₹{minimum_required:,} (Deficit: ₹{deficit:,}). Status: UNFEASIBLE."
        })

        response_text = f"""
        ❌ <b>Trip Not Financially Feasible</b><br><br>
        A <b>{days}-day trip to {dest}</b> cannot be done within <b>₹{budget:,}</b>.<br><br>
        📊 <b>Realistic Minimum Expense Breakdown:</b><br>
        • Travel/Transit (Round-trip): ~₹{calc['transport']:,}<br>
        • Budget Stay ({days-1} nights): ~₹{calc['stay']:,}<br>
        • Meals & Local Commute: ~₹{calc['living']:,}<br>
        • <b>Minimum Required Total:</b> <b>₹{minimum_required:,}</b> (Short by ₹{deficit:,})<br><br>
        💡 <b>Agent Re-planning Options:</b><br>
        1. Increase budget to at least <b>₹{minimum_required:,}</b> for a {days}-day trip.<br>
        2. Shorten the trip to <b>{max(1, suggested_days)} day(s)</b> to fit within ₹{budget:,}.<br>
        3. Switch to a closer local destination.
        """
        
        return {
            "response": response_text,
            "reasoning_steps": reasoning_steps,
            "requires_approval": False,
            "destination": dest,
            "estimated_total": f"₹{minimum_required:,} (Unfeasible for ₹{budget:,})",
            "is_feasible": False,
            "memory": agent_memory
        }

    # Feasible Scenario
    agent_memory["is_feasible"] = True

    reasoning_steps.append({
        "tool": "weather_lookup()",
        "observation": f"Forecast for {dest}: {calc['climate']}"
    })

    response_text = f"""
    ✅ <b>Itinerary Verified & Feasible!</b><br><br>
    🌤️ <b>Weather:</b> {calc['climate']}<br>
    📍 <b>Destination:</b> {dest} ({days} Days / {days-1} Nights)<br>
    ✈️ <b>Estimated Transit:</b> ~₹{calc['transport']:,}<br>
    🏨 <b>Lodging ({days-1} Nights):</b> ~₹{calc['stay']:,}<br>
    🍽️ <b>Daily Allowance:</b> ~₹{calc['living']:,}<br>
    💰 <b>Projected Total:</b> <b>₹{minimum_required:,}</b> (Within your budget target)<br><br>
    <i>Rates verified. Please authorize below to finalize reservations.</i>
    """

    return {
        "response": response_text,
        "reasoning_steps": reasoning_steps,
        "requires_approval": True,
        "destination": dest,
        "estimated_total": f"₹{minimum_required:,}",
        "is_feasible": True,
        "memory": agent_memory
    }

# ==============================================================
# FLASK ROUTE
# ==============================================================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/agent-chat", methods=["POST"])
def agent_chat():
    data = request.get_json() or {}
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"response": "Please enter a message."})

    result = run_autonomous_agent(user_msg)
    return jsonify(result)

if __name__ == "__main__":
    print("Voyager Travel Agent running at http://127.0.0.1:5000")
    app.run(debug=True)