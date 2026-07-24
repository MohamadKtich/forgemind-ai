from secrets import token_urlsafe
for name in ("SECRET_KEY","DEVICE_API_KEY","LOCAL_RECOVERY_KEY"):
    print(f"{name}={token_urlsafe(48)}")
