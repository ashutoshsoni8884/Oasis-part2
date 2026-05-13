
import sys
import os

# Add the parent directory to sys.path to import from app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Backend.db import SessionLocal
from Backend.models.agent_registry import AgentRegistry

def update_agent_versions():
    # Target versions
    updates = {
        "CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL": 14,
        "AGENTTEAMSCOLLECTORBUDDY": 15,
        "ARCREDITAGENTTEAM": 4
    }
    
    db = SessionLocal()
    try:
        print("--- Updating Agent Versions ---")
        for team_code, new_version in updates.items():
            agent = db.query(AgentRegistry).filter(AgentRegistry.team_code == team_code).first()
            if agent:
                old_version = agent.version
                agent.version = new_version
                print(f"Updated {team_code}: v{old_version} -> v{new_version}")
            else:
                print(f"Agent {team_code} not found in database. Please register it first.")
        
        db.commit()
        print("-------------------------------")
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_agent_versions()
