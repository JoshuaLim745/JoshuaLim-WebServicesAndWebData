"""
TODO: Functions / endpoints needed in main
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
class UserAuth(BaseModel):
    email: EmailStr
    password: str

class GenreUpdate(UserAuth):
    mode: str  # "add" or "delete"
    genre_name: str

# --- 1. CRUD OPERATIONS ---

@app.post("/Create/")
def createUser(user_in: UserAuth, db: Session = Depends(get_db)):
    # Check if exists
    if db.query(User).filter_by(email=user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(email=user_in.email, password=user_in.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}

@app.post("/Read/")
def readUser(user_in: UserAuth, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    return {
        "email": user.email,
        "favorite_genres": [g.name for g in user.fav_genres]
    }

@app.put("/Update/")
def updateGenres(data: GenreUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email, password=data.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    genre = db.query(Genre).filter_by(name=data.genre_name).first()
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
    return {"email": user.email, "updated_genres": [g.name for g in user.fav_genres]}

@app.delete("/Delete/")
def deleteUser(user_in: UserAuth, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")
    
    db.delete(user)
    db.commit()
    return {"message": "User data removed entirely from database"}

# --- 2. PERSONALIZED SUGGESTIONS ---

@app.post("/Suggestions/")
def getSuggestions(user_in: UserAuth, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=user_in.email, password=user_in.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect user information")

    # 1. Identify most common genre among user's 5-star books
    top_genre_subquery = (
        db.query(book_genre_link.c.genre_id)
        .join(UserRatesBook, UserRatesBook.book_id == book_genre_link.c.book_id)
        .filter(UserRatesBook.user_id == user.id, UserRatesBook.user_rating == 5.0)
        .group_by(book_genre_link.c.genre_id)
        .order_by(func.count().desc())
        .first()
    )

    if not top_genre_subquery:
        return {"message": "No top-rated books found to provide suggestions."}

    genre_id = top_genre_subquery[0]

    # 2. Find 3 books in that genre not rated by the user
    rated_books_ids = db.query(UserRatesBook.book_id).filter(UserRatesBook.user_id == user.id).subquery()
    
    suggestions = (
        db.query(Book)
        .join(book_genre_link)
        .filter(book_genre_link.c.genre_id == genre_id)
        .filter(Book.id.not_in(select(rated_books_ids)))
        .limit(3)
        .all()
    )

    if not suggestions:
        return {"message": "No new books found in your favorite genre."}

    return suggestions

# --- 3. GENRE TRENDS ---

@app.get("/Trends/{target}")
def getTrends(target: str, db: Session = Depends(get_db)):
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