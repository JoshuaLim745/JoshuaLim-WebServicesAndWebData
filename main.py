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
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select, delete
from typing import List, Optional
from pydantic import BaseModel, EmailStr

# Import from your existing file
from databaseModel import engine, User, Book, Genre, UserRatesBook, book_genre_link, user_genre_link

app = FastAPI()

# --- Database Dependency ---
def get_db():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# --- Pydantic Schemas ---
class userAuth(BaseModel):
    email: EmailStr
    password: str

class genreUpdate(userAuth):
    mode: str  # "add" or "delete"
    genreName: str

class bookRating(userAuth):
    book_id: int
    rating: float # Use a scale like 1.0 to 5.0
# --- 1. CRUD OPERATIONS ---

@app.post("/Create/", tags=["User CRUD"], summary="Register a new user")
def createUser(user_in: userAuth, db: Session = Depends(get_db)):

    """
    ### Create User Data
    This endpoint allows you to **register a new user** in the database.
    
    * **Input**: JSON containing a user's `email` and `password`.
    * **Output**: Returns the user data upon success.
    * **Error**: Returns an appropriate message if the user already exists.
    """

    # Check if exists
    if db.query(User).filter_by(email=user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    newUser = User(email=user_in.email, password=user_in.password)
    db.add(newUser)
    db.commit()
    db.refresh(newUser)


    return {
        "message": "A new user has been created",
        "email": newUser.email,
        "status": "success"
        }

@app.post("/Read/", tags=["User CRUD"], summary="View user profile")
def readUser(user_in: userAuth, db: Session = Depends(get_db)):

    """
    ### Read User Data
    Retrieves the profile and favorite genres for an existing user.
    
    * **Input**: JSON containing a user's `email` and `password`.
    * **Security**: Serves as a basic authentication check.
    * **Output**: Returns user email and a list of their favourite genres.
    * **Error**: Returns `401 Unauthorized` if user's credentials do not match with user data in the database.
    """


    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    return {
        "email": user.email,
        "favorite_genres": [g.name for g in user.fav_genres]
    }

@app.put("/Update/", tags=["User CRUD"], summary="Modify user genre preferences")
def updateGenres(data: genreUpdate, db: Session = Depends(get_db)):

    """
    ### Update User Preferences
    Allows a user to manage their favorite genre list.
    
    * **Input**: 
        * `Mode`: Use **'add'** to add a genre to a user's favorite genre list or **'delete'** to remove it from the list.
        * `genreName`: The name of the genre (e.g., 'Fantasy').
    * **Logic**: Modifies the `user_genre_link` association table.
    * **Output**: Returns the updated list of genres for the user.
    """

    user = db.query(User).filter_by(email=data.email, password=data.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    genre = db.query(Genre).filter_by(name=data.genreName).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found in database")

    if data.mode == "add":
        if genre not in user.fav_genres:
            user.fav_genres.append(genre)

    elif data.mode == "delete":
        if genre in user.fav_genres:
            user.fav_genres.remove(genre)
        else:
            HTTPException(status_code=403, detail="Genre not found in your favourite list")
    
    db.commit()
    return {
        "message": "User's genre preferences has been updated",
        "email": user.email, 
        "updated_genres": [g.name for g in user.fav_genres],
        "status": "success"
        }




@app.delete("/Delete/", tags=["User CRUD"], summary="Remove user account")
def deleteUser(user_in: userAuth, db: Session = Depends(get_db)):

    """
    ### Delete User Data
    Permanently removes a user and their associations from the database.
    
    * **Input**: JSON containing a user's `email` and `password`.
    * **Logic**: Removes the record from the `users` table. Cascade settings handle the link table.
    * **Output**: Confirmation message of removal.
    """

    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    db.delete(user)
    db.commit()
    return {
        "message": "User data removed entirely from database",
        "status": "success"}


# --- 2. PERSONALIZED SUGGESTIONS ---

@app.post("/Suggestions/", tags=["Discovery"], summary="Get book recommendations based on high user ratings")
def getSuggestions(user_in: userAuth, db: Session = Depends(get_db)):
    """
    ### Personalized Recommendations Engine
    Provides book suggestions based on user rating history (3.5 to 5.0 stars).
    """

    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")

    # 1. Identify most common genre among user's highly-rated books (3.5 - 5.0)
    top_genre_subquery = (
        db.query(book_genre_link.c.genre_id)
        .join(UserRatesBook, UserRatesBook.book_id == book_genre_link.c.book_id)
        .filter(
            UserRatesBook.user_id == user.id, 
            UserRatesBook.user_rating.between(3.5, 5.0) # Updated range filter
        )
        .group_by(book_genre_link.c.genre_id)
        .order_by(func.count().desc())
        .first()
    )

    if not top_genre_subquery:
        return {"message": "No highly-rated books (3.5+) found to provide suggestions."}

    genre_id = top_genre_subquery[0]

    # 2. Find 3 books in that genre not yet rated by the user
    # Creating a subquery of IDs the user has already interacted with
    rated_books_ids = db.query(UserRatesBook.book_id).filter(UserRatesBook.user_id == user.id)
    
    suggestions = (
        db.query(Book)
        .join(book_genre_link)
        .filter(
            book_genre_link.c.genre_id == genre_id,
            ~Book.id.in_(rated_books_ids) # Using ~...in_ for cleaner "not in" logic
        )
        .limit(3)
        .all()
    )

    if not suggestions:
        return {"message": "No new books found in your favorite genre."}

    return suggestions

# --- 3. GENRE TRENDS ---

@app.get("/Trends/{target}", tags=["Analytics"], summary="View genre popularity")
def getTrends(target: str, db: Session = Depends(get_db)):

    """
    ### Genre Trend Analysis
    Aggregates data to show which genres are currently the most popular.
    
    * **Path Parameter (`target`)**:
        * `Book`: Tallies how many books are assigned to each genre.
        * `User`: Tallies how many users have added a genre to their favorites.
    * **Logic**: Uses PostgreSQL `COUNT` and `GROUP BY` functions for efficient tallying.
    * **Output**: A dictionary of genres ordered from most to least popular.
    """

    if target.title() == "Book":
        # Popularity based on how many books are assigned a genre
        results = (
            db.query(Genre.name, func.count(book_genre_link.c.book_id).label("total"))
            .join(book_genre_link)
            .group_by(Genre.name)
            .order_by(func.desc("total"))
            .all()
        )
    elif target.title() == "User":
        # Popularity based on how many users favorited a genre
        results = (
            db.query(Genre.name, func.count(user_genre_link.c.user_id).label("total"))
            .join(user_genre_link)
            .group_by(Genre.name)
            .order_by(func.desc("total"))
            .all()
        )
    else:
        raise HTTPException(status_code=400, detail="Choose between 'User' or 'Book'")

    return {name: count for name, count in results}




# Book Rating
@app.post("/RateBook/", tags=["Book Interactions"], summary="Rate a book")
def rateBook(data: bookRating, db: Session = Depends(get_db)):
    """
    ### Rate a Book
    Allows an authenticated user to give a star rating (1.0 - 5.0) to a specific book.
    """
    
    # 1. Validate Rating Range
    # We check this first to fail fast before querying the database
    if not (1.0 <= data.rating <= 5.0):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid rating: {data.rating}. Rating must be between 1.0 and 5.0."
        )

    # 2. Verify User Credentials
    user = db.query(User).filter_by(email=data.email, password=data.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")

    # 3. Verify Book Exists
    book = db.query(Book).filter_by(id=data.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # 4. Check for an existing rating (Composite Key lookup)
    existing_entry = db.query(UserRatesBook).filter_by(
        user_id=user.id, 
        book_id=data.book_id
    ).first()

    if existing_entry:
        # Update existing rating
        existing_entry.user_rating = data.rating
        status_msg = f"Updated rating to {data.rating}"
    else:
        # Create new rating entry
        new_rating = UserRatesBook(
            user_id=user.id, 
            book_id=data.book_id, 
            user_rating=data.rating
        )
        db.add(new_rating)
        status_msg = f"Successfully rated book {data.book_id} with {data.rating} stars"

    db.commit()
    return {"message": status_msg, "user": user.email, "book_id": data.book_id}