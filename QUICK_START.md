# 🚀 Quick Start Guide - LangOrch v0.1

## Prerequisites Check

Before starting, ensure you have:

### Required
- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed
- ✅ PostgreSQL 16+ **installed and running**
- ✅ Git installed

### Optional (for full features)
- Docker Desktop (for containerized services)
- pgAdmin (for database management)

---

## Option 1: Automated Setup (Recommended)

### Step 1: Start PostgreSQL

**Windows (Check if PostgreSQL is running):**
```powershell
# Check service status
Get-Service -Name postgresql*

# Start service if stopped
Start-Service postgresql-x64-16  # Adjust version number
```

**Or using pgAdmin:**
- Open pgAdmin
- Right-click on PostgreSQL server → Start

**Linux/Mac:**
```bash
# Check status
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql
```

### Step 2: Run the automated startup script

**Windows:**
```bash
start-dev.bat
```

**Linux/Mac:**
```bash
chmod +x start-dev.sh
./start-dev.sh
```

The script will:
1. ✅ Check PostgreSQL connection
2. ✅ Create database if needed
3. ✅ Run migrations
4. ✅ Seed test data
5. ✅ Start backend and frontend

---

## Option 2: Manual Setup (Step-by-Step)

### Step 1: Database Setup

```bash
# Open PostgreSQL command line
psql -U postgres

# In psql, run:
CREATE DATABASE langorch;
CREATE USER langorch WITH PASSWORD 'langorch123';
GRANT ALL PRIVILEGES ON DATABASE langorch TO langorch;
\q
```

### Step 2: Backend Setup

```bash
cd backend

# Install dependencies (first time only)
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_test_data.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend should now be running at:** http://localhost:8000

### Step 3: Frontend Setup (New Terminal)

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

**Frontend should now be running at:** http://localhost:3000

---

## Option 3: Docker Setup (Coming Soon)

For a fully containerized environment:

```bash
docker-compose up -d
```

*Note: Docker setup is planned for Version 0.2*

---

## 🎉 Access the Application

Once both services are running:

1. **Open your browser:** http://localhost:3000
2. **Login with test credentials:**
   - **Admin:** `admin@test.com` / `admin123`
   - **User:** `user@test.com` / `user123`

3. **Explore the features:**
   - ✅ Dashboard with stats
   - ✅ User management (CRUD)
   - ✅ Role-based navigation
   - ✅ Logout functionality

---

## 🔍 Verify Everything is Working

### Backend Health Check
```bash
curl http://localhost:8000/api/v1/health
# Should return: {"status": "healthy"}
```

### API Documentation
Visit: http://localhost:8000/api/v1/docs

### Database Connection
```bash
psql -U langorch -d langorch -c "SELECT COUNT(*) FROM users;"
# Should show at least 2 users
```

---

## 🐛 Troubleshooting

### PostgreSQL Not Running

**Windows:**
```powershell
# Find PostgreSQL service
Get-Service -Name postgresql*

# Start it
Start-Service <service-name>
```

**Linux/Mac:**
```bash
sudo systemctl start postgresql
# or
brew services start postgresql
```

### Port Already in Use

**Backend (Port 8000):**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**Frontend (Port 3000):**
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3000 | xargs kill -9
```

### Database Connection Failed

Check your `.env` file in `backend/`:
```env
DATABASE_URL=postgresql+asyncpg://langorch:langorch123@localhost:5432/langorch
```

### Migration Errors

Reset migrations:
```bash
cd backend
alembic downgrade base
alembic upgrade head
```

### Frontend Build Errors

Clean rebuild:
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

---

## 📚 Next Steps

Once you've confirmed everything is working:

1. **Read the features:** [VERSION_0.1_SUMMARY.md](VERSION_0.1_SUMMARY.md)
2. **Run tests:** [TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
3. **Explore the code:** Check the project structure
4. **Start development:** Follow [DEVELOPMENT_ROADMAP.md](docs/development-phases/DEVELOPMENT_ROADMAP.md)

---

## 🆘 Still Having Issues?

1. Check the logs:
   - Backend: Console output where you ran `uvicorn`
   - Frontend: Console output where you ran `npm run dev`
   - Database: Check PostgreSQL logs

2. Verify versions:
   ```bash
   python --version  # Should be 3.11+
   node --version    # Should be 18+
   psql --version    # Should be 16+
   ```

3. Review the detailed guides:
   - [GETTING_STARTED.md](docs/GETTING_STARTED.md)
   - [TESTING_GUIDE.md](docs/TESTING_GUIDE.md)

---

## ✅ Success Checklist

Before you start development, verify:

- [ ] PostgreSQL is running
- [ ] Database `langorch` exists
- [ ] Backend starts without errors (http://localhost:8000)
- [ ] Frontend starts without errors (http://localhost:3000)
- [ ] You can login with test credentials
- [ ] Dashboard loads correctly
- [ ] User management page works

**All checked?** 🎉 You're ready to develop!

---

*Last Updated: December 25, 2024*
