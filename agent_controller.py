from multi_agent_system import run_multi_agent_system

def run_agent_system():
    print(" Starting FULL MULTI-AGENT AI SYSTEM for SSL/TLS Management")
    results = run_multi_agent_system()
    print(" Multi-agent execution completed.")
    for r in results:
        print(f"{r['domain']} → {r['final_status']}")

if __name__ == "__main__":
    run_agent_system()