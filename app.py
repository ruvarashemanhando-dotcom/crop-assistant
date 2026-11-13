import base64
import io

import requests
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------
# 1. PASTE YOUR crop.health API KEY between the quotes below.
#    Never share this file with the key inside it.
# ---------------------------------------------------------------
API_KEY = "PASTE_YOUR_KEY_HERE"

# When the app is online, the key is read safely from Streamlit "Secrets".
try:
    API_KEY = st.secrets["KINDWISE_API_KEY"]
except Exception:
    pass

API_URL = "https://crop.kindwise.com/api/v1/identification"
DETAILS = "common_names,description,treatment,symptoms,severity,spreading"

st.set_page_config(page_title="Crop Pest and Disease Assistant", page_icon="🌱")
st.title("🌱 AI Assistant for Crop Pests and Diseases")
st.write(
    "Upload a clear, close-up photo of the affected leaf or plant. "
    "You will get the likely problem and what to do about it."
)


def as_text(value):
    """Details can be plain text or a dict with a 'value' field."""
    if isinstance(value, dict):
        return value.get("value") or ""
    return value or ""


def photo_to_base64(image):
    """Shrink the photo first so the upload is fast on a slow connection."""
    small = image.copy()
    small.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    small.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return "data:image/jpeg;base64," + encoded


def diagnose(image):
    response = requests.post(
        API_URL,
        params={"details": DETAILS},
        headers={"Api-Key": API_KEY, "Content-Type": "application/json"},
        json={"images": [photo_to_base64(image)]},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def show_disease(suggestion, expanded):
    name = suggestion.get("name", "Unknown")
    chance = round(suggestion.get("probability", 0) * 100)
    details = suggestion.get("details") or {}

    with st.expander(f"{name}  ({chance}% match)", expanded=expanded):
        description = as_text(details.get("description"))
        if description:
            st.write(description)

        severity = as_text(details.get("severity"))
        if severity:
            st.markdown("**How serious:** " + severity)

        spreading = as_text(details.get("spreading"))
        if spreading:
            st.markdown("**How it spreads:** " + spreading)

        symptoms = details.get("symptoms")
        if isinstance(symptoms, dict) and symptoms:
            st.markdown("**Symptoms to look for:**")
            for title, text in symptoms.items():
                st.markdown(f"- **{title}:** {text}")

        treatment = details.get("treatment")
        if isinstance(treatment, dict) and treatment:
            st.markdown("**Treatment and prevention:**")
            for group, steps in treatment.items():
                if steps:
                    st.markdown(f"*{group.capitalize()}*")
                    for step in steps:
                        st.markdown(f"- {step}")


uploaded = st.file_uploader("Choose a plant photo", type=["jpg", "jpeg", "png"])

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="Uploaded plant photo", use_container_width=True)

    if API_KEY == "PASTE_YOUR_KEY_HERE":
        st.warning("Open app.py and paste your crop.health API key at the top.")
    elif st.button("Analyse photo"):
        try:
            with st.spinner("Checking the photo online... this can take a moment."):
                st.session_state["result"] = diagnose(image)
                st.session_state["result_for"] = uploaded.name
        except requests.exceptions.HTTPError as error:
            code = error.response.status_code
            if code == 401:
                st.error("The API key was rejected. Check that you pasted it correctly.")
            elif code == 429:
                st.error("The service is busy right now. Please try again shortly.")
            else:
                st.error(f"The service returned an error (code {code}).")
        except requests.exceptions.RequestException:
            st.error("Could not reach the service. Check your internet and try again.")

    data = st.session_state.get("result")
    if data and st.session_state.get("result_for") == uploaded.name:
        result = data.get("result", {})

        plant = result.get("is_plant", {})
        if plant and not plant.get("binary", True):
            st.warning("This photo may not show a crop. Try a closer, clearer photo of a leaf.")

        crops = result.get("crop", {}).get("suggestions", [])
        if crops:
            top = crops[0]
            st.subheader("Crop detected")
            st.write(f"{top.get('name', 'Unknown')} ({round(top.get('probability', 0) * 100)}% match)")

        diseases = result.get("disease", {}).get("suggestions", [])
        st.subheader("Possible problems")
        if diseases:
            for index, suggestion in enumerate(diseases[:3]):
                show_disease(suggestion, expanded=(index == 0))
        else:
            st.write("No clear problem was found.")

st.success("Spot problems early. Treat them right. Grow stronger crops.")
