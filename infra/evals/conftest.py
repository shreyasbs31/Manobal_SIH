import os

os.environ.setdefault("MANOBAL_SKIP_SECRETS", "1")
if os.environ.get("LIVE_EVALS") != "1":
    os.environ["MANOBAL_FORCE_LOCAL_PROVIDERS"] = "1"
