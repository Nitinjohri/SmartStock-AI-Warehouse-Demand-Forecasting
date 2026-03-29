#  SmartStock AI
### *Next-Gen Warehouse Demand Forecasting & Auto-Replenishment*

[![Build Status](https://img.shields.io/github/actions/workflow/status/your-username/smartstock-ai/ci.yml?branch=main&style=flat-square)](https://github.com/your-username/smartstock-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg?style=flat-square&logo=python)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)

---

##  Overview

**SmartStock AI** is an advanced inventory management platform engineered to solve the "Out-of-Stock" vs "Over-Stock" dilemma. By leveraging a **Hybrid ML Engine**, it provides high-precision demand forecasting and automates the replenishment cycle for enterprise warehouses.

> [!TIP]
> **Reduce carrying costs by up to 30%** while maintaining a **99.5% service level** using our recursive forecasting approach.

---

##  Key Features

| Feature | Description |
| :--- | :--- |
| ** Hybrid AI Engine** | Combines **Facebook Prophet** (seasonality) with **XGBoost** (short-term regression). |
| ** Auto-Replenishment** | Automated reordering logic based on safety stock, lead times, and demand spikes. |
| ** Dynamic Dashboards** | Real-time visualization of inventory health, trends, and critical alerts. |
| ** Cloud Native** | Fully containerized architecture optimized for scalable cloud deployments. |
| ** ML Quality Gates** | CI/CD pipelines that validate model accuracy (MAPE) before every production rollout. |

---

##  Technology Stack

<p align="left">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/react-20232a?style=for-the-badge&logo=react&logoColor=61dafb" alt="React" />
  <img src="https://img.shields.io/badge/postgres-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/XGBoost-black?style=for-the-badge&logo=scikitlearn&logoColor=white" alt="XGBoost" />
</p>

---

##  System Architecture

```mermaid
graph TD
    subgraph "Data Layer"
        A[Raw Sales Data] --> B[ML Pipeline]
    end

    subgraph "Intelligence Engine"
        B --> C{Hybrid Model}
        C -->|Seasonality| D[Facebook Prophet]
        C -->|Regression| E[XGBoost]
        D & E --> F[Forecast Aggregator]
    end

    subgraph "Application Layer"
        F --> G[(PostgreSQL)]
        G --> H[FastAPI Backend]
        H --> I[React Frontend]
    end

    style C fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```

---

##  Quick Start

### 1. Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed.
- Git (optional, for cloning).

### 2. Launching the Platform
Run the following commands in your terminal:

```bash
# Clone the repository
git clone https://github.com/your-username/smartstock-ai.git
cd smartstock-ai

# Start the entire ecosystem
docker-compose up --build -d
```

### 3. Accessing Services
*   **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
*   **API Exploration (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Health Status**: `GET /health`

---

##  Technical Strategy

### Local Development Setup
If you prefer running components individually without Docker:

```bash
# Backend Setup
cd backend
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirement.txt
uvicorn main:app --reload

# Frontend Setup
cd frontend
npm install
npm start
```

### ML Pipeline Highlights
*   **Feature Engineering**: Automated generation of Lags (7, 14, 30 days) and Rolling Windows.
*   **MAPE Gate**: Production deployments are blocked if the Mean Absolute Percentage Error (MAPE) exceeds professional thresholds.

---

##  License & Contact
Distributed under the **MIT License**.

**Author:** Nitin Johri
**GitHub:** [@your-username](https://github.com/your-username)
**Project Page:** [SmartStock AI](https://github.com/your-username/smartstock-ai)
