.PHONY: backend frontend test build verify

backend:
	cd backend && python -m fastapi dev app/main.py --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -q

build:
	cd frontend && npm run typecheck && npm run build

verify: test build
