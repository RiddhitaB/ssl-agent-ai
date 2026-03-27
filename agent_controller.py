from decision_agent import run_decision_logic
import sys

def run_agent_system():
    print("TLS CERTIFICATE AGENT STARTED")

    if len(sys.argv) > 1:
        domain = sys.argv[1]
        print(f"Running for domain: {domain}")
        run_decision_logic(domain)
    else:
        print("Running for all domains")
        run_decision_logic()

    print("Agent execution completed")


if __name__ == "__main__":
    run_agent_system()