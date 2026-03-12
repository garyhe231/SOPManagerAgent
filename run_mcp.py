"""
Start the SOP Manager MCP server using Python 3.13.
Usage: python3.13 run_mcp.py
       or: /opt/homebrew/bin/python3.13 run_mcp.py
"""
import subprocess, sys, os

python313 = "/opt/homebrew/bin/python3.13"
script    = str(__file__).replace("run_mcp.py", "mcp_server.py")

os.execv(python313, [python313, script] + sys.argv[1:])
