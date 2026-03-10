from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from router import userCRUD, bookCRUD, extraFeatures
import os

app = FastAPI(title="Book Engine API")




# Include the routers
app.include_router(userCRUD.router)
app.include_router(bookCRUD.router)
app.include_router(extraFeatures.router)



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