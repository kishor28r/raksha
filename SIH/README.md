# 🛡️ RAKSHA — AI-Powered Emergency Response & Resource Allocation System

> **Smart India Hackathon (SIH) Prototype**  
> **Theme**: Disaster Management / Smart Governance  
> **Problem Statement**: *Intelligent Emergency Response & Resource Allocation*

---

## 📌 Problem Context
During major urban crises and multi-hazard disasters (floods, fires, building collapses, highway pileups), emergency dispatchers are overwhelmed with hundreds of uncoordinated reports. Currently:
1. **First-Come-First-Served (FCFS) Inefficiency**: Units are dispatched chronologically rather than by actual life-threat level.
2. **Resource Mismatch**: Wrong units get sent (e.g., standard police patrol sent to a chemical blaze while victims remain trapped).
3. **No Multi-Incident Optimization**: Dispatchers cannot solve global combinatorial assignment across simultaneous emergencies in real time.

---

## 💡 The RAKSHA Solution
RAKSHA introduces a dual-engine architecture:
1. **Multi-Factor NLP AI Severity Scorer**: Computes an explainable composite urgency score $S \in [0, 1]$ analyzing life threat keywords, casualty extraction, vulnerable populations (children, elderly, hospitals), and temporal escalation.
2. **Hungarian Algorithm Optimizer (`scipy.optimize.linear_sum_assignment`)**: Formulates emergency response as a minimum-weight bipartite matching problem with a priority-weighted cost matrix combining travel ETA, incident severity, and unit equipment suitability.
3. **Tactical Command Center HUD**: Real-time Leaflet map with pulsating radar markers, live vehicle movement simulation, dynamic routing polylines, and an AI vs. FCFS benchmark impact counter.

---

## 📐 Mathematical Formulation

### 1. AI Severity Scoring Equation
$$S_i = w_1 \cdot T_{\text{life}} + w_2 \cdot C_{\text{casualties}} + w_3 \cdot V_{\text{vulnerability}} + w_4 \cdot U_{\text{time}}$$
- $w_1 = 0.40, \quad w_2 = 0.25, \quad w_3 = 0.20, \quad w_4 = 0.15$
- Normalized into categorical tiers: **CRITICAL** ($\ge 0.75$), **HIGH** ($0.55 - 0.74$), **MEDIUM** ($0.35 - 0.54$), **LOW** ($< 0.35$).

### 2. Hungarian Resource Allocation Cost Matrix
Given $M$ active incidents and $N$ available units:
$$\min \sum_{i=1}^{M} \sum_{j=1}^{N} C_{ij} \cdot X_{ij}$$
Subject to:
$$\sum_{j} X_{ij} \le 1, \quad \sum_{i} X_{ij} \le 1, \quad X_{ij} \in \{0, 1\}$$

The pairwise cost $C_{ij}$ is defined as:
$$C_{ij} = \left(\text{ETA}_{ij} \cdot (1.0 + 4.0 \cdot S_i)\right) + \text{TypeMismatchPenalty}_{ij} - (30.0 \cdot S_i)$$
- Asymmetric matrix sizing ($M \neq N$) is handled via dummy padding with priority penalty offsets.

---

## 🚀 Quickstart & Running the Prototype

### Prerequisites
- Python 3.10+ (with `fastapi`, `uvicorn`, `scipy`, `numpy`, `pydantic`)

### Start Server & Command Center
```bash
py run.py
```
This automatically launches the FastAPI backend and opens the Tactical HUD in your browser at `http://127.0.0.1:8000`.

### Run Backend Unit Tests
```bash
py backend/test_backend.py
```

---

## 🎤 5-Minute Hackathon Demo Pitch Script for Judges

| Time | Action | What to Say |
|---|---|---|
| **0:00 - 0:45** | Introduce Problem & Map UI | *"Good morning respected judges! In emergency management, every second counts. Traditional dispatching operates on First-Come-First-Served, leading to priority inversions where a minor fender bender receives an ambulance while people trapped in a high-rise fire wait. We present **RAKSHA** — an AI-powered Emergency Response & Resource Allocation System."* |
| **0:45 - 1:45** | Load Scenario 1 & Show AI Scoring | *(Click **Load Scenario**)* *"Here we have 5 simultaneous emergencies in Delhi: a commercial building fire, an underpass flood, a multi-vehicle pileup, an LPG leak, and minor waterlogging. Notice our **AI Severity Engine** automatically parsed free-text descriptions, extracted casualties, detected vulnerable groups like pregnant women and elderly citizens, and categorized the high-rise fire as **CRITICAL (0.84)** while waterlogging received **LOW (0.29)**."* |
| **1:45 - 2:45** | Show Hungarian Allocation | *(Point to the **AI Dispatch Plan** cards)* *"Instead of naive nearest-neighbor matching, RAKSHA uses the **Hungarian Algorithm** on a multi-factor cost matrix. It automatically assigns the closest heavy **Fire Tender** to the commercial blaze and an **NDRF Rescue Squad** to the submerged underpass, perfectly matching equipment and minimizing life-threat response latency."* |
| **2:45 - 3:45** | One-Click Accept & Simulation | *(Click **Accept All AI Plans**)* *"With one click, the dispatcher confirms the optimal plan. Watch the map: our dynamic simulation animates emergency vehicles en route with real-time routing polylines and ETA tracking. Dispatchers retain full human-in-the-loop control with manual override capabilities."* |
| **3:45 - 4:30** | Benchmark Impact Counter | *(Point to the bottom **Benchmark HUD**)* *"Look at the bottom metrics: Compared to traditional FCFS dispatching, RAKSHA achieves a **~40% reduction in overall response delay**, a **>50% faster response to critical life-threat incidents**, and **completely eliminates equipment mismatches**."* |
| **4:30 - 5:00** | Live SOS Injection & Conclusion | *(Click **Inject Alert** or submit a custom SOS)* *"When an unexpected emergency arrives from CCTV or 112 calls, the Hungarian optimizer recalculates instantly in milliseconds. RAKSHA transforms chaotic disaster dispatch into intelligent, life-saving precision. Thank you!"* |
