"""
RAKSHA: Live Integration & Verification Script
"""

import urllib.request
import json
import time

def test_live():
    base = 'http://127.0.0.1:8000'
    print("Testing Live Server at", base)

    # 1. Reset
    req = urllib.request.Request(f"{base}/api/simulation/reset", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        print("1. Reset Simulation:", resp.status)

    # 2. Load Scenario
    req = urllib.request.Request(f"{base}/api/scenarios/multi_hazard_crisis/load", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"2. Load Scenario: {data['scenario_name']} | Incidents: {data['incidents_loaded']}")

    # 3. Check Incidents
    with urllib.request.urlopen(f"{base}/api/incidents") as resp:
        incidents = json.loads(resp.read().decode())
        print(f"3. Active Incidents: {len(incidents)}")
        for inc in incidents:
            print(f"   - [{inc['severity']['level']}] {inc['title']} (Score: {inc['severity']['final_score']:.2f})")

    # 4. Check Hungarian Allocations
    with urllib.request.urlopen(f"{base}/api/optimize") as resp:
        opt = json.loads(resp.read().decode())
        print(f"4. Hungarian Optimization Plan: ({len(opt['allocations'])} pairings)")
        for a in opt['allocations']:
            print(f"   - {a['incident_title']} <= matched => {a['unit_name']} ({a['unit_type']}) [ETA: {a['eta_minutes']}m, Conf: {a['match_confidence_pct']}%, Cost: {a['cost_score']}]")

    # 5. Accept All
    req = urllib.request.Request(f"{base}/api/dispatch/accept-all", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"5. Batch Dispatch Result: Dispatched {data['dispatched_count']} units.")

    # 6. Step physical movement simulation
    req = urllib.request.Request(f"{base}/api/simulation/step?multiplier=2.0", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        en_route_count = sum(1 for u in data['units'] if u['status'] == 'EN_ROUTE')
        print(f"6. Simulation Step Active. Units En Route: {en_route_count}")

    # 7. Check Benchmark comparison
    with urllib.request.urlopen(f"{base}/api/benchmark") as resp:
        bm = json.loads(resp.read().decode())
        print("7. Benchmark Results:")
        print(f"   - FCFS Total ETA: {bm['fcfs']['total_response_time_min']} min | Mismatches: {bm['fcfs']['equipment_mismatches']}")
        print(f"   - RAKSHA AI Total ETA: {bm['raksha_ai']['total_response_time_min']} min | Mismatches: {bm['raksha_ai']['equipment_mismatches']}")
        print(f"   - Improvement Summary: {bm['improvements']['summary']}")

    # 8. Check Static Frontend Assets
    with urllib.request.urlopen(f"{base}/") as resp:
        html = resp.read().decode()
        assert "<title>RAKSHA" in html
        print(f"8. Frontend HTML is serving correctly (Length: {len(html)} chars)")

    with urllib.request.urlopen(f"{base}/static/styles.css") as resp:
        css = resp.read().decode()
        assert "--bg-core" in css
        print(f"9. CSS Stylesheet is serving correctly (Length: {len(css)} chars)")

    with urllib.request.urlopen(f"{base}/static/app.js") as resp:
        js = resp.read().decode()
        assert "initMap" in js
        print(f"10. App JavaScript is serving correctly (Length: {len(js)} chars)")

    print("\n" + "=" * 60)
    print("ALL 10 LIVE INTEGRATION VERIFICATIONS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_live()
