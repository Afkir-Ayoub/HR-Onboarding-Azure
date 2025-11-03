import streamlit as st
import httpx
import time

# --- Configuration ---
FASTAPI_URL = "http://127.0.0.1:8000/chat"

# --- App Layout ---
st.set_page_config(page_title="HR Onboarding Assistant", page_icon="🤖")
col1, col2 = st.columns([6, 1])

with col1:
    st.title("🤖 AI HR Onboarding Assistant")
    st.caption("Your friendly guide to starting at Innovatech")

with col2:
    st.markdown("<br>", unsafe_allow_html=True) #
    if st.button("➕ New"):
        st.session_state.messages = []
        st.rerun()
                
# --- Chat History Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Logic ---
# React to user input
if prompt := st.chat_input("Ask me anything about your onboarding process!"):
    with st.chat_message("User"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display response
    with st.chat_message("Assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # --- Call FastAPI Backend ---
        try:
            with httpx.Client() as client:
                payload = {
                    "message": prompt,
                    "history": [msg for msg in st.session_state.messages if msg["role"] != "user"] 
                }
                response = client.post(
                    FASTAPI_URL,
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
                
                assistant_response  = response.json().get("reply", "Sorry, something went wrong.")
                
                for char in assistant_response:
                    full_response += char
                    time.sleep(0.005)
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

        except httpx.RequestError as e:
            full_response = f"Error: Could not connect to the backend. Please ensure it's running. Details: {e}"
            message_placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"An unexpected error occurred: {e}"
            message_placeholder.markdown(full_response)

    # Add to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})