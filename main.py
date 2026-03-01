"""
Functions / endpoints needed in main
1. CRUD for User data
    Create user data - From the swagger UI Doc we can just execute some lines. 
        input --> Create/{email, password}
        output --> return user data that corresponds to the input. If incorrect user information then display appropriate message

    Read - Return user data - possibly like a user profile to just show logged in user data
        input --> Read/{email, password}
        output --> return user data that corresponds to the input. If incorrect user information then display appropriate message

    Update - similar to above we just allow users to edit their profile. 
        input --> Update/{email, password, Mode(add, delete), Genre to add/delete}
        output --> updated genre list. If incorrect user information then display appropriate message

    Delete user data
        input --> Delete/{email, password, Delete}
        output --> Removal of the user data entirely from database. If incorrect user information then display appropriate message

2. Personalised suggestions. - recommend stuff based on user preferences - link to userID
    Look at the user's top-rated books (e.g., books they gave 5 stars).
    Identify the most common genre among those top books.
    Suggest 3 books from the db that match that genre but that they haven't been read/rated by the user.

    input  --> Suggestions/{email, password}
    output --> return data of 3 books that the user has not rated. If there are none then appropriate message should be returned. If incorrect user information then display appropriate message

3. Genre Trends - Just query table and tally genres and order by popularity - can be for books or users
    User chooses between the User or Book table
    input  --> Trends/{User/Book}
    output --> list of numbers that show tally genres and order by popularity. 


Ensure for security aswell. 
1. Prevention of SQL Injection
2. CSRF Security

TODO:
1. Testing of all functionality
    a. Create -- Done
    b. Read -- Done
    c. Update -- Done
    d. Delete
    e. Suggestions
    f. Trends
    g. Rate book

2. Add password hashing and min len of password when user creates a password (maybe can be done in databaseModel.py? so that I dont have to encyrpt and decrypt each time)
3. Update Swagger UI Documentation
4. Due to allowing users to rate books, do I want to consider updating a books avg rating if a user adds their ratings?
(Will most likely need another table just for books and rating )

5. add CRUD for books
6. look for 1 to 2 more functions to implement that provide an analytical endpoint.
    a. An endpoint where given a bookId the name of the book is passed to a third party endpoint (like Gemini or chatgpt )
        to generate a description / synopsis of the book (Unconfirmed)
    b. Endpoint - Returns books with the highest avg. Return player with the most number of ratings and the avg value of their ratings

"""


from fastapi import FastAPI
from router import userCRUD, bookCRUD, extraFeatures

app = FastAPI(title="Book Engine API")

# Include the routers
app.include_router(userCRUD.router)
app.include_router(bookCRUD.router)
app.include_router(extraFeatures.router)

@app.get("/")
def home():
    return {"status": "API is running"}