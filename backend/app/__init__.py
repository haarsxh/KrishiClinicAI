"""KrishiClinic AI backend package.

Environment variables are loaded here so that every entrypoint - uvicorn,
Alembic, the seed script and any ad-hoc script - sees the same configuration
without each one having to remember to call load_dotenv() itself.

find_dotenv() walks upwards from the current working directory, so a .env in
either backend/ or the repository root is picked up. Real environment variables
always win over .env values, which keeps Docker and CI behaviour unchanged.
"""

from dotenv import load_dotenv

load_dotenv()
