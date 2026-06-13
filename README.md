backend/data/
├── general/      ← place general HR/policy PDFs here
├── clinical/     ← place clinical protocol PDFs here
├── nursing/      ← place nursing procedure PDFs here
├── billing/      ← place billing/insurance PDFs here
└── equipment/    ← place equipment manual PDFs here


# Setup
cd backend
pip install -r requirements.txt

# Ingest documents (run once)
python ingest.py

# Start server
uvicorn main:app --port 8000