# Felix Conversational Orchestrator POC

A proof-of-concept multi-agent conversational AI system for handling financial products (remittances, credit, top-ups, bill payments, wallet) through natural conversation.

## Architecture

- **Main Orchestrator**: Entry point that routes to product agents
- **Product Agents**: Specialized agents for each product vertical
- **Stateful Flows**: State machine-based multi-step processes
- **Tool Execution**: Integration with mock backend services

## Tech Stack

- **Backend**: Python + FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **LLM**: OpenAI GPT-4o
- **Frontend**: React (Vite)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- OpenAI API key

### Option 1: Docker Compose (Recommended)

1. Copy environment file:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. Edit `backend/.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_key_here
   ```

3. Start all services:
   ```bash
   docker-compose up -d
   ```

4. Open the chat interface:
   ```
   http://localhost:5173
   ```

### Option 2: Local Development

1. Start PostgreSQL and Redis locally

2. Create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy and configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run the server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

5. Open the chat interface in your browser:
   ```
   http://localhost:5173
   ```

## API Endpoints

### Chat API

- `POST /api/chat/message` - Send a message and get a response
- `POST /api/chat/session` - Create a new chat session
- `GET /api/chat/session/{id}` - Get session information
- `POST /api/chat/session/{id}/end` - End a session

### Example Request

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_demo",
    "message": "Hola, quiero enviar dinero a mi mamá"
  }'
```

## Demo Scenarios

1. **Basic Navigation**
   - "Quiero enviar dinero" → Routes to remittances agent
   - "Volver al inicio" → Returns to main orchestrator

2. **Exchange Rate Query**
   - "¿Cuál es el tipo de cambio?" → Shows current USD to MXN rate

3. **Send Remittance**
   - "Quiero enviar $200 a mi mamá"
   - System shows recipients, calculates amounts, asks for confirmation

4. **Check Balance**
   - "Ver mi saldo" → Routes to wallet agent, shows balance

5. **Escalation**
   - "Quiero hablar con alguien" → Escalates to human agent

## Project Structure

```
conversationalBuilderPOC/
├── backend/
│   ├── app/
│   │   ├── core/           # Orchestration engine
│   │   ├── clients/        # HTTP clients for services gateway
│   │   ├── models/         # SQLAlchemy ORM models (sessions, users)
│   │   ├── routes/         # FastAPI routes
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── config/         # JSON agent/tool/flow configurations
│   │   └── seed/           # Seed data
│   └── requirements.txt
├── services/               # Independently deployable services gateway (port 8001)
│   └── app/
│       ├── routers/        # REST API endpoints
│       └── services/       # Mock service implementations
├── frontend/
│   └── react-app/          # React chat + admin UI (Vite)
└── docker-compose.yml
```

## Agents Configuration

The system comes pre-seeded with:

1. **Felix Assistant** (Main Orchestrator)
   - Routes to product agents
   - Handles general queries

2. **Remittances Agent**
   - Send money, check rates, view recipients

3. **Credit Agent**
   - View credit status, make payments

4. **Wallet Agent**
   - Check balance, add funds

5. **Top-Ups Agent**
   - Send phone top-ups to Mexico/LATAM

6. **Bill Pay Agent**
   - Pay utility bills (CFE, Telmex, etc.)

## Next Steps

- Conversation analytics dashboard
- WhatsApp integration
- Real backend service integration
- Auth and rate limiting
