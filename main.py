from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from fastapi.middleware.cors import CORSMiddleware
from router import userCRUD, bookCRUD, extraFeatures
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Book Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows the Inspector to access your server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Include the routers
app.include_router(userCRUD.router)
app.include_router(bookCRUD.router)
app.include_router(extraFeatures.router)

# The Metadata content
METADATA = {
    "resource": "https://joshualim-webservicesandwebdata.onrender.com/mcp",
    "authorization_servers": ["https://joshualim-webservicesandwebdata.onrender.com"],
    "scopes_supported": ["mcp:tools"]
}

# Route 1: Root level discovery
@app.get("/.well-known/oauth-protected-resource")
async def get_root_metadata():
    return METADATA

# Route 2: Sub-path discovery (This is likely what the Inspector is looking for)
@app.get("/.well-known/oauth-protected-resource/mcp")
async def get_path_metadata():
    return METADATA

@app.get("/.well-known/oauth-authorization-server")
async def get_auth_server_metadata():
    return {
        "issuer": "https://joshualim-webservicesandwebdata.onrender.com",
        "authorization_endpoint": "https://joshualim-webservicesandwebdata.onrender.com/users/login",
        "token_endpoint": "https://joshualim-webservicesandwebdata.onrender.com/users/login",
        "response_types_supported": ["token"],
        "grant_types_supported": ["password"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"]
    }

mcp = FastApiMCP(
    app,
    include_operations=[
        "login",
        "createBook", "getBookDetails", "updateBook", "deleteBook", "rateBook",
        "createUser", "getUserProfile", "updateUser", "deleteUserAccount",
        "getGenreTrends", "getBookSuggestions", "generateBookDescriptionAI"
    ]
)

mcp.mount_http()
PORT = int(os.environ.get("PORT", 10000))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)