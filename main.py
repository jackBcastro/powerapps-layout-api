from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class LayoutRequest(BaseModel):
    app_purpose: str
    features: List[str]

class ScreenComponent(BaseModel):
    screen: str
    components: List[str]

@app.post("/generate-layout")
def generate_layout(data: LayoutRequest):
    screens = []

    if "home" in [f.lower() for f in data.features] or "navigation" in data.app_purpose.lower():
        screens.append({"screen": "Home", "components": ["Welcome message", "Navigation menu"]})

    if "gallery" in [f.lower() for f in data.features]:
        screens.append({"screen": "Browse", "components": ["Gallery control", "Search box", "Sort dropdown"]})

    if "details" in [f.lower() for f in data.features]:
        screens.append({"screen": "Details", "components": ["Display form", "Back button", "Edit button"]})

    if "form" in [f.lower() for f in data.features] or "edit" in [f.lower() for f in data.features]:
        screens.append({"screen": "Edit", "components": ["Edit form", "Submit button", "Cancel button"]})

    if "approval" in [f.lower() for f in data.features]:
        screens.append({"screen": "Admin", "components": ["Approval button", "Comment box", "Status indicator"]})

    if not screens:
        screens.append({
            "screen": "Main",
            "components": ["Label", "Text input", "Submit button"]
        })

    return {"layout": screens}
