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



backend run cmd : uvicorn backend:app --reload --port 8765 --workers 2
frontend run cmd :  python createagent.py
sqlite schema cmd : sqlite3 food1.db < schema.sql
sqlite seed cmd : sqlite3 food1.db < seed.sql