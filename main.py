from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from fastapi.middleware.cors import CORSMiddleware
from router import userCRUD, bookCRUD, extraFeatures
import os

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

@app.get("/.well-known/oauth-protected-resource")
async def get_oauth_metadata():
    return {
        "resource": "https://joshualim-webservicesandwebdata.onrender.com/mcp", 
        "authorization_servers": ["https://joshualim-webservicesandwebdata.onrender.com"],
        "scopes_supported": ["mcp:tools"]
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
PORT = os.environ.get("PORT", 8000)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)