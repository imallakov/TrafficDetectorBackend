# 🚦 TrafficDetector — Backend

A **microservices backend** for traffic detection and analytics from video. The system ingests video, runs ML-based detection on it, and aggregates the results into statistics — split into independent, independently deployable services communicating over **Kafka**.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Microservices](https://img.shields.io/badge/Architecture-Microservices-blue?style=flat)
![Kafka](https://img.shields.io/badge/Kafka-Event_Streaming-231F20?style=flat&logo=apachekafka)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-336791?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)

---

## 🧩 Architecture

The system is composed of four independent services, each with its **own database** (database-per-service), coordinated through **Kafka** for asynchronous event streaming.

| Service | Port | Responsibility | Database |
| :--- | :--- | :--- | :--- |
| **auth-service** | `8001` | Authentication & authorization | `auth-db` (5432) |
| **video-service** | `8002` | Video upload & management | `video-db` (5433) |
| **ml-service** | `8003` | ML inference / detection on video | — (uses `ml-models` volume) |
| **statistics-service** | `8004` | Aggregated detection statistics | `stats-db` (5434) |

**Infrastructure:** Kafka + Zookeeper for event streaming, shared storage volume for media, and a dedicated volume for ML models.

```
            ┌───────────────┐
   client → │  auth-service │ (8001)
            └───────────────┘
            ┌───────────────┐   video uploaded
   client → │ video-service │ ───────────────►─┐
            └───────────────┘                  │ Kafka
            ┌───────────────┐                  ▼
            │   ml-service  │ (8003)  ◄── detection requests
            └───────────────┘                  │ results
            ┌────────────────────┐             ▼
            │ statistics-service │ (8004) ◄── aggregates events
            └────────────────────┘
```

---

## 🛠 Tech stack

- **Language:** Python
- **Pattern:** Microservices, database-per-service
- **Messaging:** Apache Kafka (+ Zookeeper)
- **Databases:** PostgreSQL 14 (one per service)
- **ML:** detection models served by `ml-service`
- **Orchestration:** Docker Compose

---

## 🚀 Getting started

### Prerequisites
- Docker & Docker Compose

### Run the full system

```bash
docker compose up --build -d
```

### Run core services only (without the ML service)

```bash
docker compose up --build auth-service video-service statistics-service -d
```

---

## 📚 API documentation

Each service exposes Swagger UI:

| Service | Docs |
| :--- | :--- |
| auth-service | http://localhost:8001/swagger/ |
| video-service | http://localhost:8002/swagger/ |
| ml-service | http://localhost:8003/swagger/ |
| statistics-service | http://localhost:8004/swagger/ |

ML service health check: `http://localhost:8003/health/`

---

## 🗂 Repository structure

```
TrafficDetectorBackend/
├── auth_service/
├── video_service/
├── ml_service/
├── statistics_service/
└── docker-compose.yml
```

---

## 👤 Author

**Yakup Allakov** — [LinkedIn](https://www.linkedin.com/in/imallakov) · [GitHub](https://github.com/imallakov)
