import streamlit as st
import httpx
import time

# --- Configuration ---
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{FASTAPI_BASE_URL}/chat"
UPLOAD_URL = f"{FASTAPI_BASE_URL}/upload"
AUTH_CHECK_URL = f"{FASTAPI_BASE_URL}/auth/check"
AUTH_INITIATE_URL = f"{FASTAPI_BASE_URL}/auth/initiate"
AUTH_STATUS_URL = f"{FASTAPI_BASE_URL}/auth/status"
AUTH_USER_URL = f"{FASTAPI_BASE_URL}/auth/user"
AUTH_LOGOUT_URL = f"{FASTAPI_BASE_URL}/auth/logout"

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

# --- Authentication Section ---
def check_auth_status():
    """Check if user is authenticated."""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(AUTH_CHECK_URL)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        # Backend might not be running or slow - don't show error, just return not authenticated
        return {"status": "not_authenticated", "authenticated": False}
    except httpx.RequestError as e:
        # Connection error - backend might not be running
        return {"status": "not_authenticated", "authenticated": False}
    except Exception as e:
        # Other errors - return not authenticated without showing error
        return {"status": "not_authenticated", "authenticated": False}


def initiate_auth():
    """Initiate device flow authentication."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(AUTH_INITIATE_URL)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. Please check if the backend is running and try again.")
        return None
    except httpx.RequestError as e:
        st.error(f"❌ Could not connect to backend. Please ensure the backend is running. Error: {str(e)}")
        return None
    except httpx.HTTPStatusError as e:
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        st.error(f"❌ Failed to initiate authentication: {error_detail}")
        return None
    except Exception as e:
        st.error(f"❌ Failed to initiate authentication: {str(e)}")
        return None


def poll_auth_status(flow_id):
    """Poll for authentication status."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(AUTH_STATUS_URL, params={"flow_id": flow_id})
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        # Timeout during polling - don't treat as fatal error, just return pending
        # This allows polling to continue even if one request times out
        return {"status": "pending", "message": "Request timed out, will retry..."}
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from backend
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        # Only treat 404 (flow not found) as a real error
        if e.response.status_code == 404:
            return {
                "status": "error",
                "error": "http_error",
                "error_description": f"Authentication flow not found: {error_detail}"
            }
        # For other HTTP errors, return pending to allow retry
        return {"status": "pending", "message": f"Backend error, will retry: {error_detail}"}
    except httpx.RequestError as e:
        # Connection errors during polling - don't treat as fatal, just return pending
        # This allows polling to continue even if backend is temporarily unavailable
        return {"status": "pending", "message": "Connection issue, will retry..."}
    except Exception as e:
        # Other exceptions - return pending to allow retry
        return {"status": "pending", "message": f"Unexpected error, will retry: {str(e)}"}


def get_user_info():
    """Get authenticated user information."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(AUTH_USER_URL)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return None


def logout():
    """Logout the user."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(AUTH_LOGOUT_URL)
            response.raise_for_status()
            return True
    except Exception as e:
        st.error(f"Failed to logout: {e}")
        return False


# Initialize session state for authentication
if "auth_status" not in st.session_state:
    st.session_state.auth_status = None
if "auth_flow_id" not in st.session_state:
    st.session_state.auth_flow_id = None
if "auth_polling" not in st.session_state:
    st.session_state.auth_polling = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "auth_flow_start_time" not in st.session_state:
    st.session_state.auth_flow_start_time = None
if "auth_flow_expires_in" not in st.session_state:
    st.session_state.auth_flow_expires_in = None
if "auth_verification_uri" not in st.session_state:
    st.session_state.auth_verification_uri = None
if "auth_user_code" not in st.session_state:
    st.session_state.auth_user_code = None

# Check authentication status on app load
if st.session_state.auth_status is None:
    auth_check = check_auth_status()
    if auth_check.get("authenticated"):
        st.session_state.auth_status = "authenticated"
        user_data = get_user_info()
        if user_data:
            st.session_state.user_info = user_data.get("user")
    else:
        st.session_state.auth_status = "not_authenticated"

# --- Authentication UI in Sidebar ---
with st.sidebar:
    st.header("🔐 Microsoft Account")
    
    if st.session_state.auth_status == "authenticated":
        # User is authenticated
        if st.session_state.user_info:
            st.success("✅ Authenticated")
            user = st.session_state.user_info
            st.caption(f"👤 {user.get('displayName', 'User')}")
            st.caption(f"📧 {user.get('mail', user.get('userPrincipalName', ''))}")
        
        if st.button("🚪 Logout", type="secondary"):
            if logout():
                st.session_state.auth_status = "not_authenticated"
                st.session_state.auth_flow_id = None
                st.session_state.auth_polling = False
                st.session_state.user_info = None
                st.rerun()
    
    elif st.session_state.auth_status == "authenticating":
        # Authentication in progress
        if st.session_state.auth_flow_id:
            # Display authentication instructions prominently
            if st.session_state.auth_verification_uri and st.session_state.auth_user_code:
                st.info("📋 **Authentication Instructions:**")
                
                # Display the link
                st.markdown("### 1. 🌐 Visit this link:")
                st.markdown(
                    f'<div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px; margin: 10px 0;">'
                    f'<a href="{st.session_state.auth_verification_uri}" target="_blank" style="font-size: 18px; color: #1f77b4; text-decoration: none; font-weight: bold; word-break: break-all;">'
                    f'{st.session_state.auth_verification_uri}'
                    f'</a></div>',
                    unsafe_allow_html=True
                )
                
                # Display the code in a large, prominent box
                st.markdown("### 2. 🔐 Enter this code:")
                st.markdown(
                    f'<div style="background-color: #f0f2f6; padding: 25px; border-radius: 10px; text-align: center; margin: 15px 0; border: 2px solid #1f77b4;">'
                    f'<h1 style="font-size: 56px; font-weight: bold; letter-spacing: 12px; color: #1f77b4; margin: 0; font-family: monospace;">'
                    f'{st.session_state.auth_user_code}'
                    f'</h1></div>',
                    unsafe_allow_html=True
                )
                
                # Check if device flow has expired
                if st.session_state.auth_flow_start_time and st.session_state.auth_flow_expires_in:
                    elapsed = time.time() - st.session_state.auth_flow_start_time
                    remaining = st.session_state.auth_flow_expires_in - elapsed
                    if remaining <= 0:
                        st.error("❌ Authentication code has expired. Please click 'Authenticate' again to get a new code.")
                        st.session_state.auth_status = "not_authenticated"
                        st.session_state.auth_flow_id = None
                        st.session_state.auth_polling = False
                        st.session_state.auth_flow_start_time = None
                        st.session_state.auth_flow_expires_in = None
                        st.session_state.auth_verification_uri = None
                        st.session_state.auth_user_code = None
                    else:
                        minutes = int(remaining // 60)
                        seconds = int(remaining % 60)
                        st.caption(f"⏱️ Time remaining: {minutes}m {seconds}s | The page will automatically refresh once you authenticate.")
                else:
                    st.caption("⏳ Waiting for authentication... The page will automatically refresh once you authenticate.")
            else:
                st.info("⏳ Waiting for authentication...")
            
            # Poll for authentication status
            if st.session_state.auth_polling:
                auth_result = poll_auth_status(st.session_state.auth_flow_id)
                
                if auth_result.get("status") == "authenticated":
                    st.session_state.auth_status = "authenticated"
                    st.session_state.auth_polling = False
                    st.session_state.auth_flow_start_time = None
                    st.session_state.auth_flow_expires_in = None
                    user_data = get_user_info()
                    if user_data:
                        st.session_state.user_info = user_data.get("user")
                    st.rerun()
                elif auth_result.get("status") == "error":
                    error_desc = auth_result.get('error_description', 'Unknown error')
                    # Check if it's an expiration error
                    if "expired" in error_desc.lower():
                        st.error(f"❌ {error_desc}")
                        st.info("💡 Please click 'Authenticate' again to get a new code.")
                    else:
                        st.error(f"❌ Authentication failed: {error_desc}")
                    st.session_state.auth_status = "not_authenticated"
                    st.session_state.auth_flow_id = None
                    st.session_state.auth_polling = False
                    st.session_state.auth_flow_start_time = None
                    st.session_state.auth_flow_expires_in = None
                    st.session_state.auth_verification_uri = None
                    st.session_state.auth_user_code = None
                else:
                    # Still pending, schedule auto-refresh
                    # Use a timer to prevent too frequent polling
                    if "last_poll_time" not in st.session_state:
                        st.session_state.last_poll_time = time.time()
                    
                    current_time = time.time()
                    # Poll every 3 seconds instead of 2 to reduce load
                    if current_time - st.session_state.last_poll_time >= 3:
                        st.session_state.last_poll_time = current_time
                        # Trigger refresh without blocking
                        st.rerun()
                    else:
                        # Use a placeholder to trigger auto-refresh without blocking UI
                        placeholder = st.empty()
                        placeholder.markdown("")  # Empty placeholder to trigger refresh
                        time.sleep(0.1)  # Small delay to prevent rapid polling
                        st.rerun()
    
    else:
        # Not authenticated
        st.warning("⚠️ Not authenticated")
        st.caption("Authenticate with Microsoft to enable calendar features")
        
        if st.button("🔑 Authenticate", type="primary"):
            auth_init = initiate_auth()
            if auth_init and auth_init.get("status") == "pending":
                st.session_state.auth_status = "authenticating"
                st.session_state.auth_flow_id = auth_init.get("flow_id")
                st.session_state.auth_polling = True
                st.session_state.auth_flow_start_time = time.time()
                st.session_state.auth_flow_expires_in = auth_init.get("expires_in", 900)  # Default 15 minutes
                st.session_state.auth_verification_uri = auth_init.get("verification_uri")
                st.session_state.auth_user_code = auth_init.get("user_code")
                
                st.rerun()
            # If auth_init is None or status is not pending, error was already shown by initiate_auth()

    st.divider()
    
    # --- File Upload Section ---
    st.header("📄 Upload Documents")
    st.caption("Upload PDF files to add them to the knowledge base")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Select a PDF file to upload and ingest into the system"
    )
    
    if uploaded_file is not None:
        st.info(f"📄 Selected: {uploaded_file.name}")
        st.caption(f"Size: {len(uploaded_file.getvalue()) / 1024:.2f} KB")
        if st.button("Upload & Ingest", type="primary"):
            with st.spinner("Uploading and processing file..."):
                try:
                    with httpx.Client(timeout=300.0) as client:
                        # Prepare file for upload
                        files = {
                            "file": (uploaded_file.name, uploaded_file.read(), "application/pdf")
                        }
                        
                        # Send to backend
                        response = client.post(
                            UPLOAD_URL,
                            files=files,
                        )
                        response.raise_for_status()
                        
                        result = response.json()
                        
                        if result.get("success"):
                            st.success(f"✅ {result.get('message', 'File uploaded successfully!')}")
                            st.info(f"📊 Documents ingested: {result.get('documents_ingested', 0)}")
                            st.caption(f"📁 Saved to: {result.get('file_path', 'N/A')}")
                        else:
                            st.error(f"❌ {result.get('message', 'Upload failed')}")
                            
                except httpx.RequestError as e:
                    st.error(f"Error: Could not connect to the backend. Please ensure it's running. Details: {e}")
                except httpx.HTTPStatusError as e:
                    error_detail = "Unknown error"
                    try:
                        error_response = e.response.json()
                        error_detail = error_response.get("detail", str(e))
                    except:
                        error_detail = str(e)
                    st.error(f"Upload failed: {error_detail}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                
# --- Chat History Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
# --- Suggestion Buttons ---
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
    
if len(st.session_state.messages) == 0 and not st.session_state.pending_prompt:  # Only show when chat is empty
    st.markdown("### 💡 Try asking:")
    
    suggestions = [
        "📋 What's on my agenda?",
        "👋 What do I need to do first?",
        "🏢 Tell me about Innovatech"
    ]
    
    cols = st.columns(len(suggestions))
    for idx, suggestion in enumerate(suggestions):
        with cols[idx]:
            if st.button(suggestion, key=f"suggest_{idx}", use_container_width=True):
                st.session_state.pending_prompt = suggestion
                st.rerun()
                
# --- Chat Logic ---
user_input = st.chat_input("Ask me anything about your onboarding process!")

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
elif user_input:
    prompt = user_input
else:
    prompt = None
    
if prompt:
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
                    "history": st.session_state.messages[:-1]
                }
                response = client.post(
                    CHAT_URL,
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
    
