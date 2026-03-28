# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**数据库运维管理平台** - A comprehensive database operation and maintenance management platform with a focus on MySQL slow query optimization.

- **Backend**: Flask (Python) + SQLAlchemy
- **Frontend**: Vue 3 + TypeScript + Vite + Element Plus
- **AI Integration**: Tongyi Qianwen (阿里云通义千问) for SQL optimization suggestions
- **Database**: MySQL (primary) + SQLite (for local development)

## Project Structure

```
claude-project/
├── backend/              # Flask backend
│   ├── app.py           # Main application with API endpoints
│   ├── config.py        # Configuration
│   ├── models/          # SQLAlchemy models
│   │   ├── slow_sql.py  # Slow SQL related models
│   │   └── db_connection.py  # Database connection models
│   ├── services/        # Business logic
│   │   ├── llm_service.py  # LLM service for SQL optimization
│   │   └── slow_sql_service.py  # Slow SQL services
│   ├── utils/           # Utilities
│   │   └── downloader.py  # Report download functionality
│   ├── data/            # SQLite database (local development)
│   ├── production/      # Production configuration
│   └── requirements.txt # Python dependencies
├── frontend/            # Vue 3 frontend
│   ├── src/
│   │   ├── api/         # API calls
│   │   │   ├── request.ts  # Axios instance and interceptors
│   │   │   ├── slowSql.ts  # Slow SQL API calls
│   │   │   └── dbConnection.ts  # Database connection API calls
│   │   ├── components/  # Vue components
│   │   │   ├── Layout/  # Layout components (AppLayout, Sidebar)
│   │   │   ├── SlowSQL/  # Slow SQL related components (SQLTable, FilterBar)
│   │   │   ├── Connection/  # Connection management components (ConnectionForm)
│   │   │   └── Common/  # Common components (CopyButton)
│   │   ├── views/       # Pages
│   │   │   ├── SlowSQLList.vue  # Slow SQL list page
│   │   │   ├── SlowSQLDetail.vue  # Slow SQL detail page
│   │   │   └── ConnectionList.vue  # Connection management page
│   │   ├── stores/      # Pinia store
│   │   │   └── dbConnection.ts  # Connection management state
│   │   ├── types/       # TypeScript types
│   │   ├── router/      # Vue Router
│   │   └── main.ts      # Application entry point
│   ├── package.json     # Frontend dependencies
│   └── vite.config.ts   # Vite configuration
├── static/              # Static files
│   └── css/             # Styles
├── articles/            # Documentation and articles
└── .claude/             # Claude Code configuration
```

## Setup & Configuration

1. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Copy `backend/.env.example` to `backend/.env` and configure:
   - Database connection (MySQL or SQLite)
   - `DASHSCOPE_API_KEY` for Tongyi Qianwen API

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

## Running

**Backend**:
```bash
cd backend
python app.py
```
Runs on http://localhost:5000

**Frontend**:
```bash
cd frontend
npm run dev
```
Runs on http://localhost:5173 (or next available port)

## Main Features

### 1. Slow SQL Management
- Slow query list with filtering (database, host, time range, optimization status)
- SQL optimization suggestions via LLM (Tongyi Qianwen)
- Batch optimization
- Markdown report download
- SQL execution plan analysis

### 2. Database Connection Management
- Add, edit, delete, and enable/disable database connections
- Connection testing
- Connection list management
- Duplicate connection name validation

### 3. UI Features
- Responsive design with Element Plus UI
- Advanced filtering and search capabilities
- Real-time notifications
- Data export and reporting

## API Endpoints

### Slow SQL Endpoints
- `GET /api/slow-sqls` - Get slow SQL list with filters
- `POST /api/slow-sqls/optimize` - Optimize SQL via LLM
- `POST /api/slow-sqls/batch-optimize` - Batch optimize SQLs

### Connection Endpoints
- `GET /api/connections` - Get all connections
- `GET /api/connections/<id>` - Get single connection
- `POST /api/connections` - Create connection
- `PUT /api/connections/<id>` - Update connection
- `DELETE /api/connections/<id>` - Delete connection
- `POST /api/connections/<id>/test` - Test connection
- `POST /api/connections/test-direct` - Test connection directly

## Key Technologies

### Backend
- **Flask**: Web framework
- **SQLAlchemy**: ORM for database operations
- **PyMySQL**: MySQL connector
- **Flask-CORS**: Cross-origin resource sharing
- **Requests**: HTTP client for API calls
- **Cryptography**: Password encryption

### Frontend
- **Vue 3**: UI framework with Composition API
- **TypeScript**: Type safety
- **Vite**: Build tool
- **Element Plus**: UI component library
- **Pinia**: State management
- **Vue Router**: Client-side routing
- **Axios**: HTTP client
