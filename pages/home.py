import streamlit as st
import requests

from services.config import get_config, safe_urljoin

st.header("Truhlik")

config = get_config()

def get_actual_data():
    result= requests.get(safe_urljoin(config.get("be_path"), "/"))
    return result.json()

st.write(get_actual_data())