from dotenv import load_dotenv
load_dotenv()
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from app.models import TripPlanRequest
from backend.app.agents.agents import TripPlannerGraph

trip_planner = TripPlannerGraph()
request = TripPlanRequest(
    destination="北京",
    start_date="2026-03-04",
    end_date="2026-03-04",
)
trip_planner.plan_trip(request=request, user_id='test_user_id')