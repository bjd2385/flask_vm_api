DEBUG=true LOGLEVEL=DEBUG BLUEFYRE_AGENT_ID="751aeea3-a5d0-4257-b2a0-ab1be6e81e76" bluefyrectl execProgram gunicorn -c gunicorn_config.py api:app
