from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from datetime import datetime, timedelta
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from app.models import TripPlanRequest
# from backend.app.agents.agents import TripPlannerGraph
from backend.app.agents.multi_agnet import TripPlannerGraph

trip_planner = TripPlannerGraph()
request = TripPlanRequest(
    destination="北京",
    start_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d"),
    end_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d"),
)
asyncio.run(trip_planner.plan_trip(request=request, user_id='test_user_id'))
# trip_planner.plan_trip(request=request, user_id='test_user_id')
