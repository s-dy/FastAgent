import os

from dotenv import load_dotenv
from fastagent.core import LLMClient
from fastagent.memory import MemoryConfig, MemoryManager

from app.agents import PlannerAgent
from app.models import TripPlanRequest

load_dotenv()

llm_client = LLMClient(model=os.getenv("DASHSCOPE_MODEL_NAME"), api_key=os.getenv("DASHSCOPE_API_KEY"), base_url=os.getenv("DASHSCOPE_BASE_URL"))
memory_manager = MemoryManager(
    user_id="test_user_id",
    config=MemoryConfig(
        enable_working=True,
        enable_episodic=True,
        enable_semantic=False,
        enable_perceptual=False,
        milvus_collection_name="travel_agent_test",
    )
)

agent = PlannerAgent(llm_service=llm_client, memory_manager=memory_manager)


request = TripPlanRequest(
    destination="北京",
    start_date="2026-3-01",
    end_date="2026-3-01",
    preferences=["历史", "美食"],
    hotel_preferences=["经济型"],
    budget="中等"
)

response = agent.plan_trip(request, "test_user_id")

print(response)