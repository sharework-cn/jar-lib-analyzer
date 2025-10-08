# Source Code Difference Analysis System

A web-based system for analyzing and comparing Java source code differences between services and their latest versions.

## Project Structure

```
source-diff-analyzer/
├── backend/                 # FastAPI backend service
│   ├── main.py             # Main application file
│   └── requirements.txt    # Python dependencies
├── frontend/               # Vue 3 frontend (to be created)
├── database/               # Database schema and scripts
│   └── schema.sql          # MySQL database schema
├── scripts/                # Data import and processing scripts
│   ├── import_data.py      # Data import script
│   ├── determine_latest_versions.py  # Latest version determination
│   └── test_setup.py       # Setup verification script
└── docs/                   # Documentation
    └── System_Design_Document.md
```

## Quick Start

### 1. Database Setup

```bash
# Create MySQL database
mysql -u root -p < database/schema.sql
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API will be available at `http://localhost:8000`

### 3. Data Import

```bash
cd scripts

# Import all data
python import_data.py --all

# Or import specific data
python import_data.py --services-csv ../../work/prod/server_info.csv
python import_data.py --jar-csv ../../work/output/jar_analysis_report_20251007.csv
python import_data.py --lib-decompile-dir ../../work/prod/lib-decompile --classes-decompile-dir ../../work/prod/classes-decompile
```

### 4. Determine Latest Versions

```bash
python determine_latest_versions.py
```

### 5. Test Setup

```bash
python test_setup.py
```

## API Endpoints

- `GET /api/services` - List all services
- `GET /api/services/{id}` - Get service details
- `GET /api/services/{id}/java-classes` - Get Java classes for a service
- `GET /api/services/{id}/java-classes/{class_id}/differences` - Get differences for a Java class
- `GET /api/java-classes/{class_full_name}/latest` - Get latest version of a class

## Development Status

### ✅ Completed
- Database schema design
- Backend API framework (FastAPI)
- Data import scripts
- Latest version determination algorithm
- Basic API endpoints

### 🚧 In Progress
- Difference calculation engine
- Frontend Vue 3 application
- Advanced search functionality

### 📋 Planned
- Web interface for browsing differences
- Code diff visualization
- Performance optimization
- Production deployment

## Configuration

### Database
Update the database URL in the scripts:
```python
DATABASE_URL = "mysql+pymysql://username:password@host:port/database_name"
```

### Data Sources
The system expects data in the following locations:
- Services: `work/prod/server_info.csv`
- JAR Analysis: `work/output/jar_analysis_report_20251007.csv`
- JAR Decompiled: `work/prod/lib-decompile/`
- Class Decompiled: `work/prod/classes-decompile/`

## Contributing

1. Follow the existing code structure
2. Add proper logging and error handling
3. Update documentation for new features
4. Test with the provided test scripts

## License

This project is part of the Java Library Analyzer toolset.
