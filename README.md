# 🧠 AI HR RAG Onboarding Agent

An end-to-end **AI onboarding assistant** built with Azure OpenAI, Azure AI Search, FastAPI, LlamaIndex, LangChain, and MS Graph.  
It helps new employees onboard faster by allowing them to chat with an AI agent, search company documents via RAG, upload new documents, and interact with their Microsoft 365 calendar.

---

## 🎥 Demo Video


---

## 🚀 Features

### ✅ Intelligent Onboarding Chat Assistant
- Chat with an AI agent powered by **Azure OpenAI**.
- Understands onboarding topics, company rules, internal processes, etc.

### ✅ RAG Document Search — With Live Document Uploads
- Upload **PDF documents directly from the UI**.
- All uploaded files are automatically:
  - chunked  
  - embedded  
  - indexed into **Azure AI Search**  
- The agent immediately uses the new documents for RAG-based answers.

### ✅ Microsoft Graph Calendar Integration
- Authenticate with your **Microsoft 365 account** via Device Flow.
- The AI agent can:
  - List upcoming meetings  
  - Create new onboarding events  
  - Help plan your first days at the company  

### ✅ Full Local UX
- **FastAPI** backend for LLM logic, RAG pipeline, and MS Graph integration.
- **Streamlit** UI with:
  - Chat interface  
  - File uploader for dynamic RAG ingestion  
  - Microsoft login  

---

## 🧰 Tech Stack

### **AI & RAG**
- Azure OpenAI  
- Azure AI Search  
- LlamaIndex (RAG)  
- LangChain (agent & tools)

### **Backend**
- FastAPI  
- Python  
- MS Graph API  
- OAuth Device Flow  

### **Frontend**
- Streamlit (chat, upload, login)

### **Dev Tools**
- Git  
- GitHub  

---

## 📦 Local Setup

### 0. Init Azure Resources & Add .env file

### 1. Initialise the repository
```bash
git clone https://github.com/<yourusername>/hr-onboarding-agent.git
cd hr-onboarding-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start FastAPI
```bash
uvicorn app.main:app --reload
```

### 3. Start Streamlit UI
```bash
streamlit run ui/app.py
```