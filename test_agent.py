from ai_agent import agent

response = agent.run("""
Domain: example.com
Days Remaining: 20

If <=47 → renew
Else → wait
""")

print("RESULT:", response)