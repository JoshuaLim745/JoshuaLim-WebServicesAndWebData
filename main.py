from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from router import userCRUD, bookCRUD, extraFeatures

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)