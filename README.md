User
  │
  ▼
LangChain create_agent + Gemini
  │   (decides tool call)
  ▼
StructuredTool wrapper (restaurants.search)
  │   (requests.post)
  ▼
API Server (server.py)  POST /invoke
  │
  │  calls restaurants_search()
  ▼
SQLite food.db (SELECT/INSERT/UPDATE)
  │
  ▼
JSON response from server
  │
  ▼
Tool output fed back to Gemini
  │
  ▼
Assistant response to user