import os
import inspect
from google.analytics.admin import AnalyticsAdminServiceClient

def inspect_client():
    print("Inspecting AnalyticsAdminServiceClient...")
    print(f"List Properties ArgSpec: {inspect.getfullargspec(AnalyticsAdminServiceClient.list_properties)}")
    print("-" * 20)
    print(f"List Properties Doc:\n{AnalyticsAdminServiceClient.list_properties.__doc__}")

if __name__ == "__main__":
    inspect_client()
