# # pip install -qU langchain "langchain[anthropic]"
# from langchain.agents import create_agent
# from google import genai
# from dotenv import load_dotenv
# load_dotenv()
# client=genai.Client()  

# def get_weather(city: str) -> str:
#     """Get weather for a given city."""
#     return f"It's always sunny in {city}!"


# response = client.models.generate_content(
#     model="gemini-3-flash-preview",
#     contents="what is the weather in sf?",
#     config=types.GenerateContentConfig(
#         system_instruction="You are a helpful assistant",
#         tools=[get_weather],  # passing python function directly enables auto tool calling
#     ),
# )

# print(response.text)



from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import datetime
from zoneinfo import ZoneInfo

@tool
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

# Mock tool implementation
@tool("get_current_time", description="Get the local time in a city (e.g., 'Bangalore', 'San Francisco').")
def get_current_time(city: str) -> dict:
   
    try:
        # Step 1: Geocode the city name
        geolocator = Nominatim(user_agent="ai-agent")
        location = geolocator.geocode(city)
        # console.log(location)
        if not location:
            return f"Cannot find the city '{city}'. Try a more specific name."

        lat, lon = location.latitude, location.longitude

        # Step 2: Detect timezone from lat/lon
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lon)
        if not tz_name:
            return f"Could not determine timezone for '{city}'."

        # Step 3: Get current local time from timezone
        now = datetime.datetime.now(ZoneInfo(tz_name))
        local_time = now.strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)")

        return f"Local time in {city}: {local_time}"

    except Exception as e:
        return f"Error determining time: {str(e)}"


model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")

agent = create_agent(
    model=model,
    # tools=[get_weather,get_current_time],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in chennai?"}]}
)

print(result["messages"])
